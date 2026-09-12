# AI-NOC-Copilot

A lightweight beginner AI project for learning **RAG + LLM** using Streamlit and Groq.

## Answer Modes

The application provides three clear options:

### 🧠 General AI

```text
Question → LLM → Answer
```

The question is answered using the LLM's general model knowledge.

**Important:** this does not mean live internet search.

### 📚 Search My Documents

```text
Question → RAG Retrieval → Retrieved Content
```

The application searches only the documents uploaded by the user and displays the relevant retrieved content.

This is useful for understanding and testing the RAG retrieval step.

### 🤖 Documents + AI

```text
Question
   ↓
Retrieve relevant uploaded document content
   ↓
RAG Context
   ↓
LLM
   ↓
Final Answer
```

This demonstrates the basic RAG + LLM pattern.

## RAG File Upload

Supported files:

- TXT
- PDF
- DOCX

The application:

1. Extracts text
2. Splits it into simple chunks
3. Searches the chunks using keyword matching
4. Shows the relevant chunks
5. Optionally sends those chunks to the LLM

## Clear Results

The **🗑️ Clear Results** button clears the previous question, retrieved RAG results, LLM response, and error message.

## Important

There are **no built-in NOC knowledge responses** in this version.

RAG uses only the documents that you upload.

## API Key

This project uses Groq.

In Streamlit Cloud → Settings → Secrets, add:

```toml
GROQ_API_KEY = "your_actual_groq_api_key"
```

The secret name must be exactly:

```text
GROQ_API_KEY
```

Never put the actual API key in `app.py` or GitHub.

## Streamlit Cloud

1. Push `app.py`, `requirements.txt`, and `README.md` to GitHub.
2. Create/open the Streamlit Cloud application.
3. Select `app.py` as the main file.
4. Go to Settings → Secrets.
5. Add the `GROQ_API_KEY` secret.
6. Save and reboot/redeploy if required.

## Example Test

Upload the NOC RAG test documents.

Ask:

```text
What can cause a BGP session to go down?
```

Then test each mode:

**🧠 General AI**

Shows the LLM's general answer without using your documents.

**📚 Search My Documents**

Shows what your uploaded documents retrieve.

**🤖 Documents + AI**

Shows the retrieved document content and the LLM's explanation based on that context.

## Current RAG Implementation

This is intentionally a beginner implementation:

```text
Document
   ↓
Text Extraction
   ↓
Simple Chunking
   ↓
Keyword Matching
   ↓
Relevant Chunks
   ↓
LLM (when Documents + AI is selected)
```

It does not yet use:

- Embeddings
- Vector databases
- Semantic search
- Agents
- Complex workflows
- Live web search

These can be added later as separate learning steps.

## Learning Goal

The main goal of this version is to understand the difference between:

```text
LLM
```

```text
RAG
```

and:

```text
RAG + LLM
```
