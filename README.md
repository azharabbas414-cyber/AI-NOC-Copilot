# AI-NOC Copilot

Beginner-friendly AI NOC Copilot using RAG, Google Drive, Groq, and simple network-data analysis.

## Features
- Fixed Google Drive knowledge source (configured once in `app.py`)
- Automatically loads supported TXT, PDF, and DOCX files from the Drive folder
- Simple focused RAG retrieval
- AI Response, RAG Response, and RAG + AI Comparison
- Automatic incident classification
- Network Health using uploaded CSV metrics
- Shift Handover Assistant using the Groq-hosted LLM
- NOC Incident Report Generator
- Clear, human-in-the-loop workflow
- No router/SSH access
- No automatic remediation

## Streamlit Cloud secrets
Add these in **Settings → Secrets**:

```toml
GROQ_API_KEY = "your-groq-api-key"
GOOGLE_DRIVE_API_KEY = "your-google-drive-api-key"
```

The Google Drive folder link is already fixed in `app.py`, so users do not need to paste it or upload the knowledge documents repeatedly.

The Drive folder must be accessible to the API key. Private Drive content requiring OAuth is not included in this beginner version.

## Modules

- Incident Analysis
- Network Health
- Shift Handover Assistant
- NOC Report Generator

### Incident Analysis
Enter a network question or incident and choose AI Response, RAG Response, or RAG + AI Comparison. The RAG retriever focuses on relevant NOC knowledge and avoids unrelated chunks.

### Network Health
Upload a CSV with `Interface`, `Utilization`, `Packet Loss`, and `CRC Errors`, then click **Generate Health Check Summary**. The app uses simple demo thresholds to classify interfaces as Healthy, Attention, or Investigate.

### Shift Handover Assistant
Enter shift information, handled incidents, ongoing issues, pending actions, and important notes. The Groq-hosted LLM creates a concise handover summary for the next NOC engineer. The AI is instructed not to invent information.

### NOC Report Generator
Enter incident subject, summary, start/end time, root cause, services impacted, and recommendations. The app creates a structured downloadable Markdown incident report.

## Current AI model
The current implementation uses the Groq API with `openai/gpt-oss-20b` through an OpenAI-compatible API endpoint.

## Project structure

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```
