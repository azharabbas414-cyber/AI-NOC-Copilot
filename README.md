# AI-NOC-Copilot

A lightweight beginner AI project for learning **Generative AI and RAG** in a Network Operations Center (NOC) scenario.

The application uses a simple Streamlit interface and the Grok API.

## Simple Architecture

```text
User Incident
      ↓
Simple RAG Search
      ↓
Relevant NOC Knowledge
      ↓
Grok LLM
      ↓
AI Investigation
```

## What you will learn

- How an LLM API is called from Python
- What RAG means
- How retrieval can provide context to an LLM
- How a prompt is constructed
- How AI can analyze a network incident
- How to deploy a simple AI application on Streamlit Community Cloud

## Project Files

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

Only these three files are required.

## Features

The application can analyze simple incidents involving:

- Packet Loss
- High Latency
- Congestion
- Interface Errors
- OSPF
- BGP
- VLAN
- MTU

It returns:

- Incident Understanding
- Probable Root Cause
- Evidence
- Recommended Checks
- Confidence

## What is intentionally NOT included

This is a beginner project, so it does not include:

- SSH
- Physical routers or switches
- Automatic configuration
- Network device APIs
- Vector databases
- Embeddings
- Complex document ingestion
- Complex workflow automation
- Automatic remediation

These can be learned and added later.

# Run Locally

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Set the API key.

### Linux/macOS

```bash
export XAI_API_KEY="your_api_key_here"
```

### Windows PowerShell

```powershell
$env:XAI_API_KEY="your_api_key_here"
```

Run:

```bash
streamlit run app.py
```

# Streamlit Cloud Deployment

1. Push the three files to your GitHub repository.
2. Open Streamlit Community Cloud.
3. Create a new app.
4. Select your GitHub repository.
5. Select `app.py` as the main file.
6. Deploy the app.
7. Open the app's **Settings/Secrets** section.
8. Add this secret:

```toml
XAI_API_KEY = "your_actual_xai_api_key"
```

The secret name must be exactly:

```text
XAI_API_KEY
```

Do not put the actual API key in `app.py` or commit it to GitHub.

After adding the secret, restart/redeploy the application if required.

## Example Incident

Try:

```text
Users are reporting high latency and packet loss.
The affected link also appears to have high traffic utilization.
```

The RAG step should retrieve knowledge about latency, packet loss, and congestion. Grok then uses that context to produce the investigation.

## How the RAG works

This first version uses **very simple keyword retrieval**.

For example, if the incident contains:

```text
packet loss and high latency
```

the program searches the built-in knowledge base and retrieves matching topics.

That retrieved information is added to the Grok prompt.

This is RAG at a beginner level:

```text
Retrieve → Add Context → Generate
```

Later, the keyword search can be replaced with embeddings and a vector database.

## Important

This is a learning/demo project.

The AI output is advisory. A real NOC engineer should verify the suggested root cause and recommendations using actual network evidence before taking action.

## Suggested Learning Path

After this version works:

1. Understand the current RAG code.
2. Test different incidents.
3. Improve the knowledge base.
4. Learn embeddings.
5. Replace keyword retrieval with vector search.
6. Add document-based RAG.
7. Learn evaluation.
8. Add workflow automation later.
