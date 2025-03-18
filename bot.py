import discord # type: ignore
import os
from dotenv import load_dotenv # type: ignore
load_dotenv()

print("Lancement du bot...")
bot = discord.Client(intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot allumé !")

@bot.event
async def on_message(message: discord.Message):
    if message.channel == bot.get_channel(1351682008925077635):
        general_channel = bot.get_channel(1159293913543225367)
        embed = discord.Embed(

        )  

bot.run(os.getenv('DISCORD_TOKEN'))