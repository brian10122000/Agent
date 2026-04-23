"""
bot.py — Interface Discord avec commandes slash complètes
Toutes les commandes sont disponibles via / dans Discord.
"""

import os
import asyncio
import textwrap
from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from agent import run_agent, clear_memory, get_memory

load_dotenv()

# ── Configuration ──────────────────────────────────────────────
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MAX_LEN = 1900  # Limite Discord 2000 chars

if not DISCORD_TOKEN:
    raise EnvironmentError("❌ DISCORD_TOKEN manquant dans .env")

intents = discord.Intents.default()
intents.message_content = True

# ── Bot avec support slash commands ───────────────────────────
class AgentBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Synchronise les slash commands avec Discord
        await self.tree.sync()
        print("✅ Slash commands synchronisées avec Discord.")

    async def on_ready(self):
        print(f"✅ Connecté : {self.user} (ID: {self.user.id})")
        print(f"   Serveurs : {len(self.guilds)}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/aide pour les commandes"
            )
        )

bot = AgentBot()


# ═══════════════════════════════════════════════════════════════
#  UTILITAIRES
# ═══════════════════════════════════════════════════════════════

async def run_in_thread(user_id: str, message: str) -> str:
    """Exécute l'agent dans un thread séparé (non bloquant)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_agent, user_id, message)


async def send_response(interaction: discord.Interaction, text: str, ephemeral: bool = False):
    """
    Envoie une réponse en découpant si nécessaire.
    Gère les réponses déjà envoyées (followup vs respond).
    """
    chunks = textwrap.wrap(text, MAX_LEN, replace_whitespace=False, break_long_words=True)
    if not chunks:
        chunks = [text]

    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(chunks[0], ephemeral=ephemeral)
        else:
            await interaction.followup.send(chunks[0], ephemeral=ephemeral)
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk, ephemeral=ephemeral)
    except Exception as e:
        try:
            await interaction.followup.send(f"❌ Erreur envoi : {e}", ephemeral=True)
        except Exception:
            pass


def make_embed(title: str, description: str, color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    """Crée un embed Discord formaté."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Agent IA Discord • Propulsé par Claude")
    return embed


# ═══════════════════════════════════════════════════════════════
#  🤖 COMMANDES IA PRINCIPALES
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="ia", description="🤖 Envoie un ordre à l'agent IA (texte, analyse, question...)")
@app_commands.describe(ordre="Que veux-tu que l'IA fasse ? Sois précis !")
async def slash_ia(interaction: discord.Interaction, ordre: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, ordre)
    await send_response(interaction, response)


@bot.tree.command(name="generer", description="🚀 Génère une application complète (site, jeu, bot, script...)")
@app_commands.describe(
    description="Décris l'app à créer (ex: 'un jeu snake en Python')",
    nom="Nom du dossier où sauvegarder (ex: 'mon_jeu')"
)
async def slash_generer(interaction: discord.Interaction, description: str, nom: str = "mon_app"):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    prompt = f"Génère une application complète : {description}. Nom du projet : {nom}"
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


