import discord
from discord.ext import commands
import traceback
import sys
from utils.logger import setup_logger

logger = setup_logger('error_handler')

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Gestionnaire global des erreurs de commandes."""
        if hasattr(ctx.command, 'on_error'):
            return  # Ne pas interférer avec les gestionnaires d'erreurs personnalisés
            
        # Obtenir l'erreur d'origine si elle est encapsulée
        error = getattr(error, 'original', error)
        
        if isinstance(error, commands.CommandNotFound):
            return  # Ignorer les commandes non trouvées
        
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'La commande `{ctx.command}` est désactivée.')
            
        elif isinstance(error, commands.NoPrivateMessage):
            return await ctx.author.send(f'La commande `{ctx.command}` ne peut pas être utilisée en messages privés.')
        
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f'Argument manquant: `{error.param.name}`')
            
        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f'Argument incorrect: {str(error)}')
            
        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f'Vous n\'avez pas les permissions requises: `{", ".join(error.missing_permissions)}`')
            
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f'Je n\'ai pas les permissions requises: `{", ".join(error.missing_permissions)}`')
            
        # Enregistrer les erreurs non gérées
        logger.error(f'Erreur non gérée dans la commande {ctx.command}:')
        logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
        
        # Informer l'utilisateur
        await ctx.send(f'Une erreur s\'est produite lors de l\'exécution de la commande: `{str(error)}`')
    
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """Gestionnaire global des erreurs d'événements."""
        logger.error(f'Erreur non gérée dans l\'événement {event}:')
        logger.error(''.join(traceback.format_exception(*sys.exc_info())))

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
