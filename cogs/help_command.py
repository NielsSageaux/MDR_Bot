import discord
from discord.ext import commands
from discord import app_commands
from utils.logger import setup_logger
from config import CONFIG

logger = setup_logger('help_command')

class HelpCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command('help')  # Supprimer la commande d'aide par défaut
        
    @commands.command(name="help")
    async def help_command(self, ctx, command_name=None):
        """Affiche l'aide pour les commandes disponibles"""
        
        if command_name:
            # Aide pour une commande spécifique
            command = self.bot.get_command(command_name)
            if command:
                embed = discord.Embed(
                    title=f"Aide pour la commande `{command.name}`",
                    description=command.help or "Aucune description disponible",
                    color=CONFIG.get("COLORS.GUILDEUX")
                )
                
                # Ajouter les aliases si présents
                if command.aliases:
                    embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
                
                # Ajouter la syntaxe si disponible
                usage = f"{ctx.prefix}{command.name}"
                if command.signature:
                    usage += f" {command.signature}"
                embed.add_field(name="Utilisation", value=f"`{usage}`", inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"La commande `{command_name}` n'existe pas.")
        else:
            # Liste de toutes les commandes
            embed = discord.Embed(
                title="Liste des commandes disponibles",
                description=(
                    f"Utilisez `{ctx.prefix}help <commande>` pour obtenir plus d'informations "
                    f"sur une commande spécifique."
                ),
                color=CONFIG.get("COLORS.GUILDEUX")
            )
            
            # Grouper les commandes par cog
            cogs_dict = {}
            for command in self.bot.commands:
                if command.hidden:
                    continue
                
                cog_name = command.cog_name or "Sans catégorie"
                if cog_name not in cogs_dict:
                    cogs_dict[cog_name] = []
                
                cogs_dict[cog_name].append(command)
            
            # Ajouter les commandes par cog
            for cog_name, commands_list in sorted(cogs_dict.items()):
                commands_text = ", ".join(f"`{cmd.name}`" for cmd in sorted(commands_list, key=lambda x: x.name))
                embed.add_field(name=cog_name, value=commands_text, inline=False)
            
            # Ajouter les commandes slash
            slash_commands = []
            for command in self.bot.tree.get_commands():
                slash_commands.append(f"`/{command.name}`")
            
            if slash_commands:
                embed.add_field(name="Commandes Slash", value=", ".join(sorted(slash_commands)), inline=False)
            
            await ctx.send(embed=embed)
    
    @app_commands.command(name="help", description="Affiche l'aide pour les commandes disponibles")
    async def help_slash(self, interaction: discord.Interaction, commande: str = None):
        """Version slash de la commande d'aide"""
        
        if commande:
            command = self.bot.get_command(commande)
            if command:
                embed = discord.Embed(
                    title=f"Aide pour la commande `{command.name}`",
                    description=command.help or "Aucune description disponible",
                    color=CONFIG.get("COLORS.GUILDEUX")
                )
                
                # Ajouter les aliases si présents
                if command.aliases:
                    embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
                
                # Ajouter la syntaxe si disponible
                usage = f"!{command.name}"
                if command.signature:
                    usage += f" {command.signature}"
                embed.add_field(name="Utilisation", value=f"`{usage}`", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Vérifier les commandes slash
                slash_command = None
                for cmd in self.bot.tree.get_commands():
                    if cmd.name == commande:
                        slash_command = cmd
                        break
                
                if slash_command:
                    embed = discord.Embed(
                        title=f"Aide pour la commande `/{slash_command.name}`",
                        description=slash_command.description or "Aucune description disponible",
                        color=CONFIG.get("COLORS.GUILDEUX")
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(f"La commande `{commande}` n'existe pas.", ephemeral=True)
        else:
            # Liste de toutes les commandes
            embed = discord.Embed(
                title="Liste des commandes disponibles",
                description="Utilisez `/help <commande>` pour obtenir plus d'informations sur une commande spécifique.",
                color=CONFIG.get("COLORS.GUILDEUX")
            )
            
            # Grouper les commandes par cog pour les commandes préfixées
            cogs_dict = {}
            for command in self.bot.commands:
                if command.hidden:
                    continue
                
                cog_name = command.cog_name or "Sans catégorie"
                if cog_name not in cogs_dict:
                    cogs_dict[cog_name] = []
                
                cogs_dict[cog_name].append(command)
            
            # Ajouter les commandes par cog
            for cog_name, commands_list in sorted(cogs_dict.items()):
                commands_text = ", ".join(f"`!{cmd.name}`" for cmd in sorted(commands_list, key=lambda x: x.name))
                embed.add_field(name=cog_name, value=commands_text, inline=False)
            
            # Ajouter les commandes slash
            slash_commands = []
            for command in self.bot.tree.get_commands():
                slash_commands.append(f"`/{command.name}`")
            
            if slash_commands:
                embed.add_field(name="Commandes Slash", value=", ".join(sorted(slash_commands)), inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommandsCog(bot))
