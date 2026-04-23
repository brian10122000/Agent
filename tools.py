"""
tools.py — Outils de l'agent IA
Utilise Google Gemini (GRATUIT) pour la génération de code et d'apps.
"""

import os
import json
import subprocess
import requests
import shutil
import sys
import platform
from pathlib import Path
from datetime import datetime

from langchain.tools import tool

WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)


# ── LLM interne pour génération de code (Gemini gratuit) ──────
def _get_llm():
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key   = os.getenv("GROQ_API_KEY")

    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
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
        raise EnvironmentError("❌ Ajoute GEMINI_API_KEY ou GROQ_API_KEY dans .env")


def _ask_llm(prompt: str) -> str:
    """Appelle le LLM et retourne le texte de réponse."""
    from langchain_core.messages import HumanMessage
    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


# ═══════════════════════════════════════════════════════════════
#  📁 FICHIERS
# ═══════════════════════════════════════════════════════════════

@tool
def read_file(filename: str) -> str:
    """Lit le contenu d'un fichier du workspace. Paramètre : nom du fichier."""
    filepath = WORKSPACE / filename
    if not filepath.exists():
        return f"❌ Fichier '{filename}' introuvable."
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Erreur lecture : {e}"


@tool
def write_file(input: str) -> str:
    """
    Écrit du contenu dans un fichier du workspace.
    Paramètre JSON : {"filename": "app.py", "content": "print('hello')"}
    """
    try:
        data = json.loads(input)
        filename = data["filename"]
        content = data["content"]
    except Exception:
        return '❌ Format invalide. Utilise : {"filename": "...", "content": "..."}'
    filepath = WORKSPACE / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return f"✅ '{filename}' écrit ({len(content)} caractères)."


@tool
def list_files(dummy: str = "") -> str:
    """Liste tous les fichiers et dossiers du workspace."""
    items = list(WORKSPACE.rglob("*"))
    if not items:
        return "📂 Le workspace est vide."
    lines = [f"📂 Workspace :"]
    for item in sorted(items):
        rel = item.relative_to(WORKSPACE)
        prefix = "  📁 " if item.is_dir() else "  📄 "
        size = f"({item.stat().st_size} o)" if item.is_file() else ""
        lines.append(f"{prefix}{rel} {size}")
    return "\n".join(lines)


@tool
def delete_file(filename: str) -> str:
    """Supprime un fichier ou dossier du workspace."""
    filepath = WORKSPACE / filename
    if not filepath.exists():
        return f"❌ '{filename}' introuvable."
    if filepath.is_dir():
        shutil.rmtree(filepath)
        return f"🗑️ Dossier '{filename}' supprimé."
    filepath.unlink()
    return f"🗑️ Fichier '{filename}' supprimé."


@tool
def create_folder(folder_name: str) -> str:
    """Crée un dossier dans le workspace."""
    (WORKSPACE / folder_name).mkdir(parents=True, exist_ok=True)
    return f"✅ Dossier '{folder_name}' créé."


# ═══════════════════════════════════════════════════════════════
#  🚀 GÉNÉRATION D'APPLICATIONS
# ═══════════════════════════════════════════════════════════════

