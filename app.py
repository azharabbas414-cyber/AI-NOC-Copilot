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
FIXED_GOOGLE_DRIVE_URL = "PASTE_YOUR_GOOGLE_DRIVE_LINK_HERE"


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
# 3. Simple RAG retrieval
# =========================================================
def get_words(text):
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def retrieve_knowledge(question, uploaded_chunks, top_k=4):
    query_words = get_words(question)
    candidates = []

    for number, chunk in enumerate(uploaded_chunks, start=1):
        chunk_words = get_words(chunk)
        score = len(query_words.intersection(chunk_words))

        if score > 0:
            candidates.append(
                (score, f"RAG chunk {number}", chunk)
            )

    candidates.sort(key=lambda x: x[0], reverse=True)

    return [
        {"source": source, "text": text}
        for _, source, text in candidates[:top_k]
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

    if drive_url == "https://drive.google.com/drive/folders/1nJwrAhBnX9wjuo4TtWNSOtvvq8gl6apT?usp=drive_link":
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
        "🧠 General AI",
        "📚 Search My Documents",
        "🤖 Documents + AI",
    ],
    index=2,
)

st.caption(
    "🧠 General AI = model knowledge. "
    "📚 Search My Documents = retrieved RAG content only. "
    "🤖 Documents + AI = RAG context + LLM explanation."
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

    if mode == "🧠 General AI":
        with st.spinner("Generating General AI response..."):
            answer, error = call_llm(q)

        if error:
            st.session_state.error = error
        else:
            st.session_state.answer = answer

    elif mode == "📚 Search My Documents":
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
