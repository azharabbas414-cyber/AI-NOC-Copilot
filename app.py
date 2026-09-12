import os
import re
import streamlit as st
from openai import OpenAI

# Optional libraries used only for uploaded PDF/DOCX files.
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


# ---------------------------------------------------------
# 1. Small built-in NOC knowledge base
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 2. Read uploaded documents
# ---------------------------------------------------------
def extract_text(uploaded_file):
    """Extract text from TXT, PDF, or DOCX."""
    filename = uploaded_file.name.lower()

    if filename.endswith(".txt"):
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):
        if PdfReader is None:
            return ""
        reader = PdfReader(uploaded_file)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)

    if filename.endswith(".docx"):
        if Document is None:
            return ""
        document = Document(uploaded_file)
        return "\n".join(p.text for p in document.paragraphs)

    return ""


def split_into_chunks(text, chunk_size=700):
    """Very simple chunking for beginner RAG."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


# ---------------------------------------------------------
# 3. Simple RAG retrieval
# ---------------------------------------------------------
def keywords(text):
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def retrieve_knowledge(incident, uploaded_chunks, top_k=4):
    """Keyword-based retrieval. No vector database or embeddings yet."""
    query_words = keywords(incident)
    candidates = []

    # Built-in knowledge
    for item in BUILT_IN_KNOWLEDGE:
        text_words = keywords(item["topic"] + " " + item["text"])
        score = len(query_words.intersection(text_words))

        if score > 0:
            candidates.append(
                (score, f"Built-in: {item['topic']}", item["text"])
            )

    # Uploaded document chunks
    for number, chunk in enumerate(uploaded_chunks, start=1):
        chunk_words = keywords(chunk)
        score = len(query_words.intersection(chunk_words))

        if score > 0:
            candidates.append(
                (score, f"Uploaded document - chunk {number}", chunk)
            )

    candidates.sort(key=lambda x: x[0], reverse=True)

    if not candidates:
        return [{
            "source": "General troubleshooting",
            "text": (
                "Start with the incident time, affected service/device, "
                "interface status, traffic utilization, errors, logs, and "
                "recent configuration or routing changes."
            )
        }]

    return [
        {"source": source, "text": text}
        for _, source, text in candidates[:top_k]
    ]


# ---------------------------------------------------------
# 4. Call Grok
# ---------------------------------------------------------
def analyze_with_grok(incident, retrieved):
    # Streamlit Cloud Secrets
    try:
        api_key = st.secrets["XAI_API_KEY"]
    except Exception:
        api_key = os.getenv("XAI_API_KEY")

    if not api_key:
        return None, "XAI_API_KEY is not configured."

    context = "\n\n".join(
        f"SOURCE: {item['source']}\n{item['text']}"
        for item in retrieved
    )

    prompt = f"""
You are a beginner-friendly AI NOC Copilot.

Analyze this network incident using the retrieved knowledge.

INCIDENT:
{incident}

RETRIEVED KNOWLEDGE:
{context}

Return these sections:

### Incident Understanding
Explain what appears to be happening.

### Probable Root Cause
Give the most likely cause. Clearly say if the evidence is insufficient.

### Evidence
List the important clues.

### Recommended Checks
Give 3 to 5 practical checks for an NOC engineer.

### Confidence
Give High, Medium, or Low confidence and explain why.

Rules:
- Use the retrieved knowledge when relevant.
- Do not invent device output or measurements.
- Do not claim certainty without evidence.
- Do not make automatic configuration changes.
- Keep the explanation simple.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        response = client.responses.create(
            model="grok-4.6",
            input=prompt,
        )

        return response.output_text, None

    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------
# 5. Streamlit UI
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 AI-NOC Copilot")
st.write(
    "Beginner AI project demonstrating **RAG + Grok** "
    "for network incident analysis."
)

st.info("Flow: Upload Knowledge → Incident → RAG → Grok → AI Analysis")

st.subheader("📚 Upload RAG Knowledge")

uploaded_files = st.file_uploader(
    "Upload NOC documents",
    type=["txt", "pdf", "docx"],
    accept_multiple_files=True,
    help="Upload TXT, PDF, or DOCX files containing NOC/network knowledge.",
)

uploaded_chunks = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        text = extract_text(uploaded_file)

        if text.strip():
            chunks = split_into_chunks(text)
            uploaded_chunks.extend(chunks)
            st.success(
                f"{uploaded_file.name}: loaded {len(chunks)} text chunk(s)."
            )
        else:
            st.warning(
                f"{uploaded_file.name}: no readable text was found."
            )

st.subheader("📝 Network Incident")

incident = st.text_area(
    "Enter the incident",
    placeholder=(
        "Example: Users are reporting high latency and packet loss "
        "on a congested link."
    ),
    height=150,
)

if st.button("🔍 Analyze Incident", type="primary"):
    if not incident.strip():
        st.warning("Please enter a network incident.")
    else:
        retrieved = retrieve_knowledge(
            incident,
            uploaded_chunks,
        )

        st.subheader("📖 Retrieved RAG Context")

        for item in retrieved:
            with st.expander(item["source"], expanded=True):
                st.write(item["text"])

        with st.spinner("Grok is analyzing the incident..."):
            answer, error = analyze_with_grok(incident, retrieved)

        if error:
            st.error(error)

            if error == "XAI_API_KEY is not configured.":
                st.info(
                    "Add XAI_API_KEY in Streamlit Cloud → Settings → Secrets."
                )
        else:
            st.subheader("🤖 AI Investigation")
            st.markdown(answer)

st.divider()

st.caption(
    "Learning/demo project. Verify AI recommendations against real "
    "network evidence before taking action."
)
