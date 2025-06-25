import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.schema import HumanMessage, AIMessage
import os

# Set the API key from secrets
os.environ["GOOGLE_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.memory = ConversationBufferMemory(return_messages=True)
    # Add initial message
    initial_message = "Assalamu Alaikum! I'm your Umrah guide. I can help you with:\n- Umrah rituals and steps\n- Duas and prayers\n- Travel tips for Makkah and Madinah\n- Historical information about holy sites\n\nHow can I assist you today?"
    st.session_state.messages.append({"role": "assistant", "content": initial_message})
    st.session_state.memory.chat_memory.add_ai_message(initial_message)

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=st.secrets["GEMINI_API_KEY"],
    temperature=0.7
)

# Create conversation chain with memory
if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationChain(
        llm=llm,
        memory=st.session_state.memory,
        verbose=False  # Set to True for debugging
    )

# UI Elements
st.title("🕋 Umrah Guide")
st.subheader("Your AI Mutawwif for Umrah")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Ask me anything about Umrah...")

if prompt:
    # Add user message to session state and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Add context to make responses more Umrah-focused
                contextualized_prompt = f"""As an Umrah guide assistant, please answer the following question about Umrah, Islamic practices, or travel to the holy sites. 
                If the question is not related to these topics, politely redirect the conversation back to Umrah-related matters.
                
                User question: {prompt}"""
                
                # Get response from conversation chain (includes memory)
                response = st.session_state.conversation.predict(input=contextualized_prompt)
                
                # Display the response
                st.write(response)
                
                # Add to messages for display
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                
                # More specific error handling
                if "API key" in str(e):
                    st.error("❌ Please check your GEMINI_API_KEY in Streamlit secrets")
                elif "quota" in str(e).lower():
                    st.error("❌ API quota exceeded. Please check your Google AI Studio account.")
                else:
                    st.error("❌ Please try again or rephrase your question.")

# Sidebar with additional information
with st.sidebar:
    st.header("📚 About This Guide")
    st.markdown("""
    This AI assistant can help you with:
    - **Umrah Rituals**: Step-by-step guidance
    - **Duas**: Important prayers and their meanings
    - **Travel Tips**: Practical advice for pilgrims
    - **Holy Sites**: Information about Makkah & Madinah
    
    ### 🔄 Memory Feature
    This chatbot remembers your conversation context for better responses!
    """)
    
    # Option to clear chat history
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.memory.clear()
        st.session_state.conversation = ConversationChain(
            llm=llm,
            memory=ConversationBufferMemory(return_messages=True),
            verbose=False
        )
        st.rerun()
    
    # Display memory buffer size
    st.caption(f"Messages in memory: {len(st.session_state.messages)}")


