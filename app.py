import os
import re
import streamlit as st
from openai import OpenAI

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


# =========================================================
# 1. Built-in NOC knowledge
# =========================================================
BUILT_IN_KNOWLEDGE = [
    {
        "topic": "Packet Loss",
        "text": "Packet loss can be caused by congestion, interface errors, physical-layer problems, faulty equipment, or overloaded devices. Check interface utilization, error counters, drops, and the affected link."
    },
    {
        "topic": "High Latency",
        "text": "High latency may be caused by congestion, a long network path, routing changes, overloaded devices, or packet loss. Check the path, utilization, and whether latency changed during the incident."
    },
    {
        "topic": "Congestion",
        "text": "Network congestion occurs when traffic approaches or exceeds available bandwidth. Check interface utilization, traffic trends, queue drops, and whether a traffic spike occurred."
    },
    {
        "topic": "Interface Errors",
        "text": "CRC and other interface errors can indicate physical-layer issues, bad cables, optics, speed or duplex problems, or faulty hardware. Check interface counters and the physical connection."
    },
    {
        "topic": "OSPF",
        "text": "OSPF neighbor problems can be caused by interface issues, area mismatch, authentication mismatch, network-type mismatch, or unstable links. Check OSPF neighbors and logs."
    },
    {
        "topic": "BGP",
        "text": "BGP session problems may be caused by reachability issues, incorrect peer configuration, authentication problems, filtering, or remote peer failure. Check peer state, prefixes, and logs."
    },
    {
        "topic": "VLAN",
        "text": "VLAN connectivity problems can result from incorrect VLAN membership, trunk configuration, tagging, or native VLAN settings. Verify VLAN membership and whether the VLAN is allowed on the trunk."
    },
    {
        "topic": "MTU",
        "text": "MTU problems can cause packet drops or application connectivity issues. Check MTU values along the path and test packet sizes. Inconsistent MTU settings can cause fragmentation or dropped oversized packets."
    },
]


# =========================================================
# 2. File extraction
# =========================================================
def extract_text(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".txt"):
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):
        if PdfReader is None:
            return ""
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if filename.endswith(".docx"):
        if Document is None:
            return ""
        document = Document(uploaded_file)
        return "\n".join(p.text for p in document.paragraphs)

    return ""


def split_into_chunks(text, words_per_chunk=700):
    words = text.split()
    chunks = []

    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i:i + words_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


# =========================================================
# 3. Simple RAG retrieval
# =========================================================
def get_words(text):
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def retrieve_knowledge(question, uploaded_chunks, top_k=4):
    query_words = get_words(question)
    candidates = []

    # Built-in knowledge
    for item in BUILT_IN_KNOWLEDGE:
        item_words = get_words(item["topic"] + " " + item["text"])
        score = len(query_words.intersection(item_words))

        if score > 0:
            candidates.append(
                (score, f"Built-in: {item['topic']}", item["text"])
            )

    # Uploaded documents
    for number, chunk in enumerate(uploaded_chunks, start=1):
        chunk_words = get_words(chunk)
        score = len(query_words.intersection(chunk_words))

        if score > 0:
            candidates.append(
                (score, f"Uploaded document - chunk {number}", chunk)
            )

    candidates.sort(key=lambda x: x[0], reverse=True)

    return [
        {"source": source, "text": text}
        for _, source, text in candidates[:top_k]
    ]


# =========================================================
# 4. Groq LLM
# =========================================================
def get_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY")


