import time
import requests
import gradio as gr
from huggingface_hub import InferenceClient
from apscheduler.schedulers.background import BackgroundScheduler


api_active = False
TRANSLATION_ENDPOINT = "https://iyh5fx52avidpvyn.us-east-1.aws.endpoints.huggingface.cloud"


def translate(text: str = "") -> str:
    global api_active
    if not api_active:
        response = requests.get(TRANSLATION_ENDPOINT)
        if response.status_code != 200:
            gr.Info("Translation API is loading...\nThis may take several minutes.", duration=30)
            return "Translation API is not ready for use.\nPlease try again in a few minutes."
        else:
            api_active = True
            gr.Info("Translation API is now ready for use.\nPlease, try your query agan!", duration=10)
    if not text:
        return ""
    else:
        response = requests.post(TRANSLATION_ENDPOINT, json={
            "inputs": text,
            "parameters": {"src_lang": "<|CajFr|>" + "English", "tgt_lang": "French"}
        })

        return response.json()[0]['translation_text']


client = InferenceClient("HuggingFaceH4/zephyr-7b-beta")
def respond(message, history: list[tuple[str, str]], system_message, max_tokens = 1024, temperature = 0.7, top_p = 0.9):
    messages = [{"role": "system", "content": system_message}]

    # Build the message history
    for val in history:
        if val["role"] == "user" and val["content"]:
            messages.append({"role": "user", "content": val["content"]})
            
        elif val["role"] == "assistant" and val["content"]:
            messages.append({"role": "assistant", "content": val["content"]})

    messages.append({"role": "user", "content": message})

    # Query the model and stream the response
    response = ""
    for message in client.chat_completion(messages, max_tokens=max_tokens, stream=True, temperature=temperature, top_p=top_p):
        token = message.choices[0].delta.content

        response += token
        yield response
        

# Load the learning path HTML
with open("index.html", "r", encoding="utf-8") as file:
    learning_path_html = file.read()


system_prompt = """
You are a linguistics expert trained to facilitate 'proximal zone of development' learning for language learners of Louisiana French.
You will guide interactions and drive conversations with new students to achieve the following goals:

1) Assess the extent of a student's prior knowledge based on extensive knowledge about appropriate ordering of language learning concepts.
2) Develop concise, yet engaging interactions that require the student to learn concepts and information relevant to extending their understanding of Louisiana French.
3) Provide feedback to the student so that they can improve their skills and understanding.
4) Dynamically adjust the difficulty, vocabulary, and content of the conversation to ensure an optimal rate of learning and engagement.

In addition to these goals, always remember to be as concise as possible, while still polite and engaging in order to keep the learning setting light and fun, but above all else it is essential to manage cognitive load by keping interactions short and targeted.
"""


chat = gr.ChatInterface(
    respond,
    type="messages",
    additional_inputs=[gr.State(value=system_prompt)]
)


translator = gr.Interface(
    fn=translate,
    inputs=[gr.Textbox(label="Input Text", placeholder="Input Text To Be Translated")],
    outputs=gr.Textbox(label="Translation"),
    title="NLLB-200: English to Louisiana French Translator",
)


# Create the Interface
with gr.Blocks() as demo:
    gr.Markdown("## Louisiana French Chatbot")
    with gr.Row():
        with gr.Column(scale=3):
            gr.TabbedInterface([translator, chat], ["Translator", "Conversational Tutor"])
        with gr.Column(scale=1):
            currictulum = gr.HTML(learning_path_html)


if __name__ == "__main__":
    if requests.get(TRANSLATION_ENDPOINT).status_code != 200:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=translate, trigger="interval", seconds=30)
        scheduler.start()
    
    demo.launch()