# AI-NOC-Copilot

AI-NOC Copilot is an AI-powered Network Operations assistant for NOC and
network engineers. It automates the initial investigation of network incidents
using network evidence, RAG-based knowledge, LLM reasoning, root-cause analysis,
confidence scoring, and troubleshooting recommendations.

## Current Milestone

**Step 5A — Automated AI Investigation Workflow**

The current prototype implements the investigation orchestration flow:

```text
Incident
   ↓
Validation
   ↓
Classification
   ↓
Network Data Analysis
   ↓
RAG Knowledge Retrieval
   ↓
Grok AI Reasoning (next integration)
   ↓
Root Cause Analysis
   ↓
Confidence
   ↓
Recommendations
   ↓
Investigation Report
   ↓
Human Validation
```

The current version uses simulated network telemetry and a small in-code NOC
knowledge base. Grok API integration and production-grade vector retrieval will
be added in the next implementation stages.

## Safety

This is a read-only prototype. It does not:

- SSH into routers
- Execute network commands
- Modify configurations
- Restart interfaces
- Automatically apply remediation

The final operational decision remains with the human network engineer.

## Project Structure

```text
AI-NOC-Copilot/
├── app.py
├── requirements.txt
└── README.md
```

## Technology

- Python
- Gradio
- Pandas
- Grok API (planned)
- RAG (progressive implementation)
- Vector search (progressive implementation)
- GitHub

## Development Roadmap

1. GitHub Repository — Complete
2. MVP Definition — Complete
3. PRD — Complete
4. RAG Design — Complete
5. Automated AI Investigation Workflow — In Progress
6. Grok API Integration
7. RAG Vector Search
8. Network Analysis Enhancement
9. Gradio UI Enhancement
10. Testing & Evaluation
11. Deployment
12. Hackathon Demo
