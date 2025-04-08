import discord # type: ignore
from discord import app_commands, SelectOption, Embed, ui # type: ignore
from discord.ext import commands, tasks # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import datetime
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('guildeux_bot')

load_dotenv()

CONFIG = {
    "CHANNELS": {
        "PRESENTATION_GUILDEUX": 1351804801985548338,
        "PRESENTATION_HG": 1351602367522668607,
        "BISTROT": 1200334054701158400,
        "FORUM_PASSAGES": 1353744187752976486
    },
    "PLAYERS": {
        "Auto": 199975684607705088,
        "Iru": 326000214865346561,
        "Jean-Lard": 336572559518859265,
        "Krakoukas": 267423385967919104,
        "Meilleur": 291706707602833408,
        "Guiffee": 279349998901133314
    },
    "MESSAGES": {
        "QUOI_RESPONSES": {
            199975684607705088: "COUBEH",
            326000214865346561: "FEUR"
        }
    },
    "API": {
        "PASSAGES_SHEET_ID": "151apOpgLtJyVPzg60Ecu8BZgV1UKE5bKtNdtTxkKhX0",
        "MDR_SHEET_ID": "1qkWyIn_zfmPZgu1EE2S586hS_Zv4LeYS8x_9AeRDKeI",
        "API_KEY": "AIzaSyC_ZCNt66olCsWbTU8fVLJh8TBIxemgCVU",
        "CREDENTIALS_FILE": "credentials.json"
    },
    "COLORS": {
        "GUILDEUX": 0x9B59B6,  # violet
        "HG": 0xE74C3C,  # rouge
        "SUCCESS": 0x00FF00    # vert
    }
}

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

passages_data = {}

def get_sheets_service():
    """Initialise et retourne un service Google Sheets avec une simple clé API"""
    try:
        service = build('sheets', 'v4', developerKey=CONFIG["API"]["API_KEY"])
        return service.spreadsheets()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du service Google Sheets: {e}", exc_info=True)
        return None
    
def get_sheets_read_service():
    """Service pour les opérations de lecture avec clé API"""
    try:
        service = build('sheets', 'v4', developerKey=CONFIG["API"]["API_KEY"])
        return service.spreadsheets()
    except Exception as e:
        logger.error(f"Erreur d'initialisation du service de lecture: {e}", exc_info=True)
        return None

