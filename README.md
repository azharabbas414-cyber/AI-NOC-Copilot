# AI-NOC-Copilot

A lightweight beginner AI project for learning **LLM + RAG** using Streamlit and Groq.

## Main Feature

You can now choose how a question should be answered:

```text
1. LLM Only
2. Uploaded RAG Only
3. Both: RAG + LLM
```

### 1. LLM Only

The question is sent directly to the LLM without using your uploaded RAG documents.

This demonstrates a normal LLM question/answer.

**Note:** This option does not mean live internet search. It uses the model's available knowledge, not a real-time web search.

### 2. Uploaded RAG Only

The application searches the uploaded TXT/PDF/DOCX files and displays the retrieved information.

This lets you see what the RAG system actually found before involving the LLM.

### 3. Both: RAG + LLM

The application retrieves relevant information from your uploaded documents and then sends that context to the LLM.

This demonstrates the basic RAG pattern:

```text
Question
   ↓
Retrieve relevant document content
   ↓
Add retrieved content to prompt
   ↓
LLM
   ↓
Answer
```

## Supported RAG Files

- TXT
- PDF
- DOCX

## Project Files

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

## API Key

This project uses Groq.

Create/configure your Groq API key and add it to Streamlit Cloud Secrets using exactly:

```toml
GROQ_API_KEY = "your_actual_groq_api_key"
```

Do not commit the API key to GitHub.

## Streamlit Cloud

1. Push `app.py`, `requirements.txt`, and `README.md` to GitHub.
2. Create/open the Streamlit Cloud application.
3. Select `app.py` as the main file.
4. Add `GROQ_API_KEY` under Settings → Secrets.
5. Deploy/reboot the application.

## Example Test

Upload a packet-loss/congestion document and ask:

```text
What could cause packet loss when interface utilization is around 95 percent?
```

Try all three modes:

### LLM Only

The answer comes from the LLM without your uploaded document.

### Uploaded RAG Only

You see the relevant text retrieved from your uploaded document.

### Both: RAG + LLM

You see the retrieved document content and then the LLM explains the answer using that context.

## Important Learning Point

This version intentionally uses simple keyword retrieval.

It does NOT yet use:

- Embeddings
- Vector databases
- Semantic search
- Web search
- Agents
- Complex workflows

Those can be added later as separate learning steps.

## Future Enhancement: Live Internet Search

If you specifically want:

```text
LLM Only
RAG Only
Internet + LLM
RAG + Internet + LLM
```

we can add a web-search API as a separate next step.

That is different from "LLM Only": an LLM by itself does not automatically perform live internet searches.
