"""
agent.py — Cerveau de l'IA
Gemini GRATUIT — Compatible LangChain 0.3.x
"""

import os
from collections import defaultdict
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate

from tools import ALL_TOOLS

load_dotenv()


def _build_llm():
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key   = os.getenv("GROQ_API_KEY")

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=gemini_key,
            temperature=0.2,
            convert_system_message_to_human=True,
        )
    elif groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_key,
            temperature=0.2,
        )
    else:
        raise EnvironmentError(
            "❌ Ajoute GEMINI_API_KEY dans les variables Railway.\n"
            "Clé gratuite sur : aistudio.google.com"
        )


SYSTEM_PROMPT = """Tu es un assistant IA puissant intégré à Discord.
Tu aides les utilisateurs à exécuter des tâches réelles : lire/écrire des fichiers,
générer des applications complètes, faire des recherches web, et bien plus.

Tu raisonnes étape par étape avant d'agir.
Réponds toujours en français sauf demande contraire.

Outils disponibles :
{tools}

Format OBLIGATOIRE :
Question: la question de l'utilisateur
Thought: ma réflexion
Action: nom_outil
Action Input: entrée pour l'outil
Observation: résultat
... (répéter si nécessaire)
Thought: j'ai la réponse
Final Answer: réponse complète

Outils disponibles : [{tool_names}]

Historique :
{chat_history}

Question: {input}
{agent_scratchpad}"""


_memories: dict = defaultdict(
    lambda: ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=int(os.getenv("MEMORY_MAX_MESSAGES", "20")),
        return_messages=False,
    )
)

def get_memory(user_id: str) -> ConversationBufferWindowMemory:
    return _memories[str(user_id)]

def clear_memory(user_id: str) -> None:
    _memories.pop(str(user_id), None)


_llm    = _build_llm()
_prompt = PromptTemplate.from_template(SYSTEM_PROMPT)
_react_agent = create_react_agent(llm=_llm, tools=ALL_TOOLS, prompt=_prompt)


def run_agent(user_id: str, message: str) -> str:
    memory = get_memory(user_id)
    executor = AgentExecutor(
        agent=_react_agent,
        tools=ALL_TOOLS,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        return_intermediate_steps=False,
    )
    try:
        result = executor.invoke({"input": message})
        return result.get("output", "⚠️ Pas de réponse générée.")
    except Exception as e:
        return f"❌ Erreur agent : {e}"

