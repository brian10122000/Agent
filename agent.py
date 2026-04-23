"""
agent.py — Cerveau de l'IA
Utilise Google Gemini (100% GRATUIT, sans carte bancaire).
Mémoire par utilisateur Discord.
"""

import os
from collections import defaultdict
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate
from tools import ALL_TOOLS

load_dotenv()

# ── LLM : Google Gemini GRATUIT ───────────────────────────────
def _build_llm():
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key   = os.getenv("GROQ_API_KEY")

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",   # Modèle gratuit le plus rapide
            google_api_key=gemini_key,
            temperature=0.2,
            convert_system_message_to_human=True,
        )
    elif groq_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",  # Gratuit sur Groq
            groq_api_key=groq_key,
            temperature=0.2,
        )
    else:
        raise EnvironmentError(
            "❌ Aucune clé trouvée.\n"
            "Ajoute GEMINI_API_KEY dans .env (gratuit sur aistudio.google.com)\n"
            "Ou GROQ_API_KEY (gratuit sur groq.com)"
        )


# ── Prompt système ────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant IA puissant intégré à Discord.
Tu aides les utilisateurs à exécuter des tâches réelles : lire/écrire des fichiers,
générer des applications, faire des recherches web, et bien plus.

Tu raisonnes étape par étape avant d'agir.
Réponds toujours en français sauf demande contraire.
Sois précis, concis et utile.

Outils disponibles :
{tools}

Format OBLIGATOIRE :
Question: la question de l'utilisateur
Thought: ma réflexion sur ce que je dois faire
Action: nom_de_l_outil
Action Input: entrée pour l'outil
Observation: résultat de l'outil
... (répéter si nécessaire)
Thought: j'ai la réponse finale
Final Answer: réponse complète à l'utilisateur

Noms d'outils disponibles : [{tool_names}]

Historique :
{chat_history}

Question: {input}
{agent_scratchpad}"""


# ── Mémoire par utilisateur ───────────────────────────────────
_memories: dict = defaultdict(
    lambda: ConversationBufferWindowMemory(
        memory_key="chat_history",
        k=int(os.getenv("MEMORY_MAX_MESSAGES", 20)),
        return_messages=False,
    )
)

def get_memory(user_id: str):
    return _memories[str(user_id)]

def clear_memory(user_id: str):
    _memories.pop(str(user_id), None)


# ── Construction de l'agent ───────────────────────────────────
_llm = _build_llm()
_prompt = PromptTemplate.from_template(SYSTEM_PROMPT)
_react_agent = create_react_agent(llm=_llm, tools=ALL_TOOLS, prompt=_prompt)


def run_agent(user_id: str, message: str) -> str:
    """Point d'entrée : exécute l'agent pour un utilisateur Discord."""
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
