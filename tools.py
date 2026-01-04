"""
LangChain tools for De Vinci academic assistant.

This module provides tool wrappers that allow the ReAct agent to:
- Fetch course listings from Moodle
- Retrieve upcoming assignment deadlines

Each tool is decorated with @tool to register it with LangChain.
"""

from langchain.tools import tool
import scraper

# Global credentials storage
# Set by the Streamlit app when student enters their De Vinci login
_devinci_email = None
_devinci_password = None

def set_credentials(email: str, password: str):
    """
    Store De Vinci credentials for use by scraper tools.
    
    Called by the Streamlit app when student enters credentials.
    Credentials are used for browser authentication with Moodle.
    
    Args:
        email: De Vinci student email
        password: De Vinci password
    """
    global _devinci_email, _devinci_password
    _devinci_email = email
    _devinci_password = password

@tool
def get_courses() -> str:
    """
    Get list of all courses available on De Vinci Moodle.
    
    Retrieves the student's complete course list from the Moodle dashboard
    including course names and categories. No parameters required.
    
    Returns:
        String containing formatted list of all courses with categories
    """
    return scraper.get_courses_blocking(_devinci_email, _devinci_password)

@tool
def get_deadlines() -> str:
    """
    Get upcoming assignment deadlines and submission dates from De Vinci Moodle.
    
    Retrieves from the timeline section showing all upcoming work that needs
    to be submitted. No parameters required.
    
    Returns:
        String containing formatted list of upcoming deadlines with dates and times
    """
    return scraper.get_deadlines_blocking(_devinci_email, _devinci_password)

# Register all tools for the agent
TOOLS = [get_courses, get_deadlines]