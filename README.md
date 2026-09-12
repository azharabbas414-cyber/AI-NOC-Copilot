# AI-NOC Copilot

Beginner-friendly AI NOC Copilot using RAG, Google Drive, and Groq.

## Features
- Fixed Google Drive knowledge source (configured once in `app.py`)
- Automatically loads supported TXT, PDF, and DOCX files from the Drive folder
- Simple RAG retrieval
- General AI mode
- Search My Documents mode
- Documents + AI mode
- Clear Results button
- No router/SSH access
- No automatic remediation

## Streamlit Cloud secrets
Add these in **Settings → Secrets**:

```toml
GROQ_API_KEY = "your-groq-api-key"
GOOGLE_DRIVE_API_KEY = "your-google-drive-api-key"
```

The Google Drive folder link is already fixed in `app.py`, so users do not need to paste it or upload the documents repeatedly.

The Drive folder must be accessible to the API key (for this beginner version, use a folder/files shared appropriately for link/API access). Private Drive content requiring OAuth is not included in this version.