def get_sheets_write_service():
    """Service pour les opérations d'écriture avec compte de service"""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    try:
        creds = service_account.Credentials.from_service_account_file(
            CONFIG["API"]["CREDENTIALS_FILE"], scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        return service.spreadsheets()
    except Exception as e:
        logger.error(f"Erreur d'initialisation du service d'écriture: {e}", exc_info=True)
        return None

async def load_data():
    global passages_data
    try:
        sheets = get_sheets_service()
        if not sheets:
            return False

        result = sheets.values().get(
            spreadsheetId=CONFIG["API"]["PASSAGES_SHEET_ID"],
            range="A1:Z1000"  # Ajustez selon la taille de votre feuille
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.error("Aucune donnée trouvée dans la feuille Google")
            return False
            
        headers = values[0]
        data = []
        
        for row in values[1:]:
            padded_row = row + [''] * (len(headers) - len(row))
            row_dict = dict(zip(headers, padded_row))
            data.append(row_dict)
        
        passages_data = {}
        for row in data:
            boss = row.get('boss', '')
            if not boss:
                continue
            if boss not in passages_data:
                passages_data[boss] = {"icone": row.get('icone', '')}
            succes = row.get('succes', '')
            if not succes:
                continue
                
            passages_data[boss][succes] = {}
            
            passeurs = []
            if row.get('passeur1'):
                passeurs.append(row.get('passeur1'))
            if row.get('passeur2'):
                passeurs.append(row.get('passeur2'))
            if row.get('passeur3'):
                passeurs.append(row.get('passeur3'))
            
            passages_data[boss][succes]["passeurs"] = passeurs
            passages_data[boss][succes]["prix"] = [
                row.get('prix (kamas)', ''),
                row.get('prix réduc (kamas)', ''),
                row.get('prix (coins)', '')
            ]
        
        logger.info("Données chargées avec succès depuis Google Sheets")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données: {e}", exc_info=True)
        return False

async def update_members_data():
    """Met à jour les données des membres dans la feuille Google Sheets"""
    try:
        sheets = get_sheets_write_service()
        if not sheets:
            logger.error("Impossible d'initialiser le service d'écriture Google Sheets")
            return False
        
        result = sheets.values().get(
            spreadsheetId=CONFIG["API"]["MDR_SHEET_ID"],
            range="A1:Z1000"  # Ajustez selon la taille de votre feuille
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.error("Aucune donnée trouvée dans la feuille Google")
            return False
            
        headers = values[0]
        id_col = headers.index("ID Discord") if "ID Discord" in headers else None
        pseudo_col = headers.index("Pseudo sur serveur Discord") if "Pseudo sur serveur Discord" in headers else None
        role_col = headers.index("Rôle") if "Rôle" in headers else None
        
        if id_col is None or pseudo_col is None or role_col is None:
            logger.error("Colonnes requises non trouvées dans la feuille")
            return False
        
        members_data = []
        for i in range(1, len(values)): 
            if len(values[i]) > id_col:
                row_dict = {}
                for j, header in enumerate(headers):
                    if j < len(values[i]):
                        row_dict[header] = values[i][j]
                    else:
                        row_dict[header] = ""
                members_data.append(row_dict)
        
        update_rows = []
        
        target_guild = None
        for guild in bot.guilds:
            if guild.name == "Maison de retraite":  # Nom du serveur
                target_guild = guild
                break
                
        if not target_guild:
            logger.error("Guilde 'Maison de retraite' non trouvée")
            return False
        
        for i, member_info in enumerate(members_data, start=1):
            discord_id = member_info.get('ID Discord')
            
            if not discord_id or not discord_id.strip().isdigit():
                continue
                
            discord_id = int(discord_id)
            
            guild_member = target_guild.get_member(discord_id)
            if not guild_member:
                continue
            
            current_nickname = guild_member.display_name
            
            top_role = None
            for role in reversed(guild_member.roles):
                if role.name != "@everyone":
                    top_role = role.name
                    break
            
            if not top_role:
                top_role = "None"
            
            if current_nickname != member_info.get('Pseudo sur serveur Discord') or top_role != member_info.get('Rôle'):
                row_index = i + 1 
                
                row_values = [None] * len(headers)
                row_values[pseudo_col] = current_nickname
                row_values[role_col] = top_role

                update_rows.append({
                    'range': f'Sheet1!{chr(65+pseudo_col)}{row_index}:{chr(65+role_col)}{row_index}',
                    'values': [[current_nickname, top_role]]
                })
                
                logger.info(f"Mise à jour détectée pour {current_nickname} (ID: {discord_id})")
        
        if update_rows:
            body = {
                'valueInputOption': 'RAW',
                'data': update_rows
            }
            
            result = sheets.values().batchUpdate(
                spreadsheetId=CONFIG["API"]["MDR_SHEET_ID"],
                body=body
            ).execute()
            
            logger.info(f"Mise à jour réussie pour {result.get('totalUpdatedCells')} cellules")
            return True
        else:
            logger.info("Aucune mise à jour nécessaire pour les membres")
            return True
            
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des données membres: {e}", exc_info=True)
        return False

@bot.event
async def on_member_join(member):
    """Fonction déclenchée lorsqu'un nouveau membre rejoint le serveur"""
    # Vérifier que c'est le bon serveur (optionnel, si vous gérez plusieurs serveurs)
    if member.guild.name != "Maison de retraite":
        return

    # Log l'événement
    logger.info(f"Nouveau membre rejoint: {member.name}#{member.discriminator} (ID: {member.id})")
    
    try:
        # Récupérer les données existantes pour vérifier si le membre est déjà dans la liste
        sheets_service = get_sheets_write_service()
        sheet_range = "MDR!A:Z"  # Adaptez selon votre structure de feuille
        
        result = sheets_service.values().get(
            spreadsheetId=CONFIG["API"]["MDR_SHEET_ID"],
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        
        # Vérifier si l'ID Discord existe déjà dans les données
        member_exists = False
        for row in values:
            if len(row) > 0 and str(member.id) in row:
                member_exists = True
                logger.info(f"Membre {member.name} déjà dans la base de données")
                break
                
        if not member_exists:
            # Préparation des données du nouveau membre
            new_member_data = [
                str(member.id),                                  # ID Discord
                member.name,                                     # Nom Discord
                member.display_name,                             # Pseudo sur serveur Discord
                "Membre",                                        # Rôle (par défaut)
                datetime.datetime.now().strftime("%d/%m/%Y")     # Date d'arrivée
            ]
            
            # Déterminer la prochaine ligne libre
            next_row = len(values) + 1
            
            # Ajouter à la feuille
            update_range = f"MDR!A{next_row}:E{next_row}"  # Adaptez les colonnes selon votre structure
            
            sheets_service.values().update(
                spreadsheetId=CONFIG["API"]["MDR_SHEET_ID"],
                range=update_range,
                valueInputOption="RAW",
                body={
                    "values": [new_member_data]
                }
            ).execute()
            
            logger.info(f"Membre {member.name} ajouté à la base de données à la ligne {next_row}")
            
            # Message de bienvenue dans un canal spécifique (optionnel)
            welcome_channel = member.guild.get_channel(CONFIG["CHANNELS"]["BISTROT"])
            if welcome_channel:
                await welcome_channel.send(f"Bienvenue {member.mention} ! Ton ID a été ajouté à notre liste de membres.")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du nouveau membre {member.name} (ID: {member.id}) : {e}", exc_info=True)

@tasks.loop(hours=1)
async def refresh_data():
    await load_data()
    await update_members_data()

@refresh_data.before_loop
async def before_refresh():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user}')

    success = await load_data()
    if success:
        refresh_data.start()

    success_members = await update_members_data()
    if success_members:
        logger.info("Mise à jour des données membres réussie")

    try:
        synced = await bot.tree.sync()
        logger.info(f'Synchronisation de {len(synced)} commande(s)')
    except Exception as e:
        logger.error(f'Erreur lors de la synchronisation des commandes: {e}', exc_info=True)

@bot.tree.command(name="réseau", description="Récupérer l'excel de ce fou de Guiffee")
async def excel_get(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"<https://docs.google.com/spreadsheets/d/17YBcPa5HI9ePlEU-W9K2BSKtSc2rRjBzKOFk35n6rLU/edit?usp=sharing>", 
        ephemeral=True
    )

@bot.tree.command(name="fermer", description="Ferme le thread en cours")
async def close_thread(interaction: discord.Interaction):
    # Vérifier que la commande est utilisée dans un thread
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message(
            "Cette commande ne peut être utilisée que dans un thread.",
            ephemeral=True
        )
        return
    
    # Vérifier les permissions (seul le créateur du thread ou un modérateur peut le fermer)
    thread = interaction.channel
    member = interaction.user
    
    # Vérifier si l'utilisateur est le créateur du thread, un modérateur ou un admin
    is_creator = thread.owner_id == member.id if thread.owner_id else False
    is_passeur = member.id in CONFIG["PLAYERS"].values()
    
    has_permissions = (
        member.guild_permissions.manage_threads or 
        member.guild_permissions.administrator or
        is_passeur
    )
    
    if not (is_creator or has_permissions):
        await interaction.response.send_message(
            "Vous n'avez pas la permission de fermer ce thread.",
            ephemeral=True
        )
        return
    
    try:
        # Envoyer un message de confirmation
        await interaction.response.send_message(
            "🔒 Ce thread va être archivé dans quelques secondes...",
            ephemeral=False
        )
        
        # Envoyer un message de conclusion dans le thread
        await thread.send(
            f"🔒 **Thread fermé par {member.display_name}**\n"
            "Ce sujet a été archivé et ne peut plus recevoir de nouveaux messages."
        )
        
        # Archiver le thread
        await thread.delete()
        logger.info(f"Thread {thread.name} (ID: {thread.id}) fermé par {member.display_name}")
        
    except discord.Forbidden:
        await interaction.followup.send(
            "Je n'ai pas la permission d'archiver ce thread.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Erreur lors de la fermeture du thread: {e}", exc_info=True)
        await interaction.followup.send(
            f"Une erreur s'est produite lors de la fermeture du thread: {str(e)}",
            ephemeral=True
        )

async def boss_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Fonction qui suggère des boss en fonction de ce que l'utilisateur tape"""
    choices = []
    
    matching_bosses = [boss for boss in passages_data.keys() if current.lower() in boss.lower()]
    
    for boss in matching_bosses[:5]:  # Limite à 5 choix
        display_name = f"{passages_data[boss]['icone']} {boss}"
        choices.append(app_commands.Choice(name=display_name, value=boss))
    
    return choices

@bot.tree.command(name="passage", description="Rechercher les passages disponibles pour un boss")
@app_commands.describe(boss="Nom du boss à rechercher")
@app_commands.autocomplete(boss=boss_autocomplete)
async def boss_get(interaction: discord.Interaction, boss: str):
    await search_boss(interaction, boss)

@bot.command(name="passage")
async def boss_command(ctx, *, boss_name=None):
    if not boss_name:
        await ctx.reply("Veuillez spécifier le nom d'un boss. Exemple: `!passage Wa Wabbit`")
        return
    
    await search_boss(ctx, boss_name)

async def search_boss(ctx_or_interaction, boss_name):
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    # Recherche du boss (insensible à la casse)
    found_boss = None
    for boss in passages_data.keys():
        if boss.lower() == boss_name.lower():
            found_boss = boss
            break
    
    if not found_boss:
        message = f'Boss "{boss_name}" non trouvé dans la base de données.'
        if is_interaction:
            await ctx_or_interaction.response.send_message(message, ephemeral=True)
        else:
            await ctx_or_interaction.reply(message, ephemeral=True)
        return
    
    view = BossSuccessView(found_boss)
    boss_data = passages_data[found_boss]
    boss_icon = boss_data["icone"]
    
    # Création de la liste des succès
    success_list = []
    for item in boss_data:
        if item != "icone":
            success_list.append({item: boss_data[item]}) 

    if not success_list:
        msg = f"Aucun succès trouvé pour {boss_icon} **{found_boss}**."
        if is_interaction:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.reply(msg)
        return
    
    first_success = success_list[0]
    embed = create_success_embed(found_boss, first_success)
    
    if is_interaction:
        await ctx_or_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx_or_interaction.reply(embed=embed, view=view, ephemeral=True)


def create_success_embed(boss_name, success_data):
    """Crée un embed pour afficher les informations d'un succès"""
    boss_icon = passages_data[boss_name]['icone']
    success_name, details = list(success_data.items())[0]  # Méthode plus claire
    
    embed = discord.Embed(
        title=f"{boss_icon} {boss_name} - {success_name}",
        description="Aucune description disponible",
        color=CONFIG["COLORS"]["SUCCESS"]
    )
    
    # Format de prix plus lisible
    prices = details['prix']
    price_text = f"💰 **{prices[0]} kamas**"
    if prices[2]:  # Si prix en coins existe
        price_text += f" ou **{prices[2]} coins**"
    if prices[1] and prices[1] != prices[0]:  # Si prix réduit existe et diffère
        price_text += f"\n💲 Prix réduit: **{prices[1]} kamas**"
    
    embed.add_field(name="Prix du passage", value=price_text, inline=False)
    
    # Affichons aussi les passeurs
    if details['passeurs']:
        passeurs_text = ", ".join([f"<@{CONFIG['PLAYERS'][p]}>" for p in details['passeurs'] if p in CONFIG['PLAYERS']])
        embed.add_field(name="Passeurs", value=passeurs_text or "Aucun passeur spécifié", inline=False)
    
    embed.set_footer(text="Utilisez le menu déroulant pour voir les autres succès du boss")
    
    return embed


class SuccessSelect(ui.Select):
    """Menu déroulant pour les succès d'un boss"""
    def __init__(self, boss_name):
        self.boss_name = boss_name
        boss_data = passages_data[boss_name]
        
        # Construction de la liste des succès
        success_list = []
        for item in boss_data:
            if item != "icone":
                success_list.append({item: boss_data[item]}) 
        
        options = []
        for success in success_list:
            success_name = list(success.keys())[0]
            emoji = "🏆"  # Emoji par défaut
            
            # Limite la taille de la description
            options.append(discord.SelectOption(
                label=success_name[:100],  # Limite à 100 caractères
                description="Sélectionner ce succès",
                emoji=emoji,
                value=str(success_list.index(success))
            ))
            
        super().__init__(
            placeholder="Sélectionnez un succès...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Récupérer l'index du succès sélectionné
            selected_index = int(self.values[0])
            boss_data = passages_data[self.boss_name]
            
            # Construction de la liste des succès
            success_list = []
            for item in boss_data:
                if item != "icone":
                    success_list.append({item: boss_data[item]})
            
            if selected_index < len(success_list):
                selected_success = success_list[selected_index]
                embed = create_success_embed(self.boss_name, selected_success)
                
                # Mettre à jour le message avec le nouvel embed
                await interaction.response.edit_message(embed=embed, view=self.view)
        except Exception as e:
            logger.error(f"Erreur dans le callback du menu succès: {e}", exc_info=True)
            await interaction.response.send_message("Une erreur est survenue lors de la sélection du succès.", ephemeral=True)


class CreatePostButton(ui.Button):
    """Bouton pour créer un post dans le forum"""
    def __init__(self, boss_name):
        self.boss_name = boss_name
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Créer une demande de passage",
            emoji="📝"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Récupérer le channel du forum
            forum_channel = interaction.client.get_channel(CONFIG["CHANNELS"]["FORUM_PASSAGES"])
            if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
                await interaction.response.send_message("Le forum n'a pas été trouvé. Contactez un administrateur.", ephemeral=True)
                return
            
            # Extraction des informations de l'embed
            current_embed = interaction.message.embeds[0]
            title_parts = current_embed.title.split(' - ')
            if len(title_parts) < 2:
                await interaction.response.send_message("Impossible de déterminer le succès demandé.", ephemeral=True)
                return
                
            success = title_parts[-1]
            
            if success not in passages_data[self.boss_name]:
                await interaction.response.send_message("Erreur: Succès non trouvé dans les données.", ephemeral=True)
                return
                
            success_data = passages_data[self.boss_name][success]
            
            # Information utilisateur
            user = interaction.user
            member = interaction.guild.get_member(user.id)
            pseudo = member.nick if member and member.nick else user.name
            
            # Titre du post formaté
            post_title = f"[Demande] {self.boss_name} - {success} ({pseudo})"
            
            # Contenu formaté riche
            content = (
                f"# Demande de passage\n\n"
                f"**Demandeur:** {interaction.user.mention}\n"
                f"**Boss:** {self.boss_name}\n"
                f"**Succès:** {success}\n\n"
                f"## Prix\n"
                f"**Prix standard:** {success_data['prix'][0]} Kamas\n"
            )
            
            if success_data['prix'][2]:
                content += f"**Alternative:** {success_data['prix'][2]} coins\n\n"
            else:
                content += "\n"
                
            content += "## Passeurs\n"
            
            # Ajout des mentions de passeurs
            for passeur in success_data['passeurs']:
                if passeur in CONFIG["PLAYERS"]:
                    content += f"<@{CONFIG['PLAYERS'][passeur]}> "
            
            content += "\n\n*Merci de préciser vos disponibilités ci-dessous.*"
            
            # Création du thread avec tags si disponibles
            thread_with_message = await forum_channel.create_thread(
                name=post_title,
                content=content
            )
            
            thread = thread_with_message.thread
            
            await interaction.response.send_message(
                f"✅ Demande créée avec succès!\n"
                f"[Cliquez ici pour accéder à votre demande](https://discord.com/channels/{interaction.guild.id}/{thread.id})",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas la permission de créer un post dans le forum.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création du post: {e}", exc_info=True)
            await interaction.response.send_message(
                f"Une erreur s'est produite: {str(e)}",
                ephemeral=True
            )


class BossSuccessView(ui.View):
    """Vue combinant le menu déroulant et le bouton"""
    def __init__(self, boss_name):
        super().__init__(timeout=300)  # 5 minutes de timeout
        
        # Ajouter le menu déroulant
        self.boss_name = boss_name
        self.add_item(SuccessSelect(boss_name))
        
        # Ajouter le bouton pour créer un post
        self.add_item(CreatePostButton(boss_name))
    
    async def on_timeout(self):
        # Désactiver les composants quand le timeout est atteint
        for item in self.children:
            item.disabled = True
        
        # On ne peut pas mettre à jour le message ici car nous n'avons pas accès au message
        # Cette partie pourrait être améliorée en stockant une référence au message

# Démarrer le bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
