import os
import re
import io
import json
import streamlit as st
from openai import OpenAI
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs, quote

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


# =========================================================
# Fixed Google Drive knowledge source
# =========================================================
# Paste your Google Drive file/folder link ONCE here.
# After that, the app loads this source automatically; no repeated upload/paste is needed.
FIXED_GOOGLE_DRIVE_URL = "https://drive.google.com/drive/folders/1nJwrAhBnX9wjuo4TtWNSOtvvq8gl6apT"


# =========================================================
# 1. Text extraction
# =========================================================
def extract_text_from_bytes(data, filename):
    name = filename.lower()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if name.endswith(".pdf") and PdfReader:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx") and Document:
        document = Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)

    return ""


def split_into_chunks(text, words_per_chunk=700):
    words = text.split()
    return [
        " ".join(words[i:i + words_per_chunk]).strip()
        for i in range(0, len(words), words_per_chunk)
        if " ".join(words[i:i + words_per_chunk]).strip()
    ]


# =========================================================
# 2. Google Drive helpers
# =========================================================
def get_google_drive_api_key():
    try:
        return st.secrets["GOOGLE_DRIVE_API_KEY"]
    except Exception:
        return os.getenv("GOOGLE_DRIVE_API_KEY")


def extract_drive_id(url):
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"/folders/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def google_drive_api(url):
    api_key = get_google_drive_api_key()
    if not api_key:
        raise ValueError("GOOGLE_DRIVE_API_KEY is not configured.")

    file_id = extract_drive_id(url)
    if not file_id:
        raise ValueError("Could not find a Google Drive file/folder ID in the link.")

    return file_id, api_key


def drive_get_metadata(file_id, api_key):
    endpoint = (
        "https://www.googleapis.com/drive/v3/files/"
        + file_id
        + "?fields=id,name,mimeType,size&key="
        + api_key
    )
    request = Request(endpoint, headers={"Accept": "application/json"})

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def drive_download_file(file_id, api_key):
    metadata = drive_get_metadata(file_id, api_key)
    name = metadata.get("name", "drive_file")

    mime = metadata.get("mimeType", "")

    if mime == "application/vnd.google-apps.document":
        export_url = (
            "https://www.googleapis.com/drive/v3/files/"
            + file_id
            + "/export?mimeType=text/plain&key="
            + api_key
        )
        request = Request(export_url, headers={"Accept": "text/plain"})
        with urlopen(request, timeout=30) as response:
            return name + ".txt", response.read()

    if mime.startswith("application/vnd.google-apps."):
        raise ValueError(
            f"Google Workspace file '{name}' is not supported yet. "
            "Use a TXT, PDF, or DOCX file in the Drive folder."
        )

    download_url = (
        "https://www.googleapis.com/drive/v3/files/"
        + file_id
        + "?alt=media&key="
        + api_key
    )
    request = Request(download_url)

    with urlopen(request, timeout=60) as response:
        return name, response.read()


def drive_list_folder(folder_id, api_key):
    query = (
        "'"
        + folder_id
        + "' in parents and trashed = false"
        + " and (mimeType = 'text/plain'"
        + " or mimeType = 'application/pdf'"
        + " or mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
    )

    endpoint = (
        "https://www.googleapis.com/drive/v3/files"
        "?q=" + quote(query)
        + "&fields=files(id,name,mimeType,size)"
        + "&pageSize=100"
        + "&key=" + api_key
    )

    request = Request(endpoint, headers={"Accept": "application/json"})

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")).get("files", [])


@st.cache_data(ttl=3600, show_spinner=False)
def load_google_drive(url):
    file_id, api_key = google_drive_api(url)
    metadata = drive_get_metadata(file_id, api_key)

    chunks = []
    loaded_names = []

    if metadata.get("mimeType") == "application/vnd.google-apps.folder":
        files = drive_list_folder(file_id, api_key)

        if not files:
            raise ValueError(
                "No supported TXT, PDF, or DOCX files were found in the folder."
            )

        for item in files:
            name, data = drive_download_file(item["id"], api_key)
            text = extract_text_from_bytes(data, name)

            if text.strip():
                chunks.extend(split_into_chunks(text))
                loaded_names.append(name)
    else:
        name, data = drive_download_file(file_id, api_key)
        text = extract_text_from_bytes(data, name)

        if not text.strip():
            raise ValueError(
                "The Drive file could not be converted into readable text."
            )

        chunks.extend(split_into_chunks(text))
        loaded_names.append(name)

    return chunks, loaded_names


# =========================================================
# 3. Focused RAG retrieval
# =========================================================
# This is intentionally lightweight: no vector database or embeddings.
# The retriever removes common words, gives extra weight to exact/domain
# terms, and filters weak matches so unrelated incidents are not shown.
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "why", "how",
    "can", "could", "would", "should", "do", "does", "did", "to", "of",
    "in", "on", "for", "from", "with", "and", "or", "my", "your", "this",
    "that", "it", "be", "go", "goes", "going", "cause", "causes", "reason",
    "problem", "issue", "incident", "network", "session", "down",
}