def call_llm(question, rag_context=None):
    api_key = get_api_key()

    if not api_key:
        return None, "GROQ_API_KEY is not configured."

    if rag_context:
        prompt = f"""
You are an AI NOC Copilot.

Answer the user's question using the retrieved RAG context below.

USER QUESTION:
{question}

RAG CONTEXT:
{rag_context}

Rules:
- Give a clear, useful answer.
- Prefer the supplied RAG context when it is relevant.
- You may explain concepts using your general knowledge.
- Do not invent network measurements or device output.
- Clearly say when the evidence is insufficient.
"""
    else:
        prompt = f"""
You are an AI NOC Copilot.

Answer the user's question using your general model knowledge.

USER QUESTION:
{question}

Rules:
- Give a clear, useful answer.
- Do not invent network measurements or device output.
- Clearly say when the evidence is insufficient.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful, concise NOC AI assistant.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content, None

    except Exception as exc:
        return None, str(exc)


# =========================================================
# 5. Streamlit UI
# =========================================================
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 AI-NOC Copilot")
st.write(
    "Ask a network question and choose whether the answer should use "
    "the LLM alone, your uploaded RAG documents, or both."
)

st.info("Simple learning flow: Question → Selected Source → LLM → Answer")


# ---------------------------------------------------------
# Upload RAG documents
# ---------------------------------------------------------
st.subheader("📚 RAG Documents")

uploaded_files = st.file_uploader(
    "Upload NOC documents",
    type=["txt", "pdf", "docx"],
    accept_multiple_files=True,
)

uploaded_chunks = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        text = extract_text(uploaded_file)

        if text.strip():
            chunks = split_into_chunks(text)
            uploaded_chunks.extend(chunks)
            st.success(
                f"{uploaded_file.name}: {len(chunks)} chunk(s) loaded."
            )
        else:
            st.warning(f"{uploaded_file.name}: no readable text found.")


# ---------------------------------------------------------
# Question and source selection
# ---------------------------------------------------------
st.subheader("📝 Ask Your Question")

question = st.text_area(
    "Question",
    placeholder=(
        "Example: What could cause packet loss when interface "
        "utilization is very high?"
    ),
    height=130,
)

source_mode = st.radio(
    "How should the answer be generated?",
    options=[
        "LLM Only",
        "Uploaded RAG Only",
        "Both: RAG + LLM",
    ],
    index=2,
)

st.caption(
    "LLM Only = no uploaded document context. "
    "Uploaded RAG Only = show what your documents retrieve. "
    "Both = retrieve your documents and ask the LLM to explain them."
)


if st.button("🚀 Get Answer", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    # -----------------------------
    # LLM Only
    # -----------------------------
    if source_mode == "LLM Only":
        with st.spinner("Generating LLM answer..."):
            answer, error = call_llm(question)

        if error:
            st.error(error)
        else:
            st.subheader("🤖 LLM Response")
            st.markdown(answer)

    # -----------------------------
    # RAG Only
    # -----------------------------
    elif source_mode == "Uploaded RAG Only":
        if not uploaded_chunks:
            st.warning("Please upload at least one RAG document first.")
            st.stop()

        retrieved = retrieve_knowledge(question, uploaded_chunks)

        st.subheader("📖 RAG Retrieved Results")

        if not retrieved:
            st.info(
                "No matching content was found in the uploaded documents."
            )
        else:
            for item in retrieved:
                with st.expander(item["source"], expanded=True):
                    st.write(item["text"])

    # -----------------------------
    # Both
    # -----------------------------
    else:
        if not uploaded_chunks:
            st.warning(
                "No RAG files are uploaded. The app will provide the LLM "
                "answer without document context."
            )

            with st.spinner("Generating LLM answer..."):
                answer, error = call_llm(question)

            if error:
                st.error(error)
            else:
                st.subheader("🤖 LLM Response")
                st.markdown(answer)

        else:
            retrieved = retrieve_knowledge(question, uploaded_chunks)

            st.subheader("📖 RAG Retrieved Results")

            if retrieved:
                for item in retrieved:
                    with st.expander(item["source"], expanded=True):
                        st.write(item["text"])

                rag_context = "\n\n".join(
                    f"SOURCE: {item['source']}\n{item['text']}"
                    for item in retrieved
                )
            else:
                st.info("No matching RAG content was found.")
                rag_context = ""

            with st.spinner("Generating LLM answer using RAG context..."):
                answer, error = call_llm(
                    question,
                    rag_context=rag_context if rag_context else None,
                )

            if error:
                st.error(error)
            else:
                st.subheader("🤖 LLM Response")
                st.markdown(answer)


st.divider()

st.caption(
    "Learning/demo project. Verify AI answers against real network "
    "evidence before taking operational action."
)
