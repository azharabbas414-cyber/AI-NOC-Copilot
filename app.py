import os
import streamlit as st
from openai import OpenAI


# ---------------------------------------------------------
# Small built-in NOC knowledge base
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
        "keywords": ["latency", "delay", "slow", "high ping"],
        "knowledge": (
            "High latency may be caused by congestion, a long network path, "
            "routing changes, overloaded devices, or packet loss. Check the path, "
            "utilization, and whether latency changed during the incident."
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
            "bad cables, optics, speed/duplex problems, or faulty hardware. "
            "Check interface counters and the physical connection."
        ),
    },
    {
        "topic": "OSPF",
        "keywords": ["ospf", "neighbor", "adjacency", "area"],
        "knowledge": (
            "OSPF problems can occur when neighbor adjacencies fail. Common causes "
            "include interface problems, area mismatch, authentication mismatch, "
            "network-type mismatch, or unstable links."
        ),
    },
    {
        "topic": "BGP",
        "keywords": ["bgp", "peer", "prefix", "bgp session"],
        "knowledge": (
            "BGP session problems may be caused by reachability issues, incorrect "
            "peer configuration, authentication problems, filtering, or remote peer "
            "failure. Check peer state, prefixes, and logs."
        ),
    },
    {
        "topic": "VLAN",
        "keywords": ["vlan", "tagging", "trunk", "access port"],
        "knowledge": (
            "VLAN connectivity problems can result from incorrect VLAN membership, "
            "trunk configuration, tagging, or native VLAN settings. Verify VLAN "
            "membership and whether the VLAN is allowed on the trunk."
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


def retrieve_knowledge(incident, top_k=3):
    """Simple keyword-based retrieval: our beginner RAG step."""
    text = incident.lower()
    matches = []

    for item in KNOWLEDGE_BASE:
        score = sum(1 for keyword in item["keywords"] if keyword in text)

        if score > 0:
            matches.append((score, item))

    matches.sort(key=lambda x: x[0], reverse=True)

    if not matches:
        return [{
            "topic": "General Network Troubleshooting",
            "knowledge": (
                "Start with the incident time, affected service/device, interface "
                "status, traffic utilization, errors, logs, and recent configuration "
                "or routing changes."
            ),
        }]

    return [item for _, item in matches[:top_k]]


def analyze_with_grok(incident, retrieved):
    api_key = os.getenv("XAI_API_KEY")

    if not api_key:
        return None, "XAI_API_KEY is not configured."

    knowledge_text = "\n\n".join(
        f"{item['topic']}: {item['knowledge']}" for item in retrieved
    )

    prompt = f"""
You are a beginner-friendly AI NOC Copilot.

Analyze this network incident using the retrieved NOC knowledge.

INCIDENT:
{incident}

RETRIEVED KNOWLEDGE:
{knowledge_text}

Return these sections:

### Incident Understanding
Explain what appears to be happening.

### Probable Root Cause
Give the most likely cause. Say clearly if evidence is insufficient.

### Evidence
List the important clues.

### Recommended Checks
Give 3 to 5 practical checks for an NOC engineer.

### Confidence
Give High, Medium, or Low confidence and explain why.

Rules:
- Do not invent device output or measurements.
- Do not claim certainty without evidence.
- Do not make automatic configuration changes.
- Keep the explanation simple.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

        response = client.responses.create(
            model="grok-4.6",
            input=prompt,
        )

        return response.output_text, None

    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 AI-NOC Copilot")
st.write(
    "A simple beginner project demonstrating **RAG + Grok** "
    "for network incident analysis."
)

st.info("Flow: Incident → Simple RAG → Grok → AI Analysis")

incident = st.text_area(
    "Network Incident",
    placeholder=(
        "Example: Users are experiencing high latency and packet loss "
        "on a congested link."
    ),
    height=150,
)

if st.button("🔍 Analyze Incident", type="primary"):
    if not incident.strip():
        st.warning("Please enter a network incident.")
    else:
        retrieved = retrieve_knowledge(incident)

        st.subheader("📚 Retrieved NOC Knowledge")

        for item in retrieved:
            with st.expander(item["topic"], expanded=True):
                st.write(item["knowledge"])

        with st.spinner("Grok is analyzing the incident..."):
            answer, error = analyze_with_grok(incident, retrieved)

        if error:
            st.error(error)

            if error == "XAI_API_KEY is not configured.":
                st.caption(
                    "Add XAI_API_KEY in your Streamlit Cloud app Secrets."
                )
        else:
            st.subheader("🤖 AI Investigation")
            st.markdown(answer)

st.divider()
st.caption(
    "Learning/demo project. AI recommendations should be verified "
    "against real network evidence before taking action."
)
