"""
ESILV Academic Assistant - Streamlit Frontend

Web interface for the ReAct agent that enables students to:
- Search for courses on De Vinci Moodle
- Check upcoming assignment deadlines
- Switch between available LLM models
- Enter De Vinci credentials

Requires Ollama to be running locally with at least one model installed.
"""

import streamlit as st
import logging
import requests
from datetime import datetime
from typing import List
from agent import ReActAgent, create_llm
import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"

# Streamlit page configuration
st.set_page_config(
    page_title="ESILV Academic Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for black on white chat message colors
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
        # Keep full model names with version tags for proper initialization
        models = [model["name"] for model in data.get("models", [])]
        return models
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return []


def display_ollama_status():
    """
    Display Ollama server status and model selection in the sidebar.
    
    Shows:
    - Server connection status
    - Available models with a dropdown selector
    - Model details (size, tags)
    - Instructions if server is not running
    """
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
                index=models.index(st.session_state.get("selected_model", "mistral:latest")) 
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
    """
    Display assistant tools information and credential management in sidebar.
    
    Allows students to:
    - Enter and save De Vinci credentials securely
    - Learn about available tools
    - Understand how the agent works
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔐 De Vinci Credentials")
    
    # Credentials form
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
    """
    Initialize all Streamlit session state variables.
    
    Creates default values for:
    - Chat message history
    - Selected model
    - ReAct agent instance
    - UI preferences (show thinking)
    - De Vinci credentials
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "mistral:latest"
    
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
    """
    Display the chat conversation history.
    
    Shows all previous messages with user avatars and thinking process
    if the "show thinking" toggle is enabled.
    """
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display conversation history
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
                
                # Show thinking process if enabled
                if message["role"] == "assistant" and "thinking" in message:
                    if st.session_state.thinking_visible:
                        with st.expander("🤔 Agent Thinking Process"):
                            st.info(message["thinking"][:500] + "...")

def handle_user_input():
    """
    Handle user input from the chat box.
    
    1. Collects user input
    2. Calls the agent
    3. Stores the response in chat history
    4. Triggers page rerun to display cleanly
    """
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
                error_msg = f"❌ Error: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
        
        # Rerun to display all messages cleanly
        st.rerun()
        

def display_welcome():
    """
    Display welcome message and instructions for first-time users.
    
    Shows:
    - Overview of assistant capabilities
    - Usage instructions
    - Example questions
    """
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
    """
    Main application entry point.
    
    Initializes the Streamlit app with sidebar controls,
    checks dependencies, and manages the UI flow.
    """
    # Initialize session state
    initialize_session_state()
    
    # Sidebar configuration
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Display Ollama server status and model selection
        server_running = display_ollama_status()
        
        if not server_running:
            st.warning("⚠️ Agent requires Ollama to be running!")
            st.stop()
        
        # Display assistant information and credential management
        display_assistant_info()
        
        # Chat history management
        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # UI preferences
        st.session_state.thinking_visible = st.checkbox(
            "Show thinking process",
            value=st.session_state.thinking_visible
        )
    
    # Main content area
    if not st.session_state.messages:
        display_welcome()
    else:
        display_chat()
    
    # Chat input handling
    handle_user_input()

if __name__ == "__main__":
    main()
