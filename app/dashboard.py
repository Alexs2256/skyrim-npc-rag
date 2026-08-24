import streamlit as st
import os
import sys
import uuid
from pathlib import Path
from PIL import Image
from prompts import LydiaPrompt 
from agent import app as chatbot_app

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_FILE_NAME = "Gemini_Generated_Image_8ld2uj8ld2uj8ld2.jfif"
image_path = BASE_DIR / "app" / "assets" / "images" / IMAGE_FILE_NAME

lydia_img = None
try:
    lydia_img = Image.open(image_path)
except FileNotFoundError:
    st.sidebar.error(f"⚠️ Avatar Not Found at: {image_path}")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

st.set_page_config(page_title="Skyrim Companion Dashboard", layout="wide")

# ... (keep your existing CSS block exactly as-is) ...

st.markdown('<h1 class="skyrim-title">🛡️ Lydia: Skyrim Companion</h1>', unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("<h2 style='color:#e5c158; font-family:Georgia;'>⚙️ SYSTEM LOG</h2>", unsafe_allow_html=True)
    session_id = st.text_input("Thane Session ID", value=st.session_state.session_id)
    st.markdown("<div class='skyrim-divider'></div>", unsafe_allow_html=True)
    if st.button("✨ Reset Quest (Clear History)"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- NEW: Mode selector ---
mode = st.radio(
    "What would you like to do?",
    ["💬 Talk to Lydia", "⚔️ Start a New Quest"],
    horizontal=True,
)

# Render conversation history (unchanged)
for message in st.session_state.messages:
    avatar_icon = lydia_img if message["role"] == "assistant" else "user"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(
            f"<span style='color:#d1c2a5; white-space: pre-wrap;'>{message['content']}</span>",
            unsafe_allow_html=True,
        )

def run_graph(prompt: str, history: list, chunk_text: str):
    with st.chat_message("assistant", avatar=lydia_img):
        message_placeholder = st.empty()
        with st.spinner("Lydia is preparing to answer..."):
            try:
                graph_output = chatbot_app.invoke({
                    "prompt": prompt,
                    "session_id": session_id,
                    "history": history,
                    "chunk_text": chunk_text
                })
                ai_response = graph_output.get(
                    'response', "I am sworn to carry your burdens, but I couldn't understand that."
                )
                with st.sidebar:
                    st.info(f"📍 Active Quest Type: **{graph_output.get('route', 'unknown').upper()}**")
            except Exception as e:
                import traceback
                traceback.print_exc()
                st.exception(e)
                ai_response = f"⚠️ System Graph Error: {str(e)}"
        message_placeholder.markdown(
            f"<span style='color:#d1c2a5; white-space: pre-wrap;'>{ai_response}</span>",
            unsafe_allow_html=True,
        )
    st.session_state.messages.append({"role": "assistant", "content": ai_response})

def build_history():
    history = []
    for msg in st.session_state.messages[:-1]: 
        if msg["role"] == "user":
            role_type = "user"
        else:
           role_type = "model"
        history.append({"role": role_type, "parts": [{"text": msg["content"]}]})
    return history

# --- Chat mode (existing chat_input flow, unchanged) ---
if mode == "💬 Talk to Lydia":
    if prompt := st.chat_input("Speak, Thane. What do you need?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        run_graph(prompt, build_history(), "")

# --- Quest mode: dropdown, no free text, no routing ambiguity ---
else:
    quest_list = LydiaPrompt("").quests  # adjust if your property needs a real arg
    selected_quest = st.selectbox("Choose a quest to begin:", quest_list)

    if st.button("Start Quest"):
        st.session_state.messages.append({"role": "user", "content": selected_quest})
        with st.chat_message("user"):
            st.markdown(selected_quest)
        st.write('New Quest Started: ', selected_quest)
        run_graph(selected_quest, build_history(), "")