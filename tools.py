"""LangChain tools for De Vinci academic assistant"""

from langchain.tools import tool
import scraper

# Global credentials to be set on the app
_devinci_email = None
_devinci_password = None

def set_credentials(email: str, password: str):
    """Set De Vinci credentials for scraper"""
    global _devinci_email, _devinci_password
    _devinci_email = email
    _devinci_password = password

@tool
def get_courses() -> str:
    """
    Get list of all courses available on De Vinci Moodle.
    
    Returns:
        Complete list of all courses with their names and categories
    """
    return scraper.get_courses_blocking(_devinci_email, _devinci_password)

@tool
def get_deadlines() -> str:
    """
    Get upcoming assignment deadlines and submission dates from De Vinci Moodle.
    
    Returns:
        List of upcoming deadlines with dates and course names
    """
    return scraper.get_deadlines_blocking(_devinci_email, _devinci_password)

# Export tools for agent
TOOLS = [get_courses, get_deadlines]