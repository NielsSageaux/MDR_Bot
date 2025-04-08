import discord # type: ignore
from discord import app_commands, SelectOption, Embed, ui # type: ignore
from discord.ext import commands, tasks # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import datetime
import requests # type: ignore
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('guildeux_bot')

load_dotenv()

# Configuration centralisée
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
        "SHEETDB_URL": "https://sheetdb.io/api/v1/fmngpa95dqtn9"
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

# Variable globale pour stocker les données
passages_data = {}

async def load_data():
    global passages_data
    try: 
        response = requests.get(CONFIG["API"]["SHEETDB_URL"])
        
        if response.status_code == 200:
            data = response.json()
            passages_data = {}
            for row in data:
                boss = row['boss']
                if boss not in passages_data:
                    passages_data[boss] = {"icone": row['icone']}
                
                succes = row['succes']
                passages_data[boss][succes] = {}
                
                # Collecte des passeurs non vides
                passeurs = []
                if row['passeur1']:
                    passeurs.append(row['passeur1'])
                if row['passeur2']:
                    passeurs.append(row['passeur2'])
                if row['passeur3']:
                    passeurs.append(row['passeur3'])
                
                passages_data[boss][succes]["passeurs"] = passeurs
                passages_data[boss][succes]["prix"] = [
                    row['prix (kamas)'],
                    row['prix réduc (kamas)'],
                    row['prix (coins)']
                ]
            
            logger.info("Données chargées avec succès depuis SheetDB")
            return True
        else:
            logger.error(f"Erreur lors de la requête SheetDB: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données: {e}", exc_info=True)
        return False

@tasks.loop(hours=24)
async def refresh_data():
    await load_data()

@refresh_data.before_loop
async def before_refresh():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user}')

    success = await load_data()
    if success:
        refresh_data.start()

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


def limiter_mots(texte, limite=100):
    """Limite un texte à un certain nombre de mots"""
    mots = texte.split()
    if len(mots) <= limite:
        return texte
    else:
        return ' '.join(mots[:limite]) + '...'


async def handle_presentation(message, channel_id):
    """Fonction séparée pour gérer les présentations"""
    destination_channel = bot.get_channel(CONFIG["CHANNELS"]["BISTROT"])
    if not destination_channel:
        logger.warning(f"Canal de destination {CONFIG['CHANNELS']['BISTROT']} non trouvé")
        return
    
    content_limited = limiter_mots(message.content, 100)
    
    if channel_id == CONFIG["CHANNELS"]["PRESENTATION_GUILDEUX"]:
        titre = ":rotating_light: Nouvelle Présentation de Guildeux !!! :rotating_light:"
        color = CONFIG["COLORS"]["GUILDEUX"]
    else:
        titre = ":rotating_light: Nouvelle Présentation de Haut Gradé !!! :rotating_light:" 
        color = CONFIG["COLORS"]["HG"]
    
    embed = discord.Embed(
        title=titre,
        description=content_limited,
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url
    )
    
    embed.add_field(
        name="Accéder à la présentation complète : ",
        value=f"[#{message.channel.name}]({message.jump_url})",
        inline=False
    )
    
    # Traitement des images
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image'):
                embed.set_image(url=attachment.url)
                break
    
    await destination_channel.send(embed=embed)
    logger.info(f"Embed créé pour la présentation de {message.author.display_name}")


@bot.event
async def on_message(message):
    # Ignorer les messages du bot
    if message.author == bot.user:
        return
    
    # Gestion des réponses "quoi"
    if message.author.id in CONFIG["MESSAGES"]["QUOI_RESPONSES"] and "quoi" in message.content.lower():
        await message.reply(CONFIG["MESSAGES"]["QUOI_RESPONSES"][message.author.id], mention_author=False)
    
    # Gestion des présentations
    channel_id = message.channel.id
    if channel_id in [CONFIG["CHANNELS"]["PRESENTATION_GUILDEUX"], CONFIG["CHANNELS"]["PRESENTATION_HG"]]:
        await handle_presentation(message, channel_id)
    
    # Traite les commandes
    await bot.process_commands(message)


# Démarrer le bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
