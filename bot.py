#!/usr/bin/env python3
import discord
from discord.ext import commands
import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

from config import CONFIG
from utils.logger import setup_logger

# Initialiser le logger
logger = setup_logger('bot_main')

# Charger les variables d'environnement
load_dotenv()

# Configurer les intents
intents = discord.Intents.all()
intents.message_content = True
intents.members = True

# Initialiser le bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Ajouter un gestionnaire d'erreurs pour les commandes slash
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    logger.error(f"Erreur de commande slash: {error} (Serveur: {interaction.guild.name if interaction.guild else 'DM'}, Canal: {interaction.channel.name if interaction.channel else 'N/A'}, Utilisateur: {interaction.user})", exc_info=True)
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message(
                f"Une erreur s'est produite lors de l'exécution de cette commande: {error}", 
                ephemeral=True
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                f"Une erreur s'est produite lors de l'exécution de cette commande: {error}", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Impossible d'envoyer le message d'erreur: {e}", exc_info=True)

# Charger les cogs (extensions)
async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('_'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f"Extension chargée: {filename}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement de l'extension {filename}: {e}", exc_info=True)

# Événement de démarrage
@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user}')
    
    # Synchronisation globale des commandes
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synchronisation globale de {len(synced)} commande(s)')
        logger.info(f'Le bot est maintenant disponible sur tous les serveurs où il est invité.')
    except Exception as e:
        logger.error(f'Erreur lors de la synchronisation des commandes: {e}', exc_info=True)

# Événement lorsque le bot rejoint un nouveau serveur
@bot.event
async def on_guild_join(guild):
    logger.info(f"Bot ajouté à un nouveau serveur: {guild.name} (ID: {guild.id})")

# Gestion de l'arrêt propre
def signal_handler():
    logger.info("Arrêt du bot demandé...")
    # Permettre d'autres nettoyages ici si nécessaire
    asyncio.get_event_loop().stop()
    logger.info("Bot arrêté avec succès")

async def main():
    # Gestion des signaux (Ctrl+C)
    try:
        loop = asyncio.get_running_loop()
        
        # Pour Windows
        if sys.platform == 'win32':
            loop.add_signal_handler(signal.SIGINT, signal_handler)
            loop.add_signal_handler(signal.SIGTERM, signal_handler)
        # Pour Unix/Linux/Mac
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Si la plateforme ne supporte pas add_signal_handler
        pass

    try:
        async with bot:
            await load_extensions()
            await bot.start(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur (Ctrl+C)")
        if bot.is_closed():
            logger.info("Bot déjà fermé")
        else:
            logger.info("Fermeture du bot...")
            await bot.close()
            logger.info("Bot fermé avec succès")
    finally:
        logger.info("Nettoyage final et sortie")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Cette branche devrait rarement être atteinte
        # grâce à la gestion des signaux ci-dessus
        print("Bot arrêté manuellement")
    except Exception as e:
        logger.critical(f"Erreur critique: {e}", exc_info=True)
