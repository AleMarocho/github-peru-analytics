import streamlit as st
import os
import sys

# Ensure we can import src module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from src.agents.insights_agent import InsightsAgent
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Ask the AI Agent", page_icon="🤖", layout="wide")

def main():
    st.title("🤖 Ask the QA Insights Agent")
    st.markdown("Have questions about developers in Peru? Ask our specialized AI.")
    st.markdown("*(Powered by GPT-4 and Function Calling based on your extracted datasets)*")
    
    st.divider()

    # Initialize chat history string in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize Singleton Agent
    if "agent" not in st.session_state:
        st.session_state.agent = InsightsAgent()

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Ask me about the top languages, top developers, or industries in Peru..."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Agent thinking...
        with st.chat_message("assistant"):
            with st.spinner("Analyzing GitHub data using OpenAI Function Calling..."):
                try:
                    # Let the true Agent loop do its magic!
                    response = st.session_state.agent.run(prompt)
                except Exception as e:
                    response = f"I'm sorry, I ran into an error accessing my tools: {e}"
                    
            st.markdown(response)
            
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Sidebar tips
    st.sidebar.markdown("### Suggested Prompts")
    st.sidebar.markdown("- *Who are the top 3 developers by Impact Score?*")
    st.sidebar.markdown("- *What is the most popular programming language in Peru?*")
    st.sidebar.markdown("- *How many total developers are in the ecosystem?*")
    st.sidebar.markdown("- *Which industry dominates the repositories here?*")

if __name__ == "__main__":
    main()
