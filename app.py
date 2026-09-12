import os
import gradio as gr
import pandas as pd
from openai import OpenAI


# ============================================================
# Grok configuration
# ============================================================
XAI_API_KEY = os.getenv("XAI_API_KEY")
GROK_MODEL = "grok-4.6"


def get_grok_client():
    if not XAI_API_KEY:
        return None
    return OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://api.x.ai/v1",
    )


# ============================================================
# Sample network telemetry
# ============================================================
SAMPLE_NETWORK_DATA = pd.DataFrame(
    [
        {
            "device": "PE-RTR-01",
            "interface": "Eth-Trunk2.1793",
            "latency_ms": 180,
            "packet_loss": 8,
            "utilization": 94,
            "input_errors": 0,
            "output_errors": 12,
            "crc_errors": 0,
            "status": "UP",
            "queue_drops": "HIGH",
        },
        {
            "device": "PE-RTR-02",
            "interface": "Eth-Trunk2.1793",
            "latency_ms": 175,
            "packet_loss": 7,
            "utilization": 92,
            "input_errors": 0,
            "output_errors": 9,
            "crc_errors": 0,
            "status": "UP",
            "queue_drops": "HIGH",
        },
    ]
)


# ============================================================
# Step 1: Validate incident
# ============================================================
def validate_incident(incident):
    incident = (incident or "").strip()

    if not incident:
        return False, "Incident description is empty."

    if len(incident) < 10:
        return False, "Please provide a more descriptive incident."

    return True, "Incident validated successfully."


# ============================================================
# Step 2: Classify incident
# ============================================================
def classify_incident(incident):
    text = incident.lower()

    if any(word in text for word in ["packet loss", "packet drop", "latency", "slow"]):
        incident_type = "Performance"
    elif any(word in text for word in ["bgp", "route", "routing", "ospf"]):
        incident_type = "Routing"
    elif any(word in text for word in ["vlan", "stp", "loop", "switch"]):
        incident_type = "Switching"
    elif any(word in text for word in ["interface", "crc", "link down", "error"]):
        incident_type = "Interface"
    else:
        incident_type = "General Network"

    severity = "High" if any(
        word in text for word in ["packet loss", "link down", "down", "outage"]
    ) else "Medium"

    return incident_type, severity


# ============================================================
# Step 3: Analyze network data
# ============================================================
def analyze_network_data(data):
    findings = []

    if data.empty:
        return ["No network telemetry was provided."]

    avg_latency = data["latency_ms"].mean()
    avg_loss = data["packet_loss"].mean()
    avg_utilization = data["utilization"].mean()
    total_output_errors = data["output_errors"].sum()
    total_crc = data["crc_errors"].sum()

    if avg_latency > 100:
        findings.append(f"High latency detected: {avg_latency:.0f} ms.")

    if avg_loss > 1:
        findings.append(f"Packet loss detected: {avg_loss:.1f}%.")

    if avg_utilization > 80:
        findings.append(f"High interface utilization: {avg_utilization:.1f}%.")

    if total_output_errors > 0:
        findings.append(f"Output errors detected: {total_output_errors}.")

    if total_crc > 0:
        findings.append(f"CRC errors detected: {total_crc}.")
    else:
        findings.append("No CRC errors detected in supplied telemetry.")

    if (data["queue_drops"] == "HIGH").any():
        findings.append("High queue drops detected.")

    return findings


# ============================================================
# Step 4: RAG knowledge base
# ============================================================
KNOWLEDGE_BASE = [
    {
        "topic": "Packet Loss",
        "category": "Performance",
        "content": (
            "Packet loss can be associated with congestion, interface errors, "
            "QoS queue drops, MTU problems, or routing issues. Check utilization, "
            "errors, queue drops, latency, and routing evidence."
        ),
    },
    {
        "topic": "Network Congestion",
        "category": "QoS",
        "content": (
            "High utilization combined with packet loss, increased latency, "
            "and queue drops may indicate network congestion. Check traffic "
            "patterns, QoS policies, queues, and available capacity."
        ),
    },
    {
        "topic": "Interface Errors",
        "category": "Interface",
        "content": (
            "Input/output errors and CRC errors can indicate interface or "
            "physical/link problems. Correlate error counters with packet loss "
            "and interface status."
        ),
    },
    {
        "topic": "High Latency",
        "category": "Performance",
        "content": (
            "High latency may result from congestion, routing path changes, "
            "queueing, or transport problems. Compare latency with utilization "
            "and packet-loss evidence."
        ),
    },
]


