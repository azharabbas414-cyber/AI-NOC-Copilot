# AI-NOC-Copilot

Beginner-friendly AI-NOC Copilot using RAG + Groq LLM.

## Project structure

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

## Google Drive knowledge base

This version uses **one fixed Google Drive file/folder source**.
You do **not** need to paste the Drive link or upload the documents again on every run.

Open `app.py` and set this once:

```python
FIXED_GOOGLE_DRIVE_URL = "YOUR_GOOGLE_DRIVE_FILE_OR_FOLDER_LINK"
```

The app then loads that source automatically when `🔗 Fixed Google Drive` is selected.
The Drive loader is cached for 1 hour, so normal Streamlit UI reruns do not repeatedly download the same files.

Supported Drive content in this beginner version: TXT, PDF, DOCX, plus Google Docs exported as text.

The Drive source must be accessible to the configured Google Drive API key. Private personal Drive content requires OAuth and is not covered by this simple API-key version.

## Streamlit secrets

Add:

```toml
GROQ_API_KEY = "your_groq_key"
GOOGLE_DRIVE_API_KEY = "your_google_drive_api_key"
```

Never commit API keys to GitHub.

## Run locally

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```
