import streamlit as st
from chatbot import chat

st.set_page_config(page_title="Day 1 AI Chatbot", page_icon="🤖")
st.title("Day 1 AI Chatbot")

# Initialize chat history (persists across reruns)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render all previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle new input
if prompt := st.chat_input("Type a message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = chat(prompt)
        st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
