import os
import gradio as gr
from openai import OpenAI


# ---------------------------------------------------------
# 1. Small built-in NOC knowledge base
# ---------------------------------------------------------
KNOWLEDGE_BASE = [
    {
        "topic": "Packet Loss",
        "keywords": ["packet loss", "loss", "dropped packets", "drops"],
        "knowledge": (
            "Packet loss can be caused by link congestion, interface errors, "
            "physical-layer problems, faulty equipment, or an overloaded device. "
            "Check interface utilization, error counters, drops, and the affected link."
        ),
    },
    {
        "topic": "High Latency",
        "keywords": ["latency", "delay", "slow", "high ping", "response time"],
        "knowledge": (
            "High latency may be caused by congestion, a long network path, "
            "routing changes, overloaded devices, or packet loss. Compare latency "
            "before and after the incident and check the path and utilization."
        ),
    },
    {
        "topic": "Congestion",
        "keywords": ["congestion", "bandwidth", "utilization", "traffic", "overload"],
        "knowledge": (
            "Network congestion occurs when traffic approaches or exceeds available "
            "bandwidth. Check interface utilization, traffic trends, queue drops, "
            "and whether a traffic spike occurred."
        ),
    },
    {
        "topic": "Interface Errors",
        "keywords": ["interface error", "crc", "errors", "input error", "output error"],
        "knowledge": (
            "Interface errors such as CRC errors can indicate physical-layer issues, "
            "bad cables, optics, duplex/speed problems, or faulty hardware. "
            "Check interface counters and the physical connection."
        ),
    },
    {
        "topic": "OSPF",
        "keywords": ["ospf", "neighbor", "adjacency", "area"],
        "knowledge": (
            "OSPF problems can occur when neighbor adjacencies fail. Common causes "
            "include interface problems, area mismatch, authentication mismatch, "
            "network-type mismatch, or unstable links. Check OSPF neighbors and logs."
        ),
    },
    {
        "topic": "BGP",
        "keywords": ["bgp", "peer", "prefix", "route", "bgp session"],
        "knowledge": (
            "BGP session problems may be caused by reachability issues, incorrect "
            "peer configuration, authentication problems, filtering, or a remote peer "
            "failure. Check peer state, received/advertised prefixes, and logs."
        ),
    },
    {
        "topic": "VLAN",
        "keywords": ["vlan", "tagging", "trunk", "access port"],
        "knowledge": (
            "VLAN connectivity problems can result from incorrect VLAN membership, "
            "trunk configuration, tagging, or native VLAN settings. Verify the VLAN "
            "exists and is allowed on the relevant trunk or assigned to the correct port."
        ),
    },
    {
        "topic": "MTU",
        "keywords": ["mtu", "fragmentation", "fragment", "packet size"],
        "knowledge": (
            "MTU problems can cause packet drops or application connectivity issues. "
            "Check MTU values along the path and test packet sizes. Inconsistent MTU "
            "settings can cause fragmentation or dropped oversized packets."
        ),
    },
]


# ---------------------------------------------------------
# 2. Simple RAG retrieval
# ---------------------------------------------------------
def retrieve_knowledge(incident, top_k=3):
    text = incident.lower()
    results = []

    for item in KNOWLEDGE_BASE:
        score = 0

        for keyword in item["keywords"]:
            if keyword in text:
                score += 1

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    if not results:
        return [
            {
                "topic": "General Network Troubleshooting",
                "knowledge": (
                    "Start with the incident time, affected service/device, "
                    "interface status, traffic utilization, errors, logs, and "
                    "recent configuration or routing changes."
                ),
            }
        ]

    return [item for _, item in results[:top_k]]


# ---------------------------------------------------------
# 3. Ask Grok
# ---------------------------------------------------------
def analyze_incident(incident):
    incident = (incident or "").strip()

    if not incident:
        return "Please enter a network incident first."

    retrieved = retrieve_knowledge(incident)

    knowledge_text = "\n\n".join(
        f"**{item['topic']}**\n{item['knowledge']}"
        for item in retrieved
    )

    api_key = os.getenv("XAI_API_KEY")

    if not api_key:
        return (
            "### API key not found\n\n"
            "The RAG step worked, but Grok cannot be called because "
            "`XAI_API_KEY` is not configured.\n\n"
            "### Retrieved NOC knowledge\n\n"
            + knowledge_text
        )

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        prompt = f"""
You are a beginner-friendly AI NOC Copilot.

Analyze the following network incident using the retrieved NOC knowledge.

INCIDENT:
{incident}

RETRIEVED KNOWLEDGE:
{knowledge_text}

Give a concise answer with exactly these sections:

### Incident Understanding
Explain what appears to be happening.

### Probable Root Cause
Give the most likely cause. Clearly say when the evidence is insufficient.

### Evidence
List the important clues from the incident and retrieved knowledge.

### Recommended Checks
Give 3 to 5 practical checks an NOC engineer should perform.

### Confidence
Give High, Medium, or Low confidence and briefly explain why.

Important:
- Do not claim certainty without evidence.
- Do not invent device output or measurements.
- Do not perform or recommend automatic configuration changes.
- Keep the explanation simple and useful for a junior NOC engineer.
"""

        response = client.responses.create(
            model="grok-4.6",
            input=prompt,
        )

        return (
            "### Retrieved NOC Knowledge\n\n"
            + knowledge_text
            + "\n\n---\n\n"
            + response.output_text
        )

    except Exception as e:
        return (
            "### Error calling Grok\n\n"
            f"`{str(e)}`\n\n"
            "The RAG retrieval step completed successfully. "
            "Please check your XAI_API_KEY and API access."
        )


# ---------------------------------------------------------
# 4. Simple Gradio UI
# ---------------------------------------------------------
with gr.Blocks(title="AI-NOC Copilot") as demo:
    gr.Markdown(
        """
# 🤖 AI-NOC Copilot

A beginner-friendly AI assistant for understanding network incidents.

**Simple flow:** Incident → RAG → Grok → Analysis
"""
    )

    incident_input = gr.Textbox(
        label="Network Incident",
        placeholder=(
            "Example: Users are experiencing high latency and packet loss "
            "on a congested link."
        ),
        lines=6,
    )

    analyze_button = gr.Button("Analyze Incident", variant="primary")

    result_output = gr.Markdown(
        label="AI Investigation",
    )

    analyze_button.click(
        fn=analyze_incident,
        inputs=incident_input,
        outputs=result_output,
    )

    gr.Markdown(
        """
### What this project demonstrates
- **RAG:** retrieves relevant NOC knowledge before asking the LLM.
- **LLM:** Grok analyzes the incident using the retrieved context.
- **Human in the loop:** the tool provides analysis and recommendations only.
- **No SSH / routers:** this beginner version uses no physical network access.
"""
    )


if __name__ == "__main__":
    demo.launch()