# Important NOC/domain terms get stronger matching.
DOMAIN_TERMS = {
    "bgp", "ospf", "mtu", "crc", "packet", "loss", "congestion",
    "interface", "neighbor", "adjacency", "peer", "prefix", "route",
    "routing", "authentication", "area", "optic", "fiber", "duplex",
}

def get_words(text):
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def retrieve_knowledge(question, uploaded_chunks, top_k=4):
    query_words = get_words(question)
    meaningful_query = query_words - STOP_WORDS

    # If the question contains a strong protocol/topic term, prefer only
    # chunks that contain that same topic. This prevents a BGP question from
    # returning OSPF/MTU/CRC incidents merely because they also say "down".
    topic_terms = meaningful_query.intersection(DOMAIN_TERMS)

    candidates = []
    for number, chunk in enumerate(uploaded_chunks, start=1):
        chunk_words = get_words(chunk)

        if topic_terms and not topic_terms.intersection(chunk_words):
            continue

        overlap = meaningful_query.intersection(chunk_words)
        score = len(overlap)

        # Stronger score for domain terms and exact multi-word phrases.
        score += 2 * len(overlap.intersection(DOMAIN_TERMS))

        q_lower = question.lower().strip()
        c_lower = chunk.lower()
        if q_lower and q_lower in c_lower:
            score += 10

        # Reward common incident phrases such as "bgp session", "ospf
        # neighbor", "crc errors", and "mtu mismatch".
        phrase_hits = 0
        for phrase in (
            "bgp session", "bgp peer", "ospf neighbor", "ospf adjacency",
            "crc errors", "crc error", "packet loss", "interface errors",
            "mtu mismatch", "mtu problem", "link congestion",
        ):
            if phrase in q_lower and phrase in c_lower:
                phrase_hits += 4
        score += phrase_hits

        if score > 0:
            candidates.append((score, len(overlap), f"RAG chunk {number}", chunk))

    if not candidates:
        return []

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_score = candidates[0][0]

    # Keep only strong matches. If one document is clearly the best match,
    # return only that document rather than filling the UI with weak chunks.
    strong = [item for item in candidates if item[0] >= max(3, best_score * 0.60)]

    # For a focused incident query, one highly relevant chunk is preferred.
    if topic_terms and strong:
        strong = strong[:1]

    return [
        {"source": source, "text": text}
        for _, _, source, text in strong[:top_k]
    ]


# =========================================================
# 4. Groq
# =========================================================
def get_groq_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY")


