# AI-NOC-Copilot

## AI-NOC Copilot

AI-NOC Copilot is an AI-powered Network Operations assistant designed to help NOC
and network engineers investigate network incidents, identify probable root
causes, and receive intelligent troubleshooting recommendations.

## Project Category

**Telecom / Network + Generative AI + Workflow Automation**

## Planned AI Investigation Workflow

```text
Incident Input
      ↓
Input Validation
      ↓
Incident Classification
      ↓
Network Data Analysis
      ↓
RAG Knowledge Retrieval
      ↓
Grok AI Analysis
      ↓
Root Cause Analysis
      ↓
Confidence Assessment
      ↓
Recommendations
      ↓
Investigation Report
      ↓
Human Engineer Decision
```

## Safety

This is a **read-only NOC Copilot**. It will not SSH into routers, execute
commands, modify configurations, restart interfaces, or automatically apply
remediation. The final decision remains with the human network engineer.

## Current Version

**Step 1 — Initial Gradio UI**

The current version provides a basic Gradio interface for submitting a network
incident. Grok API, RAG, network data analysis, and automated investigation will
be added in later development steps.

## Technology

- Python
- Gradio
- Grok API
- RAG
- Vector database
- Pandas
- GitHub

## Project Structure

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

## Development Roadmap

1. Create GitHub Repository
2. MVP
3. PRD
4. RAG
5. AI Workflow Automation
6. Grok API Integration
7. Network Analysis
8. Testing & Evaluation
9. Deployment
10. Hackathon Demo
