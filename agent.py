"""ESILV Academic Assistant - ReAct Agent using LangChain with Ollama"""

import logging
import re
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

# System prompt for the agent
SYSTEM_PROMPT = """Tu es un assistant académique pour les étudiants de l'ESILV.
Réponds aux questions naturellement et utilise les outils disponibles pour récupérer les informations à jour depuis la plateforme Moodle De Vinci.
IMPORTANT : N'utilise un outil uniquement lorsqu'il est nécessaire pour répondre aux questions de l'étudiant.

OUTILS DISPONIBLES:
1. get_courses() - Récupère la LISTE COMPLÈTE de tous les cours
   UTILISE SI: L'étudiant demande ses cours, la liste des cours, "mes cours", "tous les cours"
   
2. get_deadlines() - Récupère les deadlines à venir
   UTILISE SI: L'étudiant demande les deadlines, les travaux à rendre

INSTRUCTIONS ABSOLUES:
1. SOIS HONNÊTE: Si tu appelles un outil, dis-le clairement
2. NE JAMAIS INVENTER de données (pas de "Python : 1 cours", pas de listes fictives)
3. UTILISE LES OUTILS pour obtenir les vraies données
4. SI L'OUTIL ÉCHOUE (erreur, pas d'identifiants): DIS-LE CLAIREMENT
5. NE FAIS AUCUNE HYPOTHÈSE sur les résultats

SOIS PRÉCIS ET HONNÊTE. Ne specule jamais."""

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
        
        Étudiant: {user_input}

        Maintenant, dans ta <Pensée>, explique ce que tu vas faire et quel outil(s) tu vas utiliser."""
        
        thinking_response = self.llm.invoke(thinking_prompt)
        logger.info(f"Agent thinking: {thinking_response[:200]}")
        
        # Step 2: Extract which tool(s) the agent wants to use
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
                    all_results[tool_name] = f"Erreur lors de l'exécution: {e}"
        
        # Step 4: Generate final answer based on tool results
        final_prompt = f"""{SYSTEM_PROMPT}

Étudiant: {user_input}

Ton analyse et réflexion:
{thinking_response}

Résultats des outils:
"""
        
        for tool_name, result in all_results.items():
            final_prompt += f"\n{tool_name}: {result}"
        
        final_prompt += "\n\nMaintenant, fournis une réponse complète et utile à l'étudiant en français."
        
        final_response = self.llm.invoke(final_prompt)
        
        return final_response
    
    def _extract_tool_calls(self, response: str) -> list:
        """Extract tool calls from agent response"""
        tool_calls = []
        
        # Look for patterns like "get_courses" or "get_deadlines"
        if "get_courses" in response:
            tool_calls.append(("get_courses", None))
        
        if "get_deadlines" in response:
            tool_calls.append(("get_deadlines", None))
        
        # If no explicit tool mentions, infer from keywords
        if not tool_calls:
            response_lower = response.lower()
            if any(word in response_lower for word in ["deadline", "devoir"]):
                tool_calls.append(("get_deadlines", None))
            elif any(word in response_lower for word in ["cours", "matière"]):
                tool_calls.append(("get_courses", None))
        
        return tool_calls

def main():
    """Main conversation loop"""
    print("\n" + "="*60)
    print("   ESILV Academic Assistant - ReAct Agent")
    print("="*60)
    print("\nAssistant: Bonjour! Je suis ton assistant académique ESILV.")
    print("Je peux t'aider à rechercher des cours et consulter tes deadlines.")
    print("Tape 'exit', 'quit' ou 'quitter' pour terminer.\n")
    
    # Create agent
    try:
        agent = ReActAgent(llm, tools.TOOLS)
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return
    
    # Main conversation loop
    while True:
        try:
            user_input = input("Toi: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "quitter"]:
                print("\nAssistant: À bientôt! Bon courage pour tes études! 📚")
                break
            
            # Run agent (with thinking and tool use)
            logger.info(f"Processing: {user_input}")
            print("\nAssistant: [Je réfléchis et je consulte les ressources...]")
            
            response = agent.invoke(user_input)
            print(f"\nAssistant: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nAssistant: À bientôt! 👋")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Assistant: Une erreur est survenue: {e}\n")

if __name__ == "__main__":
    main()