def retrieve_rag_knowledge(incident, top_k=3):
    text = incident.lower()
    scored = []

    for item in KNOWLEDGE_BASE:
        score = 0
        searchable = (
            item["topic"].lower()
            + " "
            + item["category"].lower()
            + " "
            + item["content"].lower()
        )

        for keyword in text.split():
            keyword = keyword.strip(".,!?;:\"'()")
            if len(keyword) >= 4 and keyword in searchable:
                score += 1

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for score, item in scored[:top_k] if score > 0]

    if not selected:
        selected = KNOWLEDGE_BASE[:top_k]

    return selected


# ============================================================
# Step 5: Grok AI reasoning
# ============================================================
def analyze_with_grok(
    incident,
    incident_type,
    severity,
    findings,
    retrieved_knowledge,
):
    client = get_grok_client()

    if client is None:
        return {
            "status": "Grok API key not configured.",
            "analysis": (
                "Grok analysis was not executed. Add the XAI_API_KEY environment "
                "secret before running the AI investigation."
            ),
            "root_cause": "Unavailable",
            "confidence": 0,
            "recommendations": [
                "Configure XAI_API_KEY and rerun the investigation."
            ],
        }

    evidence_text = "\n".join(f"- {item}" for item in findings)
    rag_text = "\n".join(
        f"- {item['topic']} ({item['category']}): {item['content']}"
        for item in retrieved_knowledge
    )

    prompt = f"""
You are an expert Telecom NOC and Network Operations Copilot.

Investigate the following network incident using ONLY the supplied incident,
observed evidence, and retrieved knowledge as the primary context.

IMPORTANT SAFETY RULES:
- Do not claim certainty when evidence is insufficient.
- Clearly distinguish observed evidence from inference.
- Do not invent telemetry, logs, configurations, or alarms.
- Do not recommend automatic network changes.
- All operational actions require human engineer validation.

INCIDENT:
{incident}

CLASSIFICATION:
Type: {incident_type}
Severity: {severity}

OBSERVED NETWORK EVIDENCE:
{evidence_text}

RETRIEVED RAG KNOWLEDGE:
{rag_text}

Return a concise investigation with these sections:

PROBABLE ROOT CAUSE:
CONFIDENCE:
OBSERVED EVIDENCE:
REASONING:
POSSIBLE IMPACT:
RECOMMENDED TROUBLESHOOTING:
MISSING INFORMATION:
HUMAN DECISION:
"""

    try:
        response = client.responses.create(
            model=GROK_MODEL,
            input=prompt,
        )

        text = response.output_text.strip()

        return {
            "status": f"Grok {GROK_MODEL} analysis completed.",
            "analysis": text,
            "root_cause": "See Grok analysis",
            "confidence": 0,
            "recommendations": [
                "Review the Grok recommendations and validate them against live network evidence."
            ],
        }

    except Exception as exc:
        return {
            "status": "Grok API request failed.",
            "analysis": f"Grok API error: {exc}",
            "root_cause": "Unavailable",
            "confidence": 0,
            "recommendations": [
                "Check the XAI_API_KEY, API access/credits, model availability, and network connectivity."
            ],
        }


