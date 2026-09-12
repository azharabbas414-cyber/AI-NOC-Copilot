# AI-NOC Copilot

A lightweight beginner project that demonstrates how **Generative AI + simple RAG** can be used to help a Network Operations Center (NOC) engineer understand a network incident.

## Project Goal

The project is intentionally simple.

It is designed for learning the basic AI flow rather than building a production network automation platform.

```text
Network Incident
       ↓
Simple RAG Search
       ↓
Relevant NOC Knowledge
       ↓
Grok LLM
       ↓
AI Investigation
```

## What the application does

1. The user enters a network incident.
2. The application searches a small built-in NOC knowledge base.
3. The most relevant knowledge is selected.
4. The knowledge and incident are sent to Grok.
5. Grok provides:
   - Incident understanding
   - Probable root cause
   - Evidence
   - Recommended checks
   - Confidence

## What is NOT included

This beginner version deliberately does not include:

- SSH access
- Physical router/switch access
- Automatic configuration changes
- Network device APIs
- Complex workflow engines
- Vector databases
- Embedding infrastructure
- Large document ingestion pipelines
- Production monitoring
- Automatic remediation

These can be added later after the basic AI concepts are understood.

## Files

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.9+
- A Grok/xAI API key

## Run locally

Install the dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Set your API key as an environment variable.

### Linux/macOS

```bash
export XAI_API_KEY="your_api_key_here"
```

### Windows PowerShell

```powershell
$env:XAI_API_KEY="your_api_key_here"
```

Then start the application:

```bash
python3 app.py
```

Gradio will provide a local web address.

## API Key Security

Do **not** put the API key inside `app.py`.

Use the secret/environment variable name:

```text
XAI_API_KEY
```

Do not commit the actual API key to GitHub.

## Example incident

Try:

```text
Users are reporting high latency and packet loss.
The affected link also appears to have high traffic utilization.
```

The application should retrieve knowledge related to packet loss, latency, and congestion and then ask Grok to analyze the incident.

## RAG in this project

This project uses a deliberately simple form of Retrieval-Augmented Generation.

The built-in knowledge base contains short NOC troubleshooting topics such as:

- Packet Loss
- High Latency
- Congestion
- Interface Errors
- OSPF
- BGP
- VLAN
- MTU

The application looks for relevant keywords in the incident and retrieves matching knowledge.

That retrieved knowledge is then included in the prompt sent to Grok.

## Important note

This is a learning/demo project.

The AI output is advisory and should not be treated as proof of a network fault. A real NOC engineer should verify the suggested cause using actual network evidence before taking action.

## Next learning steps

After this simple version is working, the project can gradually evolve:

1. Improve RAG
2. Add uploaded network documents
3. Add embeddings
4. Add a vector database
5. Add structured incident data
6. Add evaluation/testing
7. Add workflow automation
8. Deploy the application online

The goal is to add **one concept at a time**, rather than making the first version unnecessarily complex.