@tool
def generate_app(input: str) -> str:
    """
    Génère une application complète (site web, app Python, jeu, API, bot...)
    à partir d'une description. Sauvegarde tous les fichiers dans le workspace.

    Paramètre JSON : {"description": "jeu snake Python", "app_name": "snake"}
    Ou simple texte : "Crée une calculatrice HTML/CSS/JS"
    """
    try:
        if input.strip().startswith("{"):
            data = json.loads(input)
            description = data.get("description", input)
            app_name = data.get("app_name", "mon_app")
        else:
            description = input
            app_name = "mon_app"
    except Exception:
        description = input
        app_name = "mon_app"

    app_folder = WORKSPACE / app_name
    app_folder.mkdir(parents=True, exist_ok=True)

    prompt = f"""Tu es un expert développeur. Génère une application COMPLÈTE et FONCTIONNELLE.

DESCRIPTION : {description}

RÈGLES STRICTES :
1. Code COMPLET, aucun placeholder ni "à compléter"
2. Délimite chaque fichier EXACTEMENT ainsi (pas d'espace avant ===) :
===FILE: nom_fichier.ext===
[contenu complet]
===END===
3. Inclus README.txt avec les commandes de lancement
4. Pour Python : inclus requirements.txt si libs externes nécessaires
5. Pour sites web : tout dans index.html (CSS+JS inclus)
6. Commentaires en français
7. Commence DIRECTEMENT par ===FILE: sans introduction ni explication

Génère l'application maintenant :"""

    try:
        raw = _ask_llm(prompt)
    except Exception as e:
        return f"❌ Erreur LLM : {e}"

    # Parser les fichiers
    files_created = []
    current_file = None
    current_content = []

    for line in raw.split("\n"):
        if line.startswith("===FILE:") and line.endswith("==="):
            if current_file and current_content:
                fp = app_folder / current_file
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text("\n".join(current_content), encoding="utf-8")
                files_created.append(str(fp.relative_to(WORKSPACE)))
            current_file = line[8:-3].strip()
            current_content = []
        elif line == "===END===":
            if current_file and current_content:
                fp = app_folder / current_file
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text("\n".join(current_content), encoding="utf-8")
                files_created.append(str(fp.relative_to(WORKSPACE)))
            current_file = None
            current_content = []
        elif current_file is not None:
            current_content.append(line)

    # Dernier fichier sans ===END===
    if current_file and current_content:
        fp = app_folder / current_file
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("\n".join(current_content), encoding="utf-8")
        files_created.append(str(fp.relative_to(WORKSPACE)))

    if not files_created:
        fallback = app_folder / "output.txt"
        fallback.write_text(raw, encoding="utf-8")
        return f"⚠️ Sauvegardé dans workspace/{app_name}/output.txt"

    result = [f"✅ '{app_name}' généré — {len(files_created)} fichier(s) :"]
    for f in files_created:
        result.append(f"  📄 workspace/{f}")

    readme = app_folder / "README.txt"
    if readme.exists():
        result.append("\n📋 Lancement :")
        result.append(readme.read_text(encoding="utf-8")[:400])

    return "\n".join(result)


