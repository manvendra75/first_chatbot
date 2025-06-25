import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Set the API key from secrets
os.environ["GOOGLE_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today regarding Umrah?"}
    ]

# Initialize the LLM with proper API key
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=st.secrets["GEMINI_API_KEY"]
)

# UI Elements
st.title("🗣️ Umrah Guide")
st.subheader("Your Mutawwif for Umrah")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
prompt = st.chat_input("Your question")

if prompt:
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Call the LLM with proper method
                response = llm.invoke(prompt)
                # Extract content from response
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Display the response
                st.write(response_text)
                
                # Add to session state
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                # Optional: Add more specific error handling
                if "API key" in str(e):
                    st.error("Please check your GEMINI_API_KEY in Streamlit secrets")
                elif "quota" in str(e).lower():
                    st.error("API quota exceeded. Please check your Google AI Studio account.")


