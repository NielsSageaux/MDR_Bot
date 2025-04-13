import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import asyncio
from config import CONFIG
from utils.logger import setup_logger
from services.data_manager import DataManager

logger = setup_logger('passage_commands')

async def create_success_embed(boss_name, success_name, client_id):
    passages_data = DataManager.get_passages_data()
    #if passages_data[boss_name]['ICONE'] != 'placeholder':
    #    boss_name = passages_data[boss_name]['ICONE'] + " " + boss_name
    
    success_data = passages_data[boss_name]['SUCCESS'][success_name]
    
    embed = discord.Embed(
        title=f"**__{boss_name} - {success_name}__**",
        color=CONFIG["COLORS"]["SUCCESS"]
    )
    
    dataManager = await DataManager.get_instance()
    client_data = await dataManager.get_member_data(client_id)
    reduc = 1
    if client_data[2] == "Nouveau (PDE)":
        reduc = CONFIG["REDUCS"]["NOUVEAU"]
    elif client_data[2] == "Membre de guilde":
        reduc = CONFIG["REDUCS"]["NORMAL"]
    elif client_data[2] == "Resident premium" or client_data[2] == "Hauts gradés" or client_data[2] == "Directeur" or client_data[2] == "vieux des vieux":
        reduc = CONFIG["REDUCS"]["PREMIUM"] 

    if success_data['prix (kamas)'] == 'flemme':
        embed.add_field(name="Désolé !", value="Ce succès n'est pas effectué par nos passeurs.", inline=False)
    else:
        if 'm' in success_data['prix (kamas)']:
            kamas = float(success_data['prix (kamas)'].replace('m', '.')) * reduc * 100000
        elif 'k' in success_data['prix (kamas)']:
            kamas = float(success_data['prix (kamas)'].replace('k', '.')) * reduc * 1000
        kamas = f"{int(kamas):,}".replace(",", " ")
        embed.add_field(name="**Prix du passage :**", value=f"**{int(int(success_data['prix (coins)']) * reduc)} Ch'tons {CONFIG['EMOTES']['CHTON']}**", inline=True)
        embed.add_field(name="**Prix alternatif :**", value=f"**{kamas} Kamas {CONFIG['EMOTES']['KAMAS']}**", inline=True)

    embed.set_footer(text=
                     "Utilisez le menu déroulant pour voir les autres succès du boss ou le bouton pour créer une demande de passage sur ce succès. Reformulez une commande /passage pour voir les succès proposés pour d'autres boss.")

    view = discord.ui.View()
    view.add_item(SuccessSelect(boss_name))
    view.add_item(CreateThreadButton(boss_name, success_name))

    return embed

class CreateThreadButton(ui.Button):
    """Bouton pour créer un thread"""
    def __init__(self, boss_name, success_name):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Créer une demande de passage",
            emoji="📝"
        )
        self.boss_name = boss_name
        self.success_name = success_name

    async def callback(self, interaction: discord.Interaction):
        try:
            # Récupérer le channel du forum
            forum_channel = interaction.client.get_channel(CONFIG["CHANNELS"]["FORUM_PASSAGES"])
            if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
                await interaction.response.send_message("Le forum n'a pas été trouvé. Contactez un administrateur.", ephemeral=True)
                return
                
            # Récupérer les données du boss et du succès
            passages_data = DataManager.get_passages_data()
            success_data = passages_data[self.boss_name]['SUCCESS'][self.success_name]
            
            # Information utilisateur
            user = interaction.user
            member = interaction.guild.get_member(user.id)
            pseudo = member.nick if member and member.nick else user.name
            
            # Titre du post formaté
            post_title = f"[Demande] {self.boss_name} - {self.success_name} ({pseudo})"
            
            # Contenu formaté riche
            content = (
                f"# Demande de passage\n\n"
                f"**Demandeur:** {interaction.user.mention}\n"
                f"**Boss:** {self.boss_name}\n"
                f"**Succès:** {self.success_name}\n\n"
                f"## Prix\n"
                f"**Prix standard:** {success_data['prix (kamas)']} Kamas\n" # A changer dans le futur pour les ch'tons
            )
            
            if success_data['prix (coins)']:
                content += f"**Alternative:** {success_data['prix (coins)']} Ch'tons\n\n"
            else:
                content += "\n"
                
            content += "## Passeurs\n"
            
            # Ajout des mentions de passeurs
            passeurs_list = success_data['passeurs'].split(", ")
            for passeur in passeurs_list:
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

