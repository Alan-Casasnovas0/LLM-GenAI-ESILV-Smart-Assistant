"""ESILV Academic Assistant - ReAct Agent using LangChain with Ollama

This module implements a ReAct (Reasoning + Acting) agent that:
1. Thinks about the user's question
2. Decides which tools to use
3. Executes the tools
4. Generates a response based on tool results

The agent uses local LLM models via Ollama for all reasoning.
"""

import logging
from langchain_ollama import OllamaLLM
import tools

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM - Using mistral by default
llm = OllamaLLM(model="mistral", temperature=0)

def create_llm(model_name: str = "mistral") -> OllamaLLM:
    """Create an OllamaLLM instance with specified model"""
    return OllamaLLM(model=model_name, temperature=0)

# System prompt for the agent - defines behavior and available tools
SYSTEM_PROMPT = """You are an academic assistant for ESILV students.
Respond naturally to questions and use available tools to retrieve up-to-date information from De Vinci Moodle platform.
IMPORTANT: Only use a tool when necessary to answer the student's question.

AVAILABLE TOOLS:
1. get_courses() - Retrieves the COMPLETE LIST of all student's courses
   USE WHEN: Student asks for their courses, course list, "my courses", "all courses"
   
2. get_deadlines() - Retrieves upcoming assignment deadlines
   USE WHEN: Student asks for deadlines, work to submit, due dates

STRICT RULES:
1. BE HONEST: If you call a tool, state it clearly
2. NEVER INVENT data - no making up course names or fake lists
3. USE TOOLS to get real data from Moodle
4. IF TOOL FAILS (error, missing credentials): STATE IT CLEARLY
5. DO NOT make assumptions about results

BE PRECISE AND HONEST. Never speculate."""

class ReActAgent:
    """ReAct agent that reasons and uses tools to answer questions"""
    
    def __init__(self, llm, tools_list):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools_list}
        self.conversation_history = []
        
    def invoke(self, user_input: str) -> str:
        """Process user input through ReAct loop"""
        
        # Step 1: Agent thinks about the question and decides what tools to use
        thinking_prompt = f"""{SYSTEM_PROMPT}
        
        Student: {user_input}

        Now, explain what you're going to do and which tool(s) you'll use."""
        
        thinking_response = self.llm.invoke(thinking_prompt)
        logger.info(f"Agent thinking: {thinking_response[:200]}")
        
        # Step 2: Extract which tool(s) the agent wants to use from the thinking
        tool_calls = self._extract_tool_calls(thinking_response)
        
        all_results = {}
        
        # Step 3: Execute the tools
        for tool_name, tool_args in tool_calls:
            if tool_name in self.tools:
                logger.info(f"🔧 Executing tool: {tool_name}")
                try:
                    tool_obj = self.tools[tool_name]
                    result = tool_obj.func()
                    
                    all_results[tool_name] = result
                    logger.info(f"✅ Tool result: {result[:200] if result else 'No data'}")
                except Exception as e:
                    logger.error(f"❌ Tool error: {e}")
                    all_results[tool_name] = f"Error executing tool: {e}"
        
        # Step 4: Generate final answer based on tool results
        final_prompt = f"""{SYSTEM_PROMPT}

Student: {user_input}

Your reasoning:
{thinking_response}

Tool results:
"""
        
        for tool_name, result in all_results.items():
            final_prompt += f"\n{tool_name}: {result}"
        
        final_prompt += "\n\nNow provide a complete and helpful response to the student."
        
        final_response = self.llm.invoke(final_prompt)
        
        return final_response
    
    def _extract_tool_calls(self, response: str) -> list:
        """
        Extract tool calls from agent's thinking response.
        
        Looks for explicit mentions of tool names or infers from keywords.
        
        Args:
            response: The agent's thinking response
            
        Returns:
            List of (tool_name, tool_args) tuples
        """
        tool_calls = []
        
        # Look for explicit mentions of tool names
        if "get_courses" in response:
            tool_calls.append(("get_courses", None))
        
        if "get_deadlines" in response:
            tool_calls.append(("get_deadlines", None))
        
        # If no explicit tool mentions, infer from keywords
        if not tool_calls:
            response_lower = response.lower()
            if any(word in response_lower for word in ["deadline", "devoir", "assignment", "due"]):
                tool_calls.append(("get_deadlines", None))
            elif any(word in response_lower for word in ["cours", "course", "subject", "class"]):
                tool_calls.append(("get_courses", None))
        
        return tool_calls

def main():
    """
    Main entry point for CLI conversation loop.
    
    Allows users to interact with the agent from the command line.
    Useful for testing and development.
    """
    print("\n" + "="*60)
    print("   ESILV Academic Assistant - ReAct Agent")
    print("="*60)
    print("\nAssistant: Hello! I'm your ESILV academic assistant.")
    print("I can help you search for courses and check your deadlines.")
    print("Type 'exit', 'quit' to quit.\n")
    
    # Create agent
    try:
        agent = ReActAgent(llm, tools.TOOLS)
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return
    
    # Main conversation loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nAssistant: Goodbye! Good luck with your studies!")
                break
            
            # Run agent (with thinking and tool use)
            logger.info(f"Processing: {user_input}")
            print("\nAssistant: [Thinking and consulting resources...]")
            
            response = agent.invoke(user_input)
            print(f"\nAssistant: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nAssistant: Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Assistant: An error occurred: {e}\n")

if __name__ == "__main__":
    main()