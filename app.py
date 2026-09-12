import gradio as gr


def analyze_incident(incident):
    if not incident.strip():
        return "Please enter an incident description."

    return f"""
Incident received successfully.

Incident Description:
{incident}

AI Investigation Status:
Ready for analysis.

Future workflow:
Incident → Classification → Network Analysis → RAG → Grok AI
→ Root Cause Analysis → Confidence → Recommendation
"""


with gr.Blocks(title="AI-NOC Copilot") as demo:
    gr.Markdown(
        """
        # 🤖 AI-NOC Copilot
        ### Intelligent Network Operations Assistant

        **AI-powered incident investigation for NOC & Network Engineers**
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown(
                """
                ### 📡 NOC Modules

                - 🖥️ NOC Dashboard
                - 🚨 Incident Management
                - 📂 Data Ingestion
                - 📊 Network Analysis
                - 🧠 RAG Knowledge Base
                - 🤖 AI Investigation
                - 🔍 Root Cause Analysis
                - 💡 Recommendations
                - 📄 Incident Reports
                """
            )

        with gr.Column(scale=3):
            gr.Markdown("## 🚨 Incident Investigation")

            incident_input = gr.Textbox(
                label="Incident Description",
                placeholder="Example: Users are experiencing high latency and packet loss on the WAN link.",
                lines=5,
            )

            analyze_button = gr.Button(
                "🔍 Start AI Investigation",
                variant="primary",
            )

            result = gr.Textbox(
                label="Investigation Result",
                lines=12,
            )

            analyze_button.click(
                fn=analyze_incident,
                inputs=incident_input,
                outputs=result,
            )

    gr.Markdown(
        """
        ---
        **AI-NOC Copilot | Telecom / Network + Generative AI + Workflow Automation**

        🔒 Read-only prototype — no SSH, physical router access,
        or automatic network configuration changes.
        """
    )


if __name__ == "__main__":
    demo.launch()
