import discord
from discord.ext import commands
from discord import app_commands
import platform
import psutil
import datetime
from utils.logger import setup_logger
from config import CONFIG

logger = setup_logger('stats_command')

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.utcnow()

    @app_commands.command(name="stats", description="Affiche des statistiques sur le bot")
    async def stats(self, interaction: discord.Interaction):
        """Affiche des informations et statistiques sur le bot"""
        
        # Calcul du temps d'exécution
        uptime = datetime.datetime.utcnow() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # supprimer les microsecondes
        
        # Récupération des informations système
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.Process().memory_info().rss / 1024**2  # En MB
        
        # Création de l'embed
        embed = discord.Embed(
            title="📊 Statistiques du Bot",
            color=CONFIG.get("COLORS.GUILDEUX")
        )
        
        # Informations générales
        embed.add_field(name="Nom du Bot", value=self.bot.user.name, inline=True)
        embed.add_field(name="ID du Bot", value=self.bot.user.id, inline=True)
        embed.add_field(name="Créé par", value="Jean-Lard", inline=True)
        
        # Informations techniques
        embed.add_field(name="Version Discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Version Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Plateforme", value=platform.system(), inline=True)
        
        # Statistiques d'utilisation
        embed.add_field(name="Utilisation CPU", value=f"{cpu_usage:.1f}%", inline=True)
        embed.add_field(name="Utilisation Mémoire", value=f"{memory_usage:.1f} MB", inline=True)
        embed.add_field(name="Temps de fonctionnement", value=uptime_str, inline=True)
        
        # Statistiques serveur
        embed.add_field(name="Serveurs", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Utilisateurs", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="Commandes", value=len(self.bot.commands) + len(self.bot.tree.get_commands()), inline=True)
        
        # Afficher les dernières commandes (à implémenter)
        
        embed.set_footer(text=f"Bot démarré le {self.start_time.strftime('%Y-%m-%d à %H:%M:%S')} UTC")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
