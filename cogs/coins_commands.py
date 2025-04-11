import discord
from discord import app_commands
from discord.ext import commands
from utils.logger import setup_logger
from config import CONFIG
from services.data_manager import DataManager

logger = setup_logger('forum_commands')

class CoinsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="meschtons", description="Affiche ton nombre de Ch'tons")
    async def my_coins(self, interaction: discord.Interaction):
        """Affiche le nombre de Ch'tons de l'utilisateur"""
        # Récupérer le nombre de Ch'tons de l'utilisateur
        member_id = interaction.user.id
        data_manager = await DataManager.get_instance()
        member_data = await data_manager.get_member_data(member_id)
        chtons = member_data[3] if member_data else 0
        # Créer la réponse
        await interaction.response.send_message(
            f"Tu as **{chtons} Ch'tons** !",
            ephemeral=True
        )

    @app_commands.command(name="give", description="Transfère des Ch'tons de toi à un autre utilisateur")
    @app_commands.describe(user="L'utilisateur à qui donner des Ch'tons", amount="Le nombre de Ch'tons à donner")
    async def give_coins(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        # Différez immédiatement la réponse pour éviter l'expiration
        await interaction.response.defer(ephemeral=True)

        # Vérifier que le montant est positif
        if amount <= 0:
            await interaction.followup.send("Le montant doit être supérieur à 0.")
            return
        if user.id == interaction.user.id:
            await interaction.followup.send("Petit malin va, tu ne peux pas te donner des Ch'tons à toi-même !")
            return
        
        # Récupérer le nombre de Ch'tons de l'utilisateur
        data_manager = await DataManager.get_instance()
        receiver_data = await data_manager.get_member_data(user.id)
        giver_data = await data_manager.get_member_data(interaction.user.id)

        if int(giver_data[3]) < amount:
            await interaction.followup.send("Tu n'as pas assez de Ch'tons.")
            return
        
        receiver_data[3] = int(receiver_data[3]) + amount
        giver_data[3] = int(giver_data[3]) - amount

        await data_manager.save_member_data(user.id, receiver_data)
        await data_manager.save_member_data(interaction.user.id, giver_data)

        # Utiliser followup au lieu de response.send_message
        await interaction.followup.send(f"Tu as donné **{amount} Ch'tons** à {user.mention} !")
        await user.send(f"Tu as reçu **{amount} Ch'tons** de la part de {giver_data[1]} !")
        
async def setup(bot):
    await bot.add_cog(CoinsCommands(bot))