class SuccessSelect(ui.Select):
    """Menu déroulant pour les succès d'un boss"""
    boss_name = None

    def __init__(self, boss_name):
        self.boss_name = boss_name
        boss_data_success = DataManager.get_passages_data()[boss_name]['SUCCESS']
        
        success_list = list(boss_data_success.keys())
        
        options = []
        for success in success_list:
            emoji = "🏆"  # Emoji par défaut
            
            # Limite la taille de la description
            options.append(discord.SelectOption(
                label=success[:100],  # Limite à 100 caractères
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
            boss_data_success = DataManager.get_passages_data()[self.boss_name]['SUCCESS']
        
            success_list = list(boss_data_success.keys())
            
            selected_success = success_list[selected_index]
            embed = await create_success_embed(self.boss_name, selected_success, interaction.user.id) 
            
            await interaction.response.edit_message(embed=embed, view=self.view)

        except Exception as e:
            logger.error(f"Erreur dans le callback du menu succès: {e}", exc_info=True)
            await interaction.response.send_message("Une erreur est survenue lors de la sélection du succès.", ephemeral=True)

class PassageCommands(commands.Cog):
    """Commandes pour les passages de boss"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_ready = asyncio.Event()
        self.boss_list = []
        self.passages_data = {}
        self.bot.loop.create_task(self.wait_for_data())
    
    async def wait_for_data(self):
        """Attend que les données soient disponibles"""
        await self.bot.wait_until_ready()
        
        # Attendre que les données soient prêtes
        while True:
            try:
                data = DataManager.get_passages_data()
                if data:
                    self.data_ready.set()
                    self.boss_list = DataManager.get_boss_list()
                    self.passages_data = DataManager.get_passages_data()
                    logger.info(f"Données de passage prêtes: {len(data)} boss trouvés")
                    break
            except:
                pass
                
            await asyncio.sleep(1)  # Vérifier chaque seconde

    async def boss_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Fonction qui suggère des boss en fonction de ce que l'utilisateur tape"""
        choices = []
        
        matching_bosses = [boss for boss in self.boss_list if current.lower() in boss.lower()]
        
        for boss in matching_bosses[:5]:  # Limite à 5 choix
            choices.append(app_commands.Choice(name=boss, value=boss))
        
        return choices
    
    @app_commands.command(name="passage", description="Affiche les informations sur un passage de boss")
    @app_commands.describe(boss="Nom du boss")
    @app_commands.autocomplete(boss=boss_autocomplete)
    async def passage_command(self, interaction: discord.Interaction, boss: str):
        """Commande pour afficher les informations sur un passage de boss"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Vérifier si on attend encore les données
            if boss == "loading" or not self.data_ready.is_set():
                return await interaction.followup.send("Les données sont encore en cours de chargement. Veuillez réessayer.", ephemeral=True)
            
            # Récupérer les données du boss
            passages_data = DataManager.get_passages_data()
            if boss not in passages_data or 'SUCCESS' not in passages_data[boss]:
                return await interaction.followup.send(f"Boss **{boss}** non trouvé ou sans succès.", ephemeral=True)
            
            # Premier succès par défaut
            first_success = next(iter(passages_data[boss]['SUCCESS'].keys()))
            
            # Créer l'embed et la vue
            embed = await create_success_embed(boss, first_success, interaction.user.id)
            view = discord.ui.View()
            view.add_item(SuccessSelect(boss))
            view.add_item(CreateThreadButton(boss, first_success))
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la commande passage: {e}", exc_info=True)
            await interaction.followup.send("Une erreur s'est produite lors de l'exécution de la commande.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PassageCommands(bot))
    logger.info("PassageCommands cog chargé")