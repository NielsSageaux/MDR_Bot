import discord # type: ignore
from discord import app_commands # type: ignore
from discord.ext import commands # type: ignore
import os
from dotenv import load_dotenv # type: ignore
import datetime


load_dotenv()

CHANNEL_PRESENTATION_GUILDEUX_ID = int(os.getenv('CHANNEL_PRESENTATION_GUILDEUX'))
CHANNEL_PRESENTATION_HG_ID = int(os.getenv('CHANNEL_PRESENTATION_HG'))
CHANNEL_BISTROT_ID = int(os.getenv('CHANNEL_BISTROT'))

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synchronisation de {len(synced)} commande(s)')
    except Exception as e:
        print(f'Erreur lors de la synchronisation des commandes: {e}')

def limiter_mots(texte, limite=100):
    mots = texte.split()
    if len(mots) <= limite:
        return texte
    else:
        return ' '.join(mots[:limite]) + '...'

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.id in [CHANNEL_PRESENTATION_GUILDEUX_ID, CHANNEL_PRESENTATION_HG_ID]:
        destination_channel = bot.get_channel(CHANNEL_BISTROT_ID)
        
        if destination_channel:
            content_limited = limiter_mots(message.content, 100)
            

            if message.channel.id == CHANNEL_PRESENTATION_GUILDEUX_ID:
                titre = ":rotating_light: Nouvelle Présentation de Guildeux !!! :rotating_light:"
                color = discord.Color.purple()
            else:
                titre = ":rotating_light: Nouvelle Présentation de Haut Gradé !!! :rotating_light:"
                color = discord.Color.red()
            
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
            if message.attachments:
                attachment = message.attachments[0]
                if attachment.content_type and attachment.content_type.startswith('image'):
                    embed.set_image(url=attachment.url)
            # embed.set_footer(text=f"ID: {message.id}")
            
            await destination_channel.send(embed=embed)
            print(f"Embed créé pour le message de {message.author.display_name}")
    
    # Traite les commandes normalement
    await bot.process_commands(message)

@bot.tree.command(name='passage', description='Envoie un message visible uniquement par vous')
@app_commands.describe(contenu='Le contenu du message')
async def message_prive(interaction: discord.Interaction, contenu: str):
    await interaction.response.send_message(f"**Message privé:** {contenu}", ephemeral=True)

bot.run(os.getenv('DISCORD_TOKEN'))