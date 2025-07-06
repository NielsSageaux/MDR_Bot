import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
from config import CONFIG
from utils.logger import setup_logger
from services.data_manager import DataManager

logger = setup_logger('passage_commands')

class PassageView(discord.ui.View):
    """Vue unifiée pour gérer les passages"""
    
    def __init__(self, boss_name, current_success, user_id):
        super().__init__(timeout=300)
        self.boss_name = boss_name
        self.current_success = current_success
        self.user_id = user_id
        
        # Ajouter les composants
        self._add_components()
    
    def _add_components(self):
        """Ajoute les composants à la vue"""
        # Menu déroulant des succès
        boss_data = DataManager.get_passages_data()[self.boss_name]['SUCCESS']
        success_list = list(boss_data.keys())
        
        options = [
            discord.SelectOption(
                label=success[:100],
                description="Sélectionner ce succès",
                emoji="🏆",
                value=str(i)
            )
            for i, success in enumerate(success_list)
        ]
        
        select = ui.Select(
            placeholder="Sélectionnez un succès...",
            options=options
        )
        select.callback = self._success_callback
        
        # Bouton de création de thread
        button = ui.Button(
            style=discord.ButtonStyle.primary,
            label="Créer une demande de passage",
            emoji="📝"
        )
        button.callback = self._thread_callback
        
        self.add_item(select)
        self.add_item(button)
    
    async def _success_callback(self, interaction: discord.Interaction):
        """Callback pour le menu déroulant"""
        try:
            selected_index = int(interaction.data['values'][0])
            success_list = list(DataManager.get_passages_data()[self.boss_name]['SUCCESS'].keys())
            self.current_success = success_list[selected_index]
            
            embed = await self._create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Erreur callback succès: {e}")
            await interaction.response.send_message("Erreur lors de la sélection.", ephemeral=True)
    
    async def _thread_callback(self, interaction: discord.Interaction):
        """Callback pour le bouton de création de thread"""
        try:
            forum_channel = interaction.client.get_channel(CONFIG["CHANNELS"]["FORUM_PASSAGES"])
            if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
                await interaction.response.send_message("Forum non trouvé.", ephemeral=True)
                return
            
            # Récupérer les données
            passages_data = DataManager.get_passages_data()
            success_data = passages_data[self.boss_name]['SUCCESS'][self.current_success]
            
            # Calculer le prix
            dataManager = await DataManager.get_instance()
            client_data = await dataManager.get_member_data(interaction.user.id)
            reduc = self._get_reduction(client_data[2])
            
            if success_data['prix (kamas)'] == 'flemme':
                await interaction.response.send_message("Ce succès n'est pas effectué par nos passeurs.", ephemeral=True)
                return
            
            # Créer le thread
            thread_title = f"{self.boss_name} - {self.current_success} pour {interaction.user.display_name}"
            
            content = f"**Boss :** {self.boss_name}\n**Succès :** {self.current_success}\n**Demandeur :** {interaction.user.mention}\n\n"
            
            if success_data['prix (kamas)'] == 'free':
                content += "**Prix :** Gratuit !"
            else:
                kamas_str = success_data['prix (kamas)']
                if 'm' in kamas_str:
                    kamas = int(float(kamas_str.replace('m', '.')) * reduc * 1000000)
                elif 'k' in kamas_str:
                    kamas = int(float(kamas_str.replace('k', '.')) * reduc * 1000)
                
                kamas_formatted = f"{kamas:,}".replace(",", " ")
                coins = int(int(success_data['prix (coins)']) * reduc)
                content += "**Prix :**\n"
                content += f"Prix standard : **{kamas_formatted} Kamas {CONFIG['EMOTES']['KAMAS']}**\n"
                content += f"Prix alternatif: **{coins} Ch'tons {CONFIG['EMOTES']['CHTON']}**\n\n"

            content += "**Passeur(s) :**\n"
            passeurs_list = success_data['passeurs'].split(", ")
            for passeur in passeurs_list:
                content += f"{discord.utils.get(interaction.guild.members, display_name=passeur).mention} "
            content += "\n\n*Merci de préciser vos disponibilités ci-dessous.*"
            
            thread = await forum_channel.create_thread( 
                name=thread_title[:100],
                content=content
            )
            
            await interaction.response.send_message(f"✅ Demande créée avec succès ! Elle accessible ici : {thread.thread.jump_url}", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erreur création thread: {e}")
            await interaction.response.send_message("Erreur lors de la création du thread.", ephemeral=True)
    
    async def _create_embed(self):
        """Crée l'embed pour le succès actuel"""
        passages_data = DataManager.get_passages_data()
        success_data = passages_data[self.boss_name]['SUCCESS'][self.current_success]
        
        embed = discord.Embed(
            title=f"**__{self.boss_name} - {self.current_success}__**",
            color=CONFIG["COLORS"]["SUCCESS"]
        )
        
        # Calculer les prix
        dataManager = await DataManager.get_instance()
        client_data = await dataManager.get_member_data(self.user_id)
        reduc = self._get_reduction(client_data[2])
        
        if success_data['prix (kamas)'] == 'flemme':
            embed.add_field(name="Désolé !", value="Ce succès n'est pas effectué par nos passeurs.", inline=False)
        elif success_data['prix (kamas)'] == 'free':
            embed.add_field(name="**Prix du passage :**", value="**Gratuit !**", inline=True)
        else:
            # Calculer les kamas
            kamas_str = success_data['prix (kamas)']
            if 'm' in kamas_str:
                kamas = int(float(kamas_str.replace('m', '.')) * reduc * 1000000)
            elif 'k' in kamas_str:
                kamas = int(float(kamas_str.replace('k', '.')) * reduc * 1000)
            
            kamas_formatted = f"{kamas:,}".replace(",", " ")
            coins = int(int(success_data['prix (coins)']) * reduc)
            
            embed.add_field(name="**Prix du passage :**", value=f"**{coins} Ch'tons {CONFIG['EMOTES']['CHTON']}**", inline=True)
            embed.add_field(name="**Prix alternatif :**", value=f"**{kamas_formatted} Kamas {CONFIG['EMOTES']['KAMAS']}**", inline=True)

        embed.set_footer(text="Utilisez le menu pour changer de succès ou le bouton pour créer une demande. Reformulez une commande /passage pour voir les succès proposés pour d'autres boss.")
        
        return embed
    
    def _get_reduction(self, role):
        """Calcule la réduction selon le rôle"""
        if role == "Jeune Retraité":
            return CONFIG["REDUCS"]["NOUVEAU"]
        elif role == "Retraité":
            return CONFIG["REDUCS"]["NORMAL"]
        elif role in ["Retraité Premium", "Aides Soignants", "Médecin de Garde", "vieux des vieux"]:
            return CONFIG["REDUCS"]["PREMIUM"]
        return 1


class PassageCommands(commands.Cog):
    """Commandes pour les passages de boss"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_ready = asyncio.Event()
        self.boss_list = []
        
        # Charger les données
        self.bot.loop.create_task(self._load_data())
    
    async def _load_data(self):
        """Charge les données des boss"""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                data = DataManager.get_passages_data()
                if data:
                    self.boss_list = DataManager.get_boss_list()
                    self.data_ready.set()
                    logger.info(f"Données chargées: {len(data)} boss")
                    break
            except:
                pass
            await asyncio.sleep(1)

    async def boss_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplétion pour les boss"""
        matching_bosses = [boss for boss in self.boss_list if current.lower() in boss.lower()]
        return [app_commands.Choice(name=boss, value=boss) for boss in matching_bosses[:5]]
    
    @app_commands.command(name="passage", description="Affiche les informations sur un passage de boss")
    @app_commands.describe(boss="Nom du boss")
    @app_commands.autocomplete(boss=boss_autocomplete)
    async def passage_command(self, interaction: discord.Interaction, boss: str):
        """Commande principale pour les passages"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if not self.data_ready.is_set():
                return await interaction.followup.send("Données en cours de chargement...", ephemeral=True)
            
            passages_data = DataManager.get_passages_data()
            if boss not in passages_data or 'SUCCESS' not in passages_data[boss]:
                return await interaction.followup.send(f"Boss **{boss}** non trouvé.", ephemeral=True)
            
            # Premier succès par défaut
            first_success = next(iter(passages_data[boss]['SUCCESS'].keys()))
            
            # Créer la vue et l'embed
            view = PassageView(boss, first_success, interaction.user.id)
            embed = await view._create_embed()
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erreur commande passage: {e}")
            await interaction.followup.send("Une erreur s'est produite.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PassageCommands(bot))
    logger.info("PassageCommands cog chargé")
