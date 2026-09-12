# AI-NOC-Copilot

A lightweight beginner AI project for learning **Generative AI + RAG** in a Network Operations Center (NOC) scenario.

This version uses **Streamlit** and a Groq-hosted LLM.

## Simple Architecture

```text
Upload NOC Documents
        ↓
     Chunking
        ↓
Simple Keyword RAG
        ↓
Retrieved Context
        ↓
     Groq LLM
        ↓
AI Investigation
```

## What you will learn

- How an LLM API is called from Python
- What RAG means
- Basic document loading
- Basic chunking
- Basic retrieval
- How retrieved context is passed to an LLM
- How AI can analyze a network incident
- How to deploy an AI application on Streamlit Community Cloud

## Files

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

Only these three files are required.

## RAG File Upload

The application accepts:

- TXT
- PDF
- DOCX

Uploaded documents are:

1. Read
2. Split into simple text chunks
3. Searched using keyword matching
4. Relevant chunks are sent to the LLM as context

This is intentionally a simple first RAG implementation. It does not yet use embeddings or a vector database.

## API Key

This version uses the secret name:

```text
GROQ_API_KEY
```

Do not put the actual API key in `app.py` or GitHub.

## Streamlit Cloud Secrets

In your Streamlit Cloud app:

**Settings → Secrets**

Add:

```toml
GROQ_API_KEY = "your_actual_groq_api_key"
```

The secret name must be exactly:

```text
GROQ_API_KEY
```

## Run Locally

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Set your API key.

### Linux/macOS

```bash
export GROQ_API_KEY="your_api_key_here"
```

### Windows PowerShell

```powershell
$env:GROQ_API_KEY="your_api_key_here"
```

Run:

```bash
streamlit run app.py
```

## Example Test

Upload the provided NOC test documents and enter:

```text
Users are experiencing packet loss and high latency.
The interface utilization is around 95 percent and output drops are increasing.
```

The RAG system should retrieve information related to packet loss and congestion.

Another test:

```text
The OSPF neighbor went down and routes learned from that neighbor disappeared.
```

The RAG system should retrieve the OSPF knowledge.

## What is intentionally NOT included

This beginner version does not include:

- SSH
- Physical routers/switches
- Automatic configuration
- Network device APIs
- Vector databases
- Embeddings
- Complex workflow engines
- Automatic remediation

These can be added later as separate learning steps.

## Important

This is a learning/demo project.

The AI output is advisory. A real NOC engineer should verify the suggested root cause and recommendations using actual network evidence before taking action.

## Next Learning Steps

After this version works:

1. Understand the current RAG flow.
2. Test different incidents and documents.
3. Improve chunking.
4. Learn embeddings.
5. Replace keyword search with vector search.
6. Add better document processing.
7. Learn RAG evaluation.
8. Add workflow automation later.
