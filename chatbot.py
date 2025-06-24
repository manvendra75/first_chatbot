import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
import os

# Set API key if needed
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize session state variables
if 'buffer_memory' not in st.session_state:
    st.session_state.buffer_memory = ConversationBufferWindowMemory(k=3, return_messages=True)

# Add the system message as the first message in the history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are an Umrah guide with deep experience in Umrah rituals and religious processes. "
                "Assist users with your expertise and knowledge to help them perform Umrah correctly and spiritually."
            )
        },
        {"role": "assistant", "content": "How can I help you today regarding Umrah?"}
    ]

# Initialize Google Generative AI and ConversationChain
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
conversation = ConversationChain(memory=st.session_state.buffer_memory, llm=llm)

# Create user interface
st.title("🗣️ Umrah Guide")
st.subheader("㈻ Your Mutamer for Umrah")

prompt = st.chat_input("Your question")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display prior chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Extract the system message (if any)
system_message = ""
for msg in st.session_state.messages:
    if msg["role"] == "system":
        system_message = msg["content"]
        break

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            user_input = st.session_state.messages[-1]["content"]
            # Prepend system message to user input for context
            full_input = f"{system_message}\n\n{user_input}" if system_message else user_input
            response = conversation.predict(input=full_input)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