# ============================================================
# Step 6: Report
# ============================================================
def generate_report(
    incident,
    incident_type,
    severity,
    findings,
    retrieved,
    grok_result,
):
    evidence = "\n".join(f"- {item}" for item in findings)
    knowledge = "\n".join(
        f"- {item['topic']} ({item['category']})" for item in retrieved
    )

    return f"""# AI-NOC Copilot Investigation Report

## Incident
{incident}

## Classification
- Type: {incident_type}
- Severity: {severity}

## Observed Evidence
{evidence}

## Retrieved NOC Knowledge
{knowledge}

## Grok AI Investigation
{grok_result["analysis"]}

## Human Decision
**Engineer validation is required before any operational action.**

> Read-only AI investigation. No router commands or configuration changes are
> executed by this application.
"""


# ============================================================
# Complete automated workflow
# ============================================================
def run_investigation(incident):
    valid, validation_message = validate_incident(incident)

    if not valid:
        return validation_message, "", "", "", ""

    incident_type, severity = classify_incident(incident)
    findings = analyze_network_data(SAMPLE_NETWORK_DATA)
    retrieved = retrieve_rag_knowledge(incident)

    grok_result = analyze_with_grok(
        incident,
        incident_type,
        severity,
        findings,
        retrieved,
    )

    workflow_status = (
        "1. Incident validated ✓\n"
        "2. Incident classified ✓\n"
        "3. Network data analyzed ✓\n"
        "4. RAG knowledge retrieved ✓\n"
        f"5. {grok_result['status']}\n"
        "6. AI investigation completed ✓\n"
        "7. Human validation required"
    )

    evidence_output = (
        f"Incident Type: {incident_type}\n"
        f"Severity: {severity}\n\n"
        "Observed Evidence:\n"
        + "\n".join(f"- {item}" for item in findings)
    )

    rag_output = "\n".join(
        f"• {item['topic']} — {item['category']}\n  {item['content']}"
        for item in retrieved
    )

    report = generate_report(
        incident,
        incident_type,
        severity,
        findings,
        retrieved,
        grok_result,
    )

    return (
        workflow_status,
        evidence_output + "\n\nGrok AI Analysis:\n" + grok_result["analysis"],
        rag_output,
        "\n".join(f"- {item}" for item in grok_result["recommendations"]),
        report,
    )


# ============================================================
# Gradio UI
# ============================================================
with gr.Blocks(title="AI-NOC Copilot") as demo:
    gr.Markdown(
        """
        # 🤖 AI-NOC Copilot
        ### Automated AI Network Incident Investigation

        **Incident → Analysis → RAG → Grok → RCA → Recommendations → Human Decision**
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown(
                """
                ### 📡 Investigation Workflow

                1. 🚨 Incident Validation
                2. 🏷️ Classification
                3. 📊 Network Analysis
                4. 🧠 RAG Retrieval
                5. 🤖 Grok Reasoning
                6. 🔍 Root Cause Analysis
                7. 📈 Confidence
                8. 💡 Recommendations
                9. 👤 Human Review
                """
            )

        with gr.Column(scale=3):
            incident_input = gr.Textbox(
                label="Network Incident",
                placeholder=(
                    "Example: Users are experiencing high latency and "
                    "8% packet loss on the WAN link."
                ),
                lines=5,
            )

            investigate_button = gr.Button(
                "🚀 Start Automated Investigation",
                variant="primary",
            )

    workflow_status = gr.Textbox(label="Workflow Status", lines=8)
    analysis_output = gr.Textbox(label="AI Investigation", lines=18)
    rag_output = gr.Textbox(label="Retrieved NOC Knowledge (RAG)", lines=10)
    recommendation_output = gr.Textbox(
        label="Troubleshooting Recommendations",
        lines=8,
    )
    report_output = gr.Markdown()

    investigate_button.click(
        fn=run_investigation,
        inputs=incident_input,
        outputs=[
            workflow_status,
            analysis_output,
            rag_output,
            recommendation_output,
            report_output,
        ],
    )

    gr.Markdown(
        """
        ---
        🔒 **Read-only prototype:** No SSH, physical router access,
        configuration changes, or automatic remediation.
        """
    )


if __name__ == "__main__":
    demo.launch()
