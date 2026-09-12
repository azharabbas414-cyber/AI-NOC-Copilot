import gradio as gr
import pandas as pd


# -----------------------------
# Sample network telemetry
# -----------------------------
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


# -----------------------------
# Step 1: Validate incident
# -----------------------------
def validate_incident(incident):
    incident = (incident or "").strip()

    if not incident:
        return False, "Incident description is empty."

    if len(incident) < 10:
        return False, "Please provide a more descriptive incident."

    return True, "Incident validated successfully."


# -----------------------------
# Step 2: Classify incident
# -----------------------------
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


# -----------------------------
# Step 3: Analyze network data
# -----------------------------
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


# -----------------------------
# Step 4: Initial RAG retrieval
# Step 5 will replace this with
# a real vector-search + Grok flow.
# -----------------------------
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
            keyword = keyword.strip(".,!?;:"'()")
            if len(keyword) >= 4 and keyword in searchable:
                score += 1

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [item for score, item in scored[:top_k] if score > 0]

    if not selected:
        selected = KNOWLEDGE_BASE[:top_k]

    return selected


# -----------------------------
# Step 6: Evidence-based RCA
# -----------------------------
def generate_root_cause(findings):
    finding_text = " ".join(findings).lower()

    if (
        "high interface utilization" in finding_text
        and "packet loss detected" in finding_text
        and "high queue drops detected" in finding_text
    ):
        return (
            "Network congestion",
            91,
            "High utilization, packet loss, and high queue drops are correlated. "
            "No CRC errors were observed, which makes interface/physical errors "
            "less likely based on the supplied telemetry.",
        )

    if "crc errors detected" in finding_text:
        return (
            "Possible interface/physical-link issue",
            82,
            "CRC errors are present and should be correlated with interface "
            "errors, packet loss, and physical-link health.",
        )

    if "packet loss detected" in finding_text:
        return (
            "Packet-loss condition requiring further investigation",
            65,
            "Packet loss is observed, but the supplied evidence is insufficient "
            "to confirm a single root cause.",
        )

    return (
        "Insufficient evidence for a probable root cause",
        35,
        "The supplied telemetry does not contain enough abnormal indicators.",
    )


# -----------------------------
# Step 7: Recommendations
# -----------------------------
def generate_recommendations(root_cause):
    if "congestion" in root_cause.lower():
        return [
            "Review WAN/interface utilization and identify top traffic sources.",
            "Check QoS policies, queues, and queue-drop counters.",
            "Review traffic distribution and possible capacity constraints.",
            "Correlate the incident with traffic spikes and historical utilization.",
        ]

    if "interface" in root_cause.lower():
        return [
            "Check interface error counters and link health.",
            "Correlate CRC/input/output errors with packet loss.",
            "Review physical/link-layer alarms where available.",
        ]

    return [
        "Collect additional interface, routing, and performance telemetry.",
        "Compare the affected path with a known-good path.",
        "Review recent alarms and network changes.",
    ]


# -----------------------------
# Step 8: Report
# -----------------------------
def generate_report(
    incident,
    incident_type,
    severity,
    findings,
    retrieved,
    root_cause,
    confidence,
    explanation,
    recommendations,
):
    evidence = "\n".join(f"- {item}" for item in findings)
    knowledge = "\n".join(
        f"- {item['topic']} ({item['category']})" for item in retrieved
    )
    actions = "\n".join(f"{i}. {item}" for i, item in enumerate(recommendations, 1))

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

## Probable Root Cause
**{root_cause}**

## Confidence
**{confidence}%**

## AI Explanation
{explanation}

## Recommended Troubleshooting
{actions}

## Human Decision
**Engineer validation required before any operational action.**

> This is a read-only AI investigation. The result is a probable assessment,
> not confirmation of a production root cause.
"""


# -----------------------------
# Complete automated workflow
# -----------------------------
def run_investigation(incident):
    valid, validation_message = validate_incident(incident)

    if not valid:
        return (
            validation_message,
            "",
            "",
            "",
            "",
        )

    incident_type, severity = classify_incident(incident)
    findings = analyze_network_data(SAMPLE_NETWORK_DATA)
    retrieved = retrieve_rag_knowledge(incident)

    root_cause, confidence, explanation = generate_root_cause(findings)
    recommendations = generate_recommendations(root_cause)

    report = generate_report(
        incident,
        incident_type,
        severity,
        findings,
        retrieved,
        root_cause,
        confidence,
        explanation,
        recommendations,
    )

    workflow_status = (
        "1. Incident validated ✓\n"
        "2. Incident classified ✓\n"
        "3. Network data analyzed ✓\n"
        "4. RAG knowledge retrieved ✓\n"
        "5. Grok AI reasoning — NEXT STEP\n"
        "6. Root cause generated ✓\n"
        "7. Confidence assessed ✓\n"
        "8. Recommendations generated ✓\n"
        "9. Human validation required"
    )

    analysis = (
        f"Incident Type: {incident_type}\n"
        f"Severity: {severity}\n\n"
        "Observed Evidence:\n"
        + "\n".join(f"- {item}" for item in findings)
        + f"\n\nProbable Root Cause: {root_cause}"
        + f"\nConfidence: {confidence}%"
        + f"\n\nExplanation:\n{explanation}"
    )

    rag_output = "\n".join(
        f"• {item['topic']} — {item['category']}\n  {item['content']}"
        for item in retrieved
    )

    recommendation_output = "\n".join(
        f"{i}. {item}" for i, item in enumerate(recommendations, 1)
    )

    return workflow_status, analysis, rag_output, recommendation_output, report


# -----------------------------
# Gradio UI
# -----------------------------
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

    workflow_status = gr.Textbox(
        label="Workflow Status",
        lines=10,
    )

    analysis_output = gr.Textbox(
        label="AI Investigation",
        lines=12,
    )

    rag_output = gr.Textbox(
        label="Retrieved NOC Knowledge (RAG)",
        lines=10,
    )

    recommendation_output = gr.Textbox(
        label="Troubleshooting Recommendations",
        lines=8,
    )

    report_output = gr.Markdown(
        label="Investigation Report"
    )

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