@bot.tree.command(name="executer", description="⚡ Génère et exécute un script Python immédiatement")
@app_commands.describe(tache="Que doit faire le script ? (ex: 'calcule les 100 premiers nombres premiers')")
async def slash_executer(interaction: discord.Interaction, tache: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    prompt = f"Génère et exécute immédiatement un script Python qui fait : {tache}"
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


@bot.tree.command(name="analyser", description="🔍 Analyse un fichier du workspace (résumé, données, code...)")
@app_commands.describe(fichier="Nom du fichier à analyser (ex: 'data.csv', 'script.py')")
async def slash_analyser(interaction: discord.Interaction, fichier: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    prompt = f"Lis et analyse en détail le fichier '{fichier}' : résumé, points importants, suggestions."
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


@bot.tree.command(name="convertir", description="🔄 Convertit ou transforme du texte via l'IA")
@app_commands.describe(
    texte="Le texte à convertir/transformer",
    instruction="Que faire avec ce texte ? (ex: 'traduis en anglais', 'formate en JSON')"
)
async def slash_convertir(interaction: discord.Interaction, texte: str, instruction: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    import json
    prompt = f"Convertis ce texte. Instruction : {instruction}\n\nTexte : {texte}"
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  📁 COMMANDES FICHIERS
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="fichiers", description="📂 Liste tous les fichiers du workspace")
async def slash_fichiers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, "Liste tous les fichiers et dossiers du workspace en détail.")
    await send_response(interaction, response)


@bot.tree.command(name="lire", description="📄 Lit le contenu d'un fichier du workspace")
@app_commands.describe(fichier="Nom du fichier à lire (ex: 'notes.txt')")
async def slash_lire(interaction: discord.Interaction, fichier: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Lis et affiche le contenu complet du fichier '{fichier}'.")
    await send_response(interaction, response)


@bot.tree.command(name="ecrire", description="✏️ Crée ou écrase un fichier dans le workspace")
@app_commands.describe(
    fichier="Nom du fichier à créer (ex: 'todo.txt')",
    contenu="Contenu à écrire dans le fichier"
)
async def slash_ecrire(interaction: discord.Interaction, fichier: str, contenu: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Écris ce contenu dans le fichier '{fichier}' : {contenu}")
    await send_response(interaction, response)


@bot.tree.command(name="supprimer", description="🗑️ Supprime un fichier ou dossier du workspace")
@app_commands.describe(fichier="Nom du fichier/dossier à supprimer")
async def slash_supprimer(interaction: discord.Interaction, fichier: str):
    await interaction.response.defer(thinking=True)

    # Confirmation avant suppression
    embed = make_embed(
        "⚠️ Confirmation",
        f"Es-tu sûr de vouloir supprimer `{fichier}` ?\nCette action est irréversible.",
        discord.Color.orange()
    )
    view = ConfirmView(interaction.user.id, fichier)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="telecharger", description="⬇️ Télécharge un fichier depuis une URL dans le workspace")
@app_commands.describe(
    url="URL du fichier à télécharger",
    nom="Nom à donner au fichier (ex: 'image.png')"
)
async def slash_telecharger(interaction: discord.Interaction, url: str, nom: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Télécharge le fichier depuis cette URL : {url} et sauvegarde-le sous le nom '{nom}'.")
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  🌐 COMMANDES WEB
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="rechercher", description="🔍 Recherche sur le web et résume les résultats")
@app_commands.describe(requete="Ta recherche (ex: 'meilleurs frameworks Python 2025')")
async def slash_rechercher(interaction: discord.Interaction, requete: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Fais une recherche web sur : {requete}. Résume les meilleurs résultats.")
    await send_response(interaction, response)


@bot.tree.command(name="scraper", description="🌐 Extrait le contenu texte d'une page web")
@app_commands.describe(url="URL de la page à lire (ex: https://example.com)")
async def slash_scraper(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Extrait et résume le contenu de cette page web : {url}")
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  🖥️ COMMANDES SYSTÈME
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="shell", description="💻 Exécute une commande shell (Termux/Linux)")
@app_commands.describe(commande="Commande à exécuter (ex: 'ls workspace', 'python3 script.py')")
async def slash_shell(interaction: discord.Interaction, commande: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Exécute cette commande shell : {commande}")
    await send_response(interaction, response)


@bot.tree.command(name="installer", description="📦 Installe un package Python via pip")
@app_commands.describe(package="Nom du package à installer (ex: 'flask', 'pandas', 'pygame')")
async def slash_installer(interaction: discord.Interaction, package: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Installe le package Python : {package}")
    await send_response(interaction, response)


@bot.tree.command(name="systeme", description="💻 Affiche les infos système (OS, Python, espace disque...)")
async def slash_systeme(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, "Donne-moi toutes les informations système disponibles.")
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  🗄️ COMMANDES BASES DE DONNÉES
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="airtable-lire", description="🗄️ Lit les enregistrements d'une table Airtable")
@app_commands.describe(table="Nom de la table Airtable (ex: 'Projets', 'Clients')")
async def slash_airtable_lire(interaction: discord.Interaction, table: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Récupère tous les enregistrements de la table Airtable : {table}")
    await send_response(interaction, response)


@bot.tree.command(name="airtable-ajouter", description="🗄️ Ajoute un enregistrement dans Airtable")
@app_commands.describe(
    table="Nom de la table (ex: 'Tâches')",
    donnees="Données en format clé:valeur séparées par virgule (ex: 'Nom:Rapport,Statut:En cours')"
)
async def slash_airtable_ajouter(interaction: discord.Interaction, table: str, donnees: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(
        user_id,
        f"Crée un enregistrement dans la table Airtable '{table}' avec ces données : {donnees}"
    )
    await send_response(interaction, response)


@bot.tree.command(name="sheets-lire", description="📊 Lit des cellules d'une Google Sheet")
@app_commands.describe(
    spreadsheet_id="ID de la Google Sheet (dans l'URL)",
    plage="Plage de cellules (ex: 'Feuille1!A1:D10')"
)
async def slash_sheets_lire(interaction: discord.Interaction, spreadsheet_id: str, plage: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(
        user_id,
        f"Lis les données de la Google Sheet {spreadsheet_id} dans la plage {plage}"
    )
    await send_response(interaction, response)


@bot.tree.command(name="sheets-ecrire", description="📊 Écrit des données dans une Google Sheet")
@app_commands.describe(
    spreadsheet_id="ID de la Google Sheet",
    plage="Cellule de départ (ex: 'Feuille1!A1')",
    donnees="Données séparées par | pour les colonnes, / pour les lignes (ex: 'Nom|Age / Alice|25')"
)
async def slash_sheets_ecrire(interaction: discord.Interaction, spreadsheet_id: str, plage: str, donnees: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(
        user_id,
        f"Écris dans la Google Sheet {spreadsheet_id} à partir de {plage} ces données : {donnees}"
    )
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  🧠 COMMANDES MÉMOIRE & CONVERSATION
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="reset", description="🧹 Efface ta mémoire de conversation (nouveau départ)")
async def slash_reset(interaction: discord.Interaction):
    clear_memory(str(interaction.user.id))
    embed = make_embed(
        "🧹 Mémoire effacée",
        "Ta conversation a été réinitialisée. L'agent repart de zéro !",
        discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="memoire", description="🧠 Affiche le résumé de ta mémoire de conversation")
async def slash_memoire(interaction: discord.Interaction):
    memory = get_memory(str(interaction.user.id))
    hist = memory.load_memory_variables({}).get("chat_history", "")
    if not hist:
        await interaction.response.send_message(
            "🧠 Aucune mémoire enregistrée. Commence à parler avec `/ia` !",
            ephemeral=True
        )
        return
    # Tronquer si trop long
    display = hist[:1500] + ("…" if len(hist) > 1500 else "")
    embed = make_embed("🧠 Ta mémoire de conversation", f"```\n{display}\n```", discord.Color.purple())
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  🎨 COMMANDES CRÉATIVES
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="rediger", description="✍️ Rédige un texte : email, article, rapport, histoire...")
@app_commands.describe(
    type_texte="Type de texte (ex: 'email professionnel', 'article de blog', 'histoire courte')",
    sujet="Sujet ou contexte du texte",
    longueur="Longueur souhaitée (ex: 'court', 'moyen', '500 mots')"
)
async def slash_rediger(interaction: discord.Interaction, type_texte: str, sujet: str, longueur: str = "moyen"):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    prompt = f"Rédige un {type_texte} sur le sujet suivant : {sujet}. Longueur : {longueur}."
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


@bot.tree.command(name="traduire", description="🌍 Traduit du texte dans n'importe quelle langue")
@app_commands.describe(
    texte="Texte à traduire",
    langue="Langue cible (ex: 'anglais', 'espagnol', 'japonais')"
)
async def slash_traduire(interaction: discord.Interaction, texte: str, langue: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Traduis ce texte en {langue} : {texte}")
    await send_response(interaction, response)


@bot.tree.command(name="resumer", description="📋 Résume un texte long en points clés")
@app_commands.describe(
    texte="Texte à résumer",
    format_sortie="Format du résumé (ex: 'bullet points', 'paragraphe', '3 phrases')"
)
async def slash_resumer(interaction: discord.Interaction, texte: str, format_sortie: str = "bullet points"):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Résume ce texte en {format_sortie} : {texte}")
    await send_response(interaction, response)


@bot.tree.command(name="code", description="💻 Génère du code dans n'importe quel langage")
@app_commands.describe(
    langage="Langage de programmation (ex: 'Python', 'JavaScript', 'SQL')",
    description="Ce que le code doit faire"
)
async def slash_code(interaction: discord.Interaction, langage: str, description: str):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"Génère du code {langage} qui fait : {description}. Explique chaque partie.")
    await send_response(interaction, response)


@bot.tree.command(name="corriger", description="🔧 Corrige et améliore du code")
@app_commands.describe(
    code="Le code à corriger (colle-le directement)",
    probleme="Quel est le problème ou ce que tu veux améliorer ?"
)
async def slash_corriger(interaction: discord.Interaction, code: str, probleme: str = "Trouve et corrige les bugs"):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    response = await run_in_thread(user_id, f"{probleme}\n\nCode :\n{code}")
    await send_response(interaction, response)


@bot.tree.command(name="planifier", description="📅 Crée un plan détaillé pour un projet ou une tâche")
@app_commands.describe(
    projet="Description du projet ou de la tâche",
    duree="Durée disponible (ex: '1 semaine', '3 mois')"
)
async def slash_planifier(interaction: discord.Interaction, projet: str, duree: str = "non définie"):
    await interaction.response.defer(thinking=True)
    user_id = str(interaction.user.id)
    prompt = f"Crée un plan d'action détaillé et structuré pour : {projet}. Durée : {duree}. Inclure étapes, jalons, et conseils."
    response = await run_in_thread(user_id, prompt)
    await send_response(interaction, response)


# ═══════════════════════════════════════════════════════════════
#  ℹ️ COMMANDE AIDE
# ═══════════════════════════════════════════════════════════════

@bot.tree.command(name="aide", description="ℹ️ Affiche toutes les commandes disponibles")
async def slash_aide(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Agent IA Discord — Toutes les commandes",
        description="Utilise `/` pour voir les commandes. Chaque commande a une description détaillée.",
        color=discord.Color.blurple()
    )

    embed.add_field(name="━━━ 🤖 IA Principale ━━━", value="\u200b", inline=False)
    embed.add_field(name="/ia", value="Ordre libre à l'agent IA", inline=True)
    embed.add_field(name="/generer", value="Crée une app complète", inline=True)
    embed.add_field(name="/executer", value="Génère + exécute Python", inline=True)
    embed.add_field(name="/analyser", value="Analyse un fichier", inline=True)
    embed.add_field(name="/convertir", value="Transforme du texte", inline=True)

    embed.add_field(name="━━━ 📁 Fichiers ━━━", value="\u200b", inline=False)
    embed.add_field(name="/fichiers", value="Liste le workspace", inline=True)
    embed.add_field(name="/lire", value="Lit un fichier", inline=True)
    embed.add_field(name="/ecrire", value="Crée/écrase un fichier", inline=True)
    embed.add_field(name="/supprimer", value="Supprime un fichier", inline=True)
    embed.add_field(name="/telecharger", value="Télécharge depuis URL", inline=True)

    embed.add_field(name="━━━ 🌐 Web ━━━", value="\u200b", inline=False)
    embed.add_field(name="/rechercher", value="Recherche sur le web", inline=True)
    embed.add_field(name="/scraper", value="Extrait contenu d'une page", inline=True)

    embed.add_field(name="━━━ 🖥️ Système ━━━", value="\u200b", inline=False)
    embed.add_field(name="/shell", value="Exécute une commande shell", inline=True)
    embed.add_field(name="/installer", value="Installe un package pip", inline=True)
    embed.add_field(name="/systeme", value="Infos système", inline=True)

    embed.add_field(name="━━━ 🗄️ Bases de données ━━━", value="\u200b", inline=False)
    embed.add_field(name="/airtable-lire", value="Lit une table Airtable", inline=True)
    embed.add_field(name="/airtable-ajouter", value="Ajoute dans Airtable", inline=True)
    embed.add_field(name="/sheets-lire", value="Lit une Google Sheet", inline=True)
    embed.add_field(name="/sheets-ecrire", value="Écrit dans Google Sheet", inline=True)

    embed.add_field(name="━━━ ✍️ Créatif ━━━", value="\u200b", inline=False)
    embed.add_field(name="/rediger", value="Rédige email/article/histoire", inline=True)
    embed.add_field(name="/traduire", value="Traduit dans toute langue", inline=True)
    embed.add_field(name="/resumer", value="Résume un texte long", inline=True)
    embed.add_field(name="/code", value="Génère du code", inline=True)
    embed.add_field(name="/corriger", value="Corrige/améliore du code", inline=True)
    embed.add_field(name="/planifier", value="Plan de projet détaillé", inline=True)

    embed.add_field(name="━━━ 🧠 Mémoire ━━━", value="\u200b", inline=False)
    embed.add_field(name="/memoire", value="Voir ta mémoire", inline=True)
    embed.add_field(name="/reset", value="Efface la mémoire", inline=True)

    embed.set_footer(text="💡 Tape / dans Discord pour voir toutes les commandes avec leur description")
    await interaction.response.send_message(embed=embed)


# ═══════════════════════════════════════════════════════════════
#  🔘 VUE DE CONFIRMATION (pour suppression)
# ═══════════════════════════════════════════════════════════════

class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int, filename: str):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.filename = filename

    @discord.ui.button(label="✅ Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas ta commande.", ephemeral=True)
            return
        await interaction.response.defer()
        response = await run_in_thread(str(self.user_id), f"Supprime le fichier '{self.filename}'")
        await interaction.followup.send(response, ephemeral=True)
        self.stop()

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Annulé.", ephemeral=True)
        self.stop()


# ═══════════════════════════════════════════════════════════════
#  📩 MENTION DIRECTE (sans slash)
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        content = message.content
        for mention in [f"<@{bot.user.id}>", f"<@!{bot.user.id}>"]:
            content = content.replace(mention, "").strip()
        if content:
            async with message.channel.typing():
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, run_agent, str(message.author.id), content)
            chunks = textwrap.wrap(response, MAX_LEN, replace_whitespace=False, break_long_words=True)
            if not chunks:
                chunks = [response]
            await message.reply(chunks[0], mention_author=False)
            for chunk in chunks[1:]:
                await message.channel.send(chunk)
        else:
            await message.reply("👋 Utilise `/aide` pour voir toutes mes commandes !", mention_author=False)
        return
    await bot.process_commands(message)


# ═══════════════════════════════════════════════════════════════
#  🚀 DÉMARRAGE
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
