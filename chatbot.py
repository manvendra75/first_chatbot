import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import os

os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today regarding Umrah?"}
    ]

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

st.title("🗣️ Umrah Guide")
st.subheader("㈻ Your Mutamer for Umrah")

prompt = st.chat_input("Your question")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = llm(st.session_state.messages[-1]["content"])
                st.write(response)
                # FIX: Wrap response in a dict
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"An error occurred: {e}")