def call_llm(question, rag_context=None):
    api_key = get_groq_key()

    if not api_key:
        return None, "GROQ_API_KEY is not configured."

    if rag_context:
        prompt = f"""
You are an AI NOC Copilot.

Answer the user's question using the retrieved content from the user's
RAG documents.

USER QUESTION:
{question}

RETRIEVED RAG CONTENT:
{rag_context}

Rules:
- Use the RAG content as the primary source.
- Clearly explain the answer.
- Do not invent information not supported by the context.
- If the context is insufficient, say so.
"""
    else:
        prompt = f"""
You are an AI NOC Copilot.

Answer the user's question using your general model knowledge.

USER QUESTION:
{question}

Rules:
- Give a clear answer.
- Do not invent device output or network measurements.
- Clearly say when evidence is insufficient.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a helpful NOC AI assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content, None

    except Exception as exc:
        return None, str(exc)


# =========================================================
# 5. Clear
# =========================================================
def clear_results():
    st.session_state.question = ""
    st.session_state.answer = ""
    st.session_state.rag_results = []
    st.session_state.error = ""
    st.session_state.drive_chunks = []
    st.session_state.drive_files = []


# =========================================================
# 6. UI
# =========================================================
st.set_page_config(page_title="AI-NOC Copilot", page_icon="🤖", layout="centered")



# --- Polished UI ---
st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 1.8rem; padding-bottom: 3rem;}
.hero {
    padding: 1.5rem 1.7rem; border: 1px solid rgba(128,128,128,.18);
    border-radius: 18px; margin-bottom: 1.25rem;
    background: linear-gradient(135deg, rgba(70,90,140,.10), rgba(70,140,120,.07));
}
.hero h1 {margin:0 0 .35rem 0; font-size: 2.05rem;}
.hero p {margin:0; opacity:.78; font-size:1rem;}
.section-title {font-weight:700; font-size:1.08rem; margin:1.1rem 0 .45rem;}
.status {
    border-radius: 12px; padding: .75rem 1rem; margin:.5rem 0 1rem;
    border:1px solid rgba(128,128,128,.18);
}
.answer-card {
    border:1px solid rgba(128,128,128,.18); border-radius:16px;
    padding:1rem 1.1rem; margin-top:.65rem;
}
.answer-card h4 {margin-top:0;}
.small-muted {opacity:.65; font-size:.88rem;}
div[data-testid="stRadio"] > div {gap: .45rem;}
div[data-testid="stRadio"] label {
    border:1px solid rgba(128,128,128,.20); border-radius:12px;
    padding:.35rem .7rem; 
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🤖 AI-NOC Copilot</h1>
  <p>Lightweight AI assistant for NOC incident analysis • RAG + AI comparison</p>
</div>
""", unsafe_allow_html=True)
for key, default in {
    "question": "",
    "answer": "",
    "rag_results": [],
    "error": "",
    "drive_chunks": [],
    "drive_files": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🤖 AI-NOC Copilot")
st.write(
    "A beginner AI project for learning RAG + LLM using your own NOC knowledge."
)

st.info("Question → Choose Source → Retrieve → Answer")

# ---------------------------------------------------------
# RAG source
# ---------------------------------------------------------
st.subheader("📚 RAG Knowledge")

source_type = st.radio(
    "Choose where your RAG documents come from",
    ["📁 Upload from PC", "🔗 Fixed Google Drive"],
    horizontal=True,
)

rag_chunks = []
drive_files = []

if source_type == "📁 Upload from PC":
    uploaded_files = st.file_uploader(
        "Upload NOC knowledge files",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            text = extract_text_from_bytes(
                uploaded_file.getvalue(),
                uploaded_file.name,
            )

            if text.strip():
                rag_chunks.extend(split_into_chunks(text))

        if rag_chunks:
            st.success(
                f"✅ {len(uploaded_files)} document(s) ready for RAG • "
                f"{len(rag_chunks)} chunk(s)"
            )

else:
    # The Drive source is fixed in the app, so the user does not need to
    # paste the link or upload the documents on every run.
    drive_url = FIXED_GOOGLE_DRIVE_URL.strip()

    if drive_url == "PASTE_YOUR_GOOGLE_DRIVE_LINK_HERE":
        st.warning(
            "Set your Google Drive link once in FIXED_GOOGLE_DRIVE_URL in app.py."
        )
    else:
        st.caption("🔗 Fixed Google Drive source")
        st.code(drive_url, language=None)

        # Cache the downloaded Drive content so normal Streamlit reruns do not
        # download the same documents again.
        try:
            with st.spinner("Loading fixed Google Drive knowledge base..."):
                rag_chunks, drive_files = load_google_drive(drive_url)

            st.session_state.drive_chunks = rag_chunks
            st.session_state.drive_files = drive_files

            st.success(
                f"✅ {len(drive_files)} document(s) ready for RAG • "
                f"{len(rag_chunks)} chunk(s)"
            )
        except Exception as exc:
            st.error(f"Google Drive error: {exc}")

        if drive_files:
            st.caption("Loaded: " + " • ".join(drive_files))


# ---------------------------------------------------------
# Question
# ---------------------------------------------------------
st.subheader("📝 Ask Your Question")

question = st.text_area(
    "Question",
    value=st.session_state.question,
    placeholder="Example: What can cause a BGP session to go down?",
    height=120,
)

mode = st.radio(
    "How should the answer be generated?",
    [
        "🧠 AI Response",
        "📚 RAG Response",
        "🔍 RAG + AI Comparison",
    ],
    index=2,
)

st.caption(
    "🧠 AI Response = model knowledge. "
    "📚 RAG Response = retrieved RAG content only. "
    "🔍 RAG + AI Comparison = RAG context + LLM explanation."
)

col1, col2 = st.columns(2)

with col1:
    analyze = st.button("🚀 Get Answer", type="primary", use_container_width=True)

with col2:
    clear = st.button("🗑️ Clear Results", use_container_width=True)

if clear:
    clear_results()
    st.rerun()

if analyze:
    q = question.strip()

    if not q:
        st.warning("Please enter a question.")
        st.stop()

    st.session_state.question = q
    st.session_state.answer = ""
    st.session_state.rag_results = []
    st.session_state.error = ""

    if mode == "🧠 AI Response":
        with st.spinner("Generating General AI response..."):
            answer, error = call_llm(q)

        if error:
            st.session_state.error = error
        else:
            st.session_state.answer = answer

    elif mode == "📚 RAG Response":
        if not rag_chunks:
            st.session_state.error = "Please load RAG documents first."
        else:
            results = retrieve_knowledge(q, rag_chunks)
            st.session_state.rag_results = results

            if not results:
                st.session_state.error = (
                    "No relevant content was found in your RAG documents."
                )

    else:
        if not rag_chunks:
            st.session_state.error = "Please load RAG documents first."
        else:
            results = retrieve_knowledge(q, rag_chunks)
            st.session_state.rag_results = results

            context = "\n\n".join(
                f"SOURCE: {item['source']}\n{item['text']}"
                for item in results
            )

            with st.spinner("Generating answer using RAG + AI..."):
                answer, error = call_llm(
                    q,
                    rag_context=context if context else None,
                )

            if error:
                st.session_state.error = error
            else:
                st.session_state.answer = answer


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------
if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.rag_results:
    st.subheader("📖 RAG Retrieved Results")
    for item in st.session_state.rag_results:
        with st.expander(item["source"], expanded=True):
            st.write(item["text"])

if st.session_state.answer:
    st.subheader("🤖 LLM Response")
    st.markdown(st.session_state.answer)

st.divider()
st.caption(
    "Learning/demo project. Verify AI answers against real network evidence."
)
