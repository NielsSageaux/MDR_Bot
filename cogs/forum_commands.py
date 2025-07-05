import discord
from discord import app_commands
from discord.ext import commands
from utils.logger import setup_logger
from config import CONFIG

logger = setup_logger('forum_commands')

class ForumCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="fermer", description="Ferme le thread en cours")
    async def close_thread(self, interaction: discord.Interaction):
        """Ferme le thread dans lequel est utilisée la commande"""
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
        
        has_permissions = (
            member.guild_permissions.manage_threads or 
            member.guild_permissions.administrator
        )
        
        if not (is_creator or has_permissions):
            await interaction.response.send_message(
                "Vous n'avez pas la permission de fermer ce thread.",
                ephemeral=True
            )
            return
        
        try:
            messages = []
            async for message in thread.history(limit=None):
                if message.content.strip():
                    messages.append(f"{message.author.display_name}: {message.content}")
            
            messages.reverse()

            filename = f"conversation_{thread.id}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Thread: {thread.name}\n")
                f.write("\n".join(messages))

            await self.bot.get_channel(CONFIG["CHANNELS"]["TRANSCRIPT"]).send(
                f"📁 Thread fermé: **{thread.name}**",
                file=discord.File(filename)
            )

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

async def setup(bot):
    await bot.add_cog(ForumCommands(bot))
