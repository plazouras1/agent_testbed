from dotenv import load_dotenv

load_dotenv()

import gradio as gr
from agent.agent import run_agent

# Gradio's ChatInterface passes history as a list of {"role", "content"} dicts,
# but our agent keeps state in a list of types.Content objects (the Gemini format).
# We maintain `contents` in a gr.State so it persists across turns in the same session.


def chat(user_message: str, history: list, contents: list):
    reply, contents = run_agent(user_message, contents)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    return "", history, contents


with gr.Blocks(title="Agent Lab") as demo:
    gr.Markdown("## Agent Lab\n`fetch_news` · `web_search` · `fetch_url` · `save_note`")

    chatbot = gr.Chatbot(height=520)
    contents_state = gr.State([])  # holds the Gemini conversation history

    with gr.Row():
        txt = gr.Textbox(placeholder="Ask anything…", scale=9, show_label=False)
        btn = gr.Button("Send", scale=1)

    # wire up both Enter-key and button click
    txt.submit(chat, [txt, chatbot, contents_state], [txt, chatbot, contents_state])
    btn.click(chat, [txt, chatbot, contents_state], [txt, chatbot, contents_state])


if __name__ == "__main__":
    demo.launch()
