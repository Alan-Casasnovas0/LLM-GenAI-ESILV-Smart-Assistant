"""
ESILV Academic Assistant - Streamlit Frontend
Integrates with ReAct agent for intelligent course search and deadline tracking
"""

import streamlit as st
import logging
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List
from agent import ReActAgent, llm, SYSTEM_PROMPT, create_llm
import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"

# Page config
st.set_page_config(
    page_title="ESILV Academic Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def check_ollama_server(base_url: str = OLLAMA_BASE_URL) -> tuple:
    """Check if Ollama server is running"""
    try:
        response = requests.get(base_url, timeout=2)
        return response.status_code == 200, None
    except Exception as e:
        return False, str(e)

@st.cache_data
def get_available_models(base_url: str = OLLAMA_BASE_URL) -> List[str]:
    """Fetch available models from Ollama with full names"""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        # Keep full model names with version tags (e.g., "mistral:latest")
        models = [model["name"] for model in data.get("models", [])]
        return models
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return []

def get_model_info(base_url: str = OLLAMA_BASE_URL) -> Dict:
    """Get detailed info about available models"""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching model info: {e}")
        return {"models": []}

def display_ollama_status():
    """Display Ollama server status in sidebar"""
    st.sidebar.markdown("## 🔌 Server Status")
    
    is_running, error = check_ollama_server()
    
    if is_running:
        st.sidebar.success("Ollama Server Running", icon="✅")
        
        # Get available models
        models = get_available_models()
        
        if models:
            st.sidebar.markdown(f"**Available Models:** {len(models)}")
            selected_model = st.sidebar.selectbox(
                "Choose a model:",
                options=models,
                index=models.index(st.session_state.get("selected_model", "mistral")) 
                    if st.session_state.get("selected_model") in models else 0,
                key="model_selector"
            )
            
            if selected_model != st.session_state.get("selected_model"):
                st.session_state.selected_model = selected_model
                # Recreate agent with new model
                new_llm = create_llm(selected_model)
                st.session_state.agent = ReActAgent(new_llm, tools.TOOLS)
                st.success(f"✅ Switched to {selected_model}", icon="✨")
        else:
            st.sidebar.warning("⚠️ No models found. Run: `ollama pull llama3.2:1b`")
    else:
        st.sidebar.error("Ollama Server Not Running", icon="❌")
        st.sidebar.markdown("""
        **To start Ollama:**
        
        ```bash
        ollama serve
        ```
        
        **To pull a model:**
        
        ```bash
        ollama pull llama3.2:1b
        ollama pull mistral
        ```
        """)
        return False
    
    return is_running

def display_assistant_info():
    """Display assistant information and credentials in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔐 De Vinci Credentials")
    
    # Credentials section
    with st.sidebar.form("devinci_credentials"):
        email = st.text_input("Email", placeholder="your.email@edu.devinci.fr", type="default")
        password = st.text_input("Password", placeholder="Your password", type="password")
        
        if st.form_submit_button("✅ Save Credentials"):
            if email and password:
                st.session_state.devinci_email = email
                st.session_state.devinci_password = password
                tools.set_credentials(email, password)
                st.success("Credentials saved!")
            else:
                st.error("Please enter both email and password")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📋 Assistant Info")
    
    with st.sidebar.expander("Available Tools"):
        st.markdown("""
        **get_courses**: Retrieve all courses on Moodle
        - Used when student asks about their courses
        
        **get_deadlines**: Retrieve upcoming deadlines
        - Used when student asks about assignment deadlines
        """)
    
    with st.sidebar.expander("How It Works"):
        st.markdown("""
        1. **Thinking**: Agent analyzes your question
        2. **Tool Selection**: Chooses relevant tools
        3. **Data Collection**: Calls tools to get real data
        4. **Response**: Generates answer based on data
        """)

def initialize_session_state():
    """Initialize Streamlit session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "mistral"
    
    if "agent" not in st.session_state:
        llm_instance = create_llm(st.session_state.selected_model)
        st.session_state.agent = ReActAgent(llm_instance, tools.TOOLS)
    
    if "thinking_visible" not in st.session_state:
        st.session_state.thinking_visible = True
    
    if "devinci_email" not in st.session_state:
        st.session_state.devinci_email = None
    
    if "devinci_password" not in st.session_state:
        st.session_state.devinci_password = None

def display_chat():
    """Display chat interface"""
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display conversation history
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
                
                # Show thinking process if available
                if message["role"] == "assistant" and "thinking" in message:
                    if st.session_state.thinking_visible:
                        with st.expander("🤔 Agent Thinking Process"):
                            st.info(message["thinking"][:500] + "...")

def handle_user_input():
    """Handle user input and agent response"""
    # Input section
    st.markdown("---")
    user_input = st.chat_input("Ask about courses or deadlines...")
    
    if user_input:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        
        # Get agent response
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.agent.invoke(user_input)
                
                # Add to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                error_msg = f"❌ Erreur: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
        
        # Rerun to display all messages cleanly
        st.rerun()
        

def display_welcome():
    """Display welcome message"""
    st.markdown("""
    # 📚 ESILV Academic Assistant
    
    Welcome to your intelligent academic companion! I can help you with:
    - 🔍 **Course Search**: Find courses on De Vinci Moodle
    - ⏰ **Deadline Tracking**: Get your upcoming assignment deadlines
    - 💡 **Smart Assistance**: AI-powered answers about your courses
    
    ---
    
    ### How to Use
    1. Type your question in the chat box below
    2. The agent will think and analyze your request
    3. It will use available tools to fetch real data
    4. You'll get a comprehensive answer
    
    **Example questions:**
    - "What are my upcoming deadlines?"
    - "Show me all available courses"
    - "Search for courses about machine learning"
    """)

def main():
    """Main application"""
    # Initialize session state
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Display Ollama status
        server_running = display_ollama_status()
        
        if not server_running:
            st.warning("⚠️ Agent requires Ollama to be running!")
            st.stop()
        
        # Display assistant info
        display_assistant_info()
        
        # Clear chat button
        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Toggle thinking visibility
        st.session_state.thinking_visible = st.checkbox(
            "Show thinking process",
            value=st.session_state.thinking_visible
        )
    
    # Main content
    if not st.session_state.messages:
        display_welcome()
    else:
        display_chat()
    
    # Handle user input
    handle_user_input()

if __name__ == "__main__":
    main()
