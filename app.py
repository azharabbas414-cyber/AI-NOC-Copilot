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
# 1. Extract text from uploaded files
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


# =========================================================
# 2. Simple chunking
# =========================================================
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

Answer the user's question using the retrieved content from the user's
uploaded RAG documents.

USER QUESTION:
{question}

RETRIEVED RAG CONTENT:
{rag_context}

Rules:
- Use the uploaded RAG content as the primary source.
- Clearly explain the answer.
- Do not invent information that is not supported by the context.
- If the retrieved content does not contain enough information, say so.
- Do not invent device output or network measurements.
"""
    else:
        prompt = f"""
You are an AI NOC Copilot.

Answer the user's question using your general model knowledge.

USER QUESTION:
{question}

Rules:
- Give a clear and useful answer.
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
# 5. Clear function
# =========================================================
def clear_results():
    st.session_state.question = ""
    st.session_state.answer = ""
    st.session_state.rag_results = []
    st.session_state.error = ""


# =========================================================
# 6. Page configuration
# =========================================================
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="🤖",
    layout="centered",
)

# Session state
if "question" not in st.session_state:
    st.session_state.question = ""

if "answer" not in st.session_state:
    st.session_state.answer = ""

if "rag_results" not in st.session_state:
    st.session_state.rag_results = []

if "error" not in st.session_state:
    st.session_state.error = ""


# =========================================================
# 7. UI
# =========================================================
st.title("🤖 AI-NOC Copilot")

st.write(
    "A beginner AI project for learning **RAG + LLM** using your own "
    "NOC documents."
)

st.info(
    "Flow: Upload Documents → Ask Question → Select Source → Retrieve → Answer"
)


# ---------------------------------------------------------
# Upload documents
# ---------------------------------------------------------
st.subheader("📚 Upload RAG Documents")

uploaded_files = st.file_uploader(
    "Upload your NOC knowledge files",
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
            st.warning(
                f"{uploaded_file.name}: no readable text was found."
            )

# ---------------------------------------------------------
# Question
# ---------------------------------------------------------
st.subheader("📝 Ask Your Question")

question = st.text_area(
    "Question",
    value=st.session_state.question,
    placeholder="Example: What can cause a BGP session to go down?",
    height=120,
    key="question_input",
)

# ---------------------------------------------------------
# Answer mode
# ---------------------------------------------------------
source_mode = st.radio(
    "How should the answer be generated?",
    options=[
        "🧠 General AI",
        "📚 Search My Documents",
        "🤖 Documents + AI",
    ],
    index=2,
)

st.caption(
    "🧠 General AI = answer using the LLM's general model knowledge. "
    "📚 Search My Documents = search only your uploaded RAG documents. "
    "🤖 Documents + AI = retrieve your documents and let the LLM explain them."
)

# ---------------------------------------------------------
# Buttons
# ---------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    analyze_clicked = st.button(
        "🚀 Get Answer",
        type="primary",
        use_container_width=True,
    )

with col2:
    clear_clicked = st.button(
        "🗑️ Clear Results",
        use_container_width=True,
    )

if clear_clicked:
    st.session_state.question = ""
    st.session_state.answer = ""
    st.session_state.rag_results = []
    st.session_state.error = ""
    st.rerun()


# ---------------------------------------------------------
# Process question
# ---------------------------------------------------------
if analyze_clicked:
    current_question = question.strip()

    if not current_question:
        st.warning("Please enter a question.")
    else:
        st.session_state.question = current_question
        st.session_state.answer = ""
        st.session_state.rag_results = []
        st.session_state.error = ""

        # -----------------------------
        # LLM Only
        # -----------------------------
        if source_mode == "🧠 General AI":
            with st.spinner("Generating LLM response..."):
                answer, error = call_llm(current_question)

            if error:
                st.session_state.error = error
            else:
                st.session_state.answer = answer

        # -----------------------------
        # RAG Only
        # -----------------------------
        elif source_mode == "📚 Search My Documents":
            if not uploaded_chunks:
                st.session_state.error = (
                    "Please upload at least one RAG document first."
                )
            else:
                results = retrieve_knowledge(
                    current_question,
                    uploaded_chunks,
                )
                st.session_state.rag_results = results

                if not results:
                    st.session_state.error = (
                        "No relevant content was found in the uploaded documents."
                    )

        # -----------------------------
        # Both RAG + LLM
        # -----------------------------
        else:
            if not uploaded_chunks:
                st.warning(
                    "No RAG documents uploaded. The LLM will answer "
                    "without document context."
                )

                with st.spinner("Generating LLM response..."):
                    answer, error = call_llm(current_question)

                if error:
                    st.session_state.error = error
                else:
                    st.session_state.answer = answer

            else:
                results = retrieve_knowledge(
                    current_question,
                    uploaded_chunks,
                )
                st.session_state.rag_results = results

                if results:
                    rag_context = "\n\n".join(
                        f"SOURCE: {item['source']}\n{item['text']}"
                        for item in results
                    )
                else:
                    rag_context = ""

                with st.spinner("Generating answer using RAG + LLM..."):
                    answer, error = call_llm(
                        current_question,
                        rag_context=rag_context if rag_context else None,
                    )

                if error:
                    st.session_state.error = error
                else:
                    st.session_state.answer = answer


# =========================================================
# 8. Display results
# =========================================================
if st.session_state.error:
    st.error(st.session_state.error)

    if st.session_state.error == "GROQ_API_KEY is not configured.":
        st.info(
            "Add GROQ_API_KEY in Streamlit Cloud → Settings → Secrets."
        )


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
    "Learning/demo project. Verify AI answers against real network "
    "evidence before taking operational action."
)
