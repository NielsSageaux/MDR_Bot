import discord
from discord.ext import commands, tasks
from discord import app_commands

from services.data_manager import DataManager
from services.google_sheets import GoogleSheetsService
from config import CONFIG
from utils.logger import setup_logger

logger = setup_logger('member_management')

class MemberManagement(commands.Cog):
    """Gestion des membres du serveur"""
    
    def __init__(self, bot):
        self.bot = bot
        self.update_members_data.start()
    
    def cog_unload(self):
        self.update_members_data.cancel()
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Gestion des nouveaux membres"""
        if member.guild.name != CONFIG["GUILD_NAME"]:
            return
        
        logger.info(f"Nouveau membre rejoint: {member.name} (ID: {member.id})")
        
        try:
            # Récupérer l'instance de DataManager
            data_manager = await DataManager.get_instance()
            
            # Vérifier si le membre existe déjà dans la base de données
            existing_member = await data_manager.get_member_data(member.id)
            
            if not existing_member:
                # Préparer les données du nouveau membre
                # Créer un tableau avec les informations du membre
                # [ID, Pseudo, Rôle, autres informations...]
                member_data = [
                    str(member.id),
                    member.display_name,
                    "Membre"  # Rôle par défaut
                ]
                
                # Ajouter le nouveau membre à la base de données
                success = await data_manager.save_member_data(
                    member_id=str(member.id),
                    data=member_data
                )
                
                if success:
                    logger.info(f"Nouveau membre ajouté à la base de données: {member.name}")
                    # Envoyer un message de bienvenue
                    welcome_channel = member.guild.get_channel(CONFIG["CHANNELS"]["BIENVENUE"])
                    if welcome_channel:
                        await welcome_channel.send(f"Hello {member.mention} ! Bienvenue à **{member.guild.name}** !")
            else:
                logger.info(f"Membre {member.name} déjà dans la base de données")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du nouveau membre {member.name} (ID: {member.id}) : {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.name != CONFIG["GUILD_NAME"]:
            return
        logger.info(f"Membre quitté: {member.name} (ID: {member.id})")

        try:
            # Récupérer l'instance de DataManager
            data_manager = await DataManager.get_instance()
            
            # Supprimer le membre de la base de données
            success = await DataManager.delete_member(member.id)
            
            if success:
                logger.info(f"Membre {member.name} supprimé de la base de données")

            else:
                logger.error(f"Erreur lors de la suppression du membre {member.name} (ID: {member.id}) de la base de données")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du membre {member.name} (ID: {member.id}) : {e}", exc_info=True)
    
    @tasks.loop(hours=1)
    async def update_members_data(self):
        """Met à jour périodiquement les données des membres"""
        logger.info("Mise à jour des données des membres...")
        
        try:
            target_guild = None
            for guild in self.bot.guilds:
                if guild.name == CONFIG["GUILD_NAME"]:
                    target_guild = guild
                    break
            
            if not target_guild:
                logger.error(f"Guilde '{CONFIG['GUILD_NAME']}' non trouvée")
                return
            
            # Récupérer l'instance de DataManager
            data_manager = await DataManager.get_instance()
            
            # Récupérer tous les membres de la feuille Google Sheets
            all_members = await GoogleSheetsService.read_all_rows(
                CONFIG["API"]["MDR_SHEET_ID"],
                "Sheet1"  # Ajustez selon votre structure
            )
            
            if not all_members or len(all_members) < 2:  # vérifier qu'il y a au moins une ligne d'en-tête et une ligne de données
                logger.error("Aucune donnée trouvée dans la feuille des membres")
                return
            
            headers = all_members[0]
            # Déterminer les indices des colonnes pertinentes
            id_col = headers.index("ID Discord") if "ID Discord" in headers else 0
            pseudo_col = headers.index("Pseudo sur serveur Discord") if "Pseudo sur serveur Discord" in headers else 1
            role_col = headers.index("Rôle") if "Rôle" in headers else 2
            
            update_count = 0
            
            # Parcourir les membres dans la base de données
            for i, row in enumerate(all_members[1:], start=0):  # Skip l'en-tête
                if len(row) <= id_col or not row[id_col].strip():
                    continue
                
                try:
                    discord_id = row[id_col].strip()
                    discord_id_int = int(discord_id)
                    guild_member = target_guild.get_member(discord_id_int)
                    
                    if not guild_member:
                        continue
                    
                    # Récupérer les informations actuelles
                    current_nickname = guild_member.display_name
                    stored_nickname = row[pseudo_col] if len(row) > pseudo_col else ""
                    
                    top_role = None
                    for role in reversed(guild_member.roles):
                        if role.name != "@everyone":
                            top_role = role.name
                            break
                    
                    if not top_role:
                        top_role = "Membre"
                    
                    stored_role = row[role_col] if len(row) > role_col else ""
                    
                    # Vérifier si une mise à jour est nécessaire
                    if current_nickname != stored_nickname or top_role != stored_role:
                        # Créer une copie de la ligne avec les données mises à jour
                        updated_row = row.copy() if len(row) >= max(id_col, pseudo_col, role_col) + 1 else [""] * (max(id_col, pseudo_col, role_col) + 1)
                        updated_row[pseudo_col] = current_nickname
                        updated_row[role_col] = top_role
                        
                        # Mise à jour des données
                        success = await GoogleSheetsService.update_row_by_id(
                            CONFIG["API"]["MDR_SHEET_ID"],
                            "Sheet1",
                            id_col,
                            discord_id,
                            updated_row
                        )
                        
                        if success:
                            update_count += 1
                            logger.info(f"Mise à jour du membre: {current_nickname} (ID: {discord_id})")
                
                except ValueError:
                    logger.error(f"ID Discord invalide dans la ligne {i+2}: {row[id_col]}")
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du membre à la ligne {i+2}: {e}", exc_info=True)
            
            if update_count > 0:
                logger.info(f"{update_count} membres mis à jour")
            else:
                logger.info("Aucun membre à mettre à jour")
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des données des membres: {e}", exc_info=True)
    
    @update_members_data.before_loop
    async def before_update_members_data(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(MemberManagement(bot))
