from discord.ext import commands
from discord import app_commands
from functools import wraps
from config import CONFIG

def is_admin():
    """Vérifie si l'utilisateur est un administrateur"""
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_passeur():
    """Vérifie si l'utilisateur est un passeur"""
    async def predicate(ctx):
        return ctx.author.id in CONFIG.get("PLAYERS").values()
    return commands.check(predicate)

def has_role(role_name):
    """Vérifie si l'utilisateur a un rôle spécifique"""
    async def predicate(ctx):
        return discord.utils.get(ctx.author.roles, name=role_name) is not None
    return commands.check(predicate)

# Pour les commandes slash
def slash_is_admin():
    """Vérifie si l'utilisateur est un administrateur (pour les commandes slash)"""
    def predicate(interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

def slash_is_passeur():
    """Vérifie si l'utilisateur est un passeur (pour les commandes slash)"""
    def predicate(interaction):
        return interaction.user.id in CONFIG.get("PLAYERS").values()
    return app_commands.check(predicate)

def slash_has_role(role_name):
    """Vérifie si l'utilisateur a un rôle spécifique (pour les commandes slash)"""
    def predicate(interaction):
        return discord.utils.get(interaction.user.roles, name=role_name) is not None
    return app_commands.check(predicate)