@tool
def generate_and_run_python(input: str) -> str:
    """
    Génère un script Python et l'exécute immédiatement. Retourne le résultat.
    Paramètre : description de ce que le script doit faire.
    Exemple : "Calcule les 20 premiers nombres premiers"
    """
    prompt = f"""Génère un script Python court et fonctionnel qui fait :
{input}

RÈGLES :
- Stdlib Python uniquement (pas de pip install)
- Utilise print() pour afficher les résultats
- Pas d'input() interactif
- Commence directement avec le code, sans backticks ni explication

Code Python :"""

    try:
        code = _ask_llm(prompt).strip()
        # Nettoyer les backticks
        if "```" in code:
            lines = code.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            code = "\n".join(lines)
    except Exception as e:
        return f"❌ Erreur génération : {e}"

    script_path = WORKSPACE / "_temp_script.py"
    script_path.write_text(code, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip() or "(pas de sortie)"
        errors = result.stderr.strip()
        if errors and not result.stdout.strip():
            return f"❌ Erreur :\n{errors}\n\nCode :\n{code[:400]}"
        parts = [f"✅ Exécuté !\n\n📤 Résultat :\n{output}"]
        if errors:
            parts.append(f"\n⚠️ Warnings :\n{errors[:200]}")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "⏱️ Timeout (30s dépassé)."
    except Exception as e:
        return f"❌ Erreur : {e}"


@tool
def generate_bot_discord(description: str) -> str:
    """
    Génère un bot Discord complet (discord.py) à partir d'une description.
    Exemple : "Un bot qui envoie une blague toutes les heures"
    """
    return generate_app.invoke(json.dumps({
        "description": f"Bot Discord avec discord.py : {description}. Inclure bot.py, .env.example, README.txt.",
        "app_name": "bot_genere"
    }))


# ═══════════════════════════════════════════════════════════════
#  🌐 WEB
# ═══════════════════════════════════════════════════════════════

@tool
def web_search_tool(query: str) -> str:
    """Recherche sur le web via DuckDuckGo (sans clé API). Paramètre : requête."""
    try:
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        resp = requests.get("https://api.duckduckgo.com/", params=params, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        results = []
        if data.get("AbstractText"):
            results.append(f"📌 {data['AbstractText'][:300]}\n   🔗 {data.get('AbstractURL','')}")
        for item in data.get("RelatedTopics", [])[:5]:
            if isinstance(item, dict) and item.get("Text"):
                results.append(f"• {item['Text'][:150]}\n  🔗 {item.get('FirstURL','')}")
        if not results:
            return f"🔍 Aucun résultat pour '{query}'."
        return f"🔍 Résultats :\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"❌ Erreur recherche : {e}"


@tool
def scrape_webpage(url: str) -> str:
    """Extrait le texte d'une page web. Paramètre : URL complète."""
    try:
        import re
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 2000:
            text = text[:2000] + "… [tronqué]"
        return f"🌐 {url} :\n\n{text}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@tool
def download_file_from_url(input: str) -> str:
    """
    Télécharge un fichier dans le workspace.
    Paramètre JSON : {"url": "https://...", "filename": "nom.ext"}
    """
    try:
        data = json.loads(input)
        resp = requests.get(data["url"], timeout=30, stream=True,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        fp = WORKSPACE / data["filename"]
        with open(fp, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return f"✅ '{data['filename']}' téléchargé ({fp.stat().st_size} octets)."
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════
#  🖥️ SYSTÈME
# ═══════════════════════════════════════════════════════════════

@tool
def run_shell_command(command: str) -> str:
    """
    Exécute une commande shell (Termux/Linux). ⚠️ Utilise avec précaution.
    Paramètre : commande shell. Ex: "ls workspace", "python3 workspace/app.py"
    """
    BLOCKED = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:"]
    for b in BLOCKED:
        if b in command:
            return f"🚫 Commande bloquée : '{b}'"
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=60, cwd=str(WORKSPACE.parent)
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        parts = []
        if out:
            parts.append(f"📤 Sortie :\n{out[:1500]}")
        if err:
            parts.append(f"⚠️ Erreurs :\n{err[:500]}")
        return "\n".join(parts) if parts else "✅ Commande exécutée (pas de sortie)."
    except subprocess.TimeoutExpired:
        return "⏱️ Timeout (60s)."
    except Exception as e:
        return f"❌ Erreur : {e}"


@tool
def install_package(package_name: str) -> str:
    """Installe un package Python via pip. Paramètre : nom du package."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return f"✅ '{package_name}' installé."
        return f"❌ Erreur : {result.stderr[:300]}"
    except subprocess.TimeoutExpired:
        return f"⏱️ Installation trop longue."
    except Exception as e:
        return f"❌ Erreur : {e}"


@tool
def get_system_info(dummy: str = "") -> str:
    """Retourne les infos système (OS, Python, espace disque)."""
    info = {
        "OS": platform.system(),
        "Version": platform.version()[:50],
        "Machine": platform.machine(),
        "Python": sys.version.split()[0],
        "Workspace": str(WORKSPACE.resolve()),
    }
    try:
        disk = shutil.disk_usage(WORKSPACE)
        info["Disque libre"] = f"{disk.free // (1024**2)} MB"
    except Exception:
        pass
    return "💻 Système :\n" + "\n".join(f"  • {k} : {v}" for k, v in info.items())


# ═══════════════════════════════════════════════════════════════
#  🗄️ AIRTABLE
# ═══════════════════════════════════════════════════════════════

@tool
def airtable_get_records(table_name: str) -> str:
    """Récupère les enregistrements d'une table Airtable. Nécessite AIRTABLE_API_KEY + AIRTABLE_BASE_ID."""
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        return "❌ AIRTABLE_API_KEY et AIRTABLE_BASE_ID manquants dans .env"
    try:
        resp = requests.get(
            f"https://api.airtable.com/v0/{base_id}/{requests.utils.quote(table_name)}",
            headers={"Authorization": f"Bearer {api_key}"}, timeout=10
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            return f"📋 Table '{table_name}' vide."
        lines = [f"📋 {len(records)} enregistrement(s) :"]
        for r in records[:10]:
            lines.append(f"  • {r['id']} | {json.dumps(r.get('fields',{}), ensure_ascii=False)}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Erreur Airtable : {e}"


@tool
def airtable_create_record(input: str) -> str:
    """
    Crée un enregistrement Airtable.
    Paramètre JSON : {"table": "Tâches", "fields": {"Nom": "Rapport"}}
    """
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        return "❌ AIRTABLE_API_KEY et AIRTABLE_BASE_ID manquants dans .env"
    try:
        data = json.loads(input)
        resp = requests.post(
            f"https://api.airtable.com/v0/{base_id}/{requests.utils.quote(data['table'])}",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"fields": data["fields"]}, timeout=10
        )
        resp.raise_for_status()
        return f"✅ Enregistrement créé : {resp.json()['id']}"
    except Exception as e:
        return f"❌ Erreur Airtable : {e}"


# ═══════════════════════════════════════════════════════════════
#  📊 GOOGLE SHEETS
# ═══════════════════════════════════════════════════════════════

@tool
def sheets_read(input: str) -> str:
    """
    Lit une Google Sheet.
    Paramètre JSON : {"spreadsheet_id": "...", "range": "Feuille1!A1:C5"}
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        data = json.loads(input)
        creds = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json"),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
        service = build("sheets", "v4", credentials=creds)
        values = service.spreadsheets().values().get(
            spreadsheetId=data["spreadsheet_id"], range=data["range"]
        ).execute().get("values", [])
        if not values:
            return "📊 Aucune donnée."
        return "📊 Données :\n" + "\n".join("  | " + " | ".join(str(c) for c in row) + " |" for row in values)
    except ImportError:
        return "❌ Installe : pip install google-auth google-auth-httplib2 google-api-python-client"
    except Exception as e:
        return f"❌ Erreur Sheets : {e}"


@tool
def sheets_write(input: str) -> str:
    """
    Écrit dans une Google Sheet.
    Paramètre JSON : {"spreadsheet_id": "...", "range": "A1", "values": [["Nom","Score"]]}
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        data = json.loads(input)
        creds = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"])
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().update(
            spreadsheetId=data["spreadsheet_id"], range=data["range"],
            valueInputOption="USER_ENTERED", body={"values": data["values"]}
        ).execute()
        return f"✅ {result.get('updatedCells', 0)} cellule(s) mise(s) à jour."
    except ImportError:
        return "❌ Installe : pip install google-auth google-auth-httplib2 google-api-python-client"
    except Exception as e:
        return f"❌ Erreur Sheets : {e}"


# ═══════════════════════════════════════════════════════════════
#  🛠️ UTILITAIRES IA
# ═══════════════════════════════════════════════════════════════

@tool
def get_current_datetime(dummy: str = "") -> str:
    """Retourne la date et l'heure actuelles."""
    return f"🕐 {datetime.now().strftime('%A %d %B %Y à %H:%M:%S')}"


@tool
def summarize_file(filename: str) -> str:
    """Lit un fichier et génère un résumé intelligent. Paramètre : nom du fichier."""
    fp = WORKSPACE / filename
    if not fp.exists():
        return f"❌ '{filename}' introuvable."
    try:
        content = fp.read_text(encoding="utf-8")[:6000]
    except Exception as e:
        return f"❌ Erreur lecture : {e}"
    try:
        result = _ask_llm(f"Résume ce fichier ({filename}) de façon claire en français :\n\n{content}")
        return f"📋 Résumé de '{filename}' :\n\n{result}"
    except Exception as e:
        return f"❌ Erreur résumé : {e}"


@tool
def convert_text(input: str) -> str:
    """
    Transforme du texte via l'IA (traduire, reformater, JSON→CSV...).
    Paramètre JSON : {"text": "...", "instruction": "Traduis en anglais"}
    """
    try:
        data = json.loads(input)
    except Exception:
        return '❌ Format invalide. Utilise : {"text": "...", "instruction": "..."}'
    try:
        result = _ask_llm(f"Instruction : {data['instruction']}\n\nTexte :\n{data['text']}\n\nRésultat :")
        return f"✅ Résultat :\n{result}"
    except Exception as e:
        return f"❌ Erreur : {e}"


# ── Export ─────────────────────────────────────────────────────
ALL_TOOLS = [
    read_file, write_file, list_files, delete_file, create_folder,
    generate_app, generate_and_run_python, generate_bot_discord,
    web_search_tool, scrape_webpage, download_file_from_url,
    run_shell_command, install_package, get_system_info,
    airtable_get_records, airtable_create_record,
    sheets_read, sheets_write,
    get_current_datetime, summarize_file, convert_text,
]
