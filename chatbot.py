import streamlit as st
# from streamlit_chat import message  # Not used in this code

from langchain_google_genai import ChatGoogleGenerativeAI  # Uncommented
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory

import os

# Set API key if needed
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize session state variables
if 'buffer_memory' not in st.session_state:
    st.session_state.buffer_memory = ConversationBufferWindowMemory(k=3, return_messages=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]

# Initialize Google Generative AI and ConversationChain
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
conversation = ConversationChain(memory=st.session_state.buffer_memory, llm=llm)

# Create user interface
st.title("🗣️ Conversational Chatbot")
st.subheader("㈻ Simple Chat Interface for LLMs by Build Fast with AI")

prompt = st.chat_input("Your question")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display prior chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = conversation.predict(input=st.session_state.messages[-1]["content"])
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

