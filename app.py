import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
from characters import CHARACTERS

load_dotenv()
token = os.environ.get("token")
# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="Телефонная будка 📞", page_icon="📞")

# Замени ключ на свой актуальный
OPENAI_API_KEY = token

if "client" not in st.session_state:
    st.session_state.client = OpenAI(api_key=OPENAI_API_KEY)
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- ИНТЕРФЕЙС УПРАВЛЕНИЯ ---
with st.sidebar:
    st.header("Настройки")
    char_id = st.selectbox(
        "Кому звоним?",
        options=list(CHARACTERS.keys()),
        format_func=lambda x: CHARACTERS[x]["name"]
    )
    selected_char = CHARACTERS[char_id]

    if st.button("Сбросить разговор 🗑️"):
        st.session_state.messages = []
        st.rerun()

st.title(f"Разговор: {selected_char['name']}")


# --- ЛОГИКА AI ---
def get_ai_response(user_text, character, is_voice=False):
    client = st.session_state.client

    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-10:]]
    messages = [{"role": "system", "content": character["prompt"]}] + history + [{"role": "user", "content": user_text}]

    # 1. Текст
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    ai_text = response.choices[0].message.content

    # 2. Голос (если нужно)
    ai_audio_data = None
    if is_voice:
        voice_res = client.audio.speech.create(
            model="tts-1",
            voice=character["voice"],
            input=ai_text
        )
        ai_audio_data = voice_res.content

    return ai_text, ai_audio_data


# --- ОТОБРАЖЕНИЕ ЧАТА ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "audio" in message:
            st.audio(message["audio"], format="audio/mp3")

# --- ОБРАБОТКА ВВОДА ---
user_input = st.chat_input("Напишите сообщение...")
audio_value = st.audio_input("Или скажите что-нибудь 🎙️")

prompt = None
is_audio_message = False

if user_input:
    prompt = user_input
elif audio_value:
    with st.spinner("Слушаю..."):
        # Исправляем ошибку UnicodeEncodeError (ASCII)
        audio_value.name = "audio.wav"

        transcription = st.session_state.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_value
        )
        prompt = transcription.text
        is_audio_message = True

if prompt:
    # Сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Генерация ответа
    with st.chat_message("assistant"):
        with st.spinner(f"{selected_char['name']} печатает..."):
            ai_text, ai_audio = get_ai_response(prompt, selected_char, is_voice=is_audio_message)

            st.markdown(ai_text)
            if ai_audio:
                st.audio(ai_audio, format="audio/mp3")

    # Сохранение
    msg_data = {"role": "assistant", "content": ai_text}
    if ai_audio:
        msg_data["audio"] = ai_audio
    st.session_state.messages.append(msg_data)