import json
from discord.ext import tasks
import time
from utils.logger import setup_logger
from services.google_sheets import GoogleSheetsService
from config import CONFIG

logger = setup_logger('data_manager')

class DataCache:
    def __init__(self, ttl=3600):  # TTL par défaut: 1 heure
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache and time.time() < self.cache[key]['expires']:
            return self.cache[key]['data']
        return None
    
    def set(self, key, data, ttl=None):
        expires = time.time() + (ttl if ttl else self.ttl)
        self.cache[key] = {
            'data': data,
            'expires': expires
        }
    
    def invalidate(self, key=None):
        if key:
            if key in self.cache:
                del self.cache[key]
        else:
            self.cache.clear()

class DataManager:
    _instance = None
    _passages_data = {}
    _cache = DataCache()
    _boss_list = []
    
    def __init__(self):
        self._load_data_task = None
    
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = DataManager()
            await cls._instance.initialize()
        return cls._instance
    
    async def initialize(self):
        await self.load_data_once()
        # Démarrer la tâche périodique
        if self._load_data_task is None:
            self._load_data_task = self.load_data
            self._load_data_task.start()

    @staticmethod
    def get_passages_data():
        return DataManager._passages_data

    @staticmethod
    def get_boss_list():
        return DataManager._boss_list
    
    async def load_data_once(self):
        """Version sans décorateur pour l'initialisation"""
        cached_data = DataManager._cache.get('passages_data')
        if cached_data:
            DataManager._passages_data = cached_data
            return True
        
        try:
            spreadsheet_id = CONFIG["API"]["PASSAGES_SHEET_ID"]
            sheet_name = "Sheet1"
            range_name = f"{sheet_name}!A:F"
            
            data = await GoogleSheetsService.read_all_rows(
                spreadsheet_id,
                range_name
            )
            
            if data:
                processed_data = {}
                DataManager._boss_list = []  # Reset la liste
                
                for row in data[1:]:
                    if len(row) > 5:
                        if processed_data.get(row[0]) is None:
                            processed_data[row[0]] = {"ICONE": row[1], "SUCCESS": {}}
                            DataManager._boss_list.append(row[0])
                        processed_data[row[0]]["SUCCESS"][row[2]] = {
                            "prix (kamas)": row[3],
                            "prix (coins)": row[4],
                            "passeurs": row[5]
                        }
                
                DataManager._passages_data = processed_data
                DataManager._cache.set('passages_data', processed_data)
                logger.info(f"Données chargées: {len(processed_data)} éléments trouvés")
                return True
            else:
                logger.error("Aucune donnée trouvée")
                return False
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}", exc_info=True)
            return False
    
    @tasks.loop(hours=1)
    async def load_data(self):
        """Charge les données depuis Google Sheets de manière périodique"""
        return await self.load_data_once()
    
    @load_data.error
    async def load_data_error(self, error):
        """Gère les erreurs de la tâche pour éviter qu'elle s'arrête"""
        logger.error(f"Erreur dans la tâche load_data: {error}", exc_info=True)

    async def save_member_data(self, member_id, data):
        """Sauvegarde les données d'un membre"""
        try:
            # Utiliser le nouveau GoogleSheetsService
            spreadsheet_id = CONFIG["API"]["MDR_SHEET_ID"]
            sheet_name = "Sheet1"  # Ajustez selon votre nom de feuille
            
            # Vérifier si le membre existe déjà
            row_index = await GoogleSheetsService.find_row_index(
                spreadsheet_id,
                sheet_name,
                0,  # Supposant que l'ID est dans la première colonne
                member_id
            )
            
            result = False
            if row_index != -1:
                # Mettre à jour un membre existant
                result = await GoogleSheetsService.update_row_by_id(
                    spreadsheet_id,
                    sheet_name,
                    0,  # Colonne ID
                    member_id,
                    data
                )
            else:
                # Créer un nouveau membre
                # Assurez-vous que member_id est dans data[0]
                if data[0] != member_id:
                    data.insert(0, member_id)
                result = await GoogleSheetsService.create_row(
                    spreadsheet_id,
                    sheet_name,
                    data
                )
            
            # Invalider le cache
            DataManager._cache.invalidate(f'member_{member_id}')
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données du membre {member_id}: {e}", exc_info=True)
            return False
    
    async def get_member_data(self, member_id):
        """Récupère les données d'un membre"""
        cache_key = f'member_{member_id}'
        cached_data = DataManager._cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            spreadsheet_id = CONFIG["API"]["MDR_SHEET_ID"]
            sheet_name = "Sheet1"  # Ajustez selon votre nom de feuille
            
            member_data = await GoogleSheetsService.read_row_by_id(
                spreadsheet_id,
                sheet_name,
                0,  # Colonne ID
                member_id
            )
            
            if member_data:
                DataManager._cache.set(cache_key, member_data)
                return member_data
            else:
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du membre {member_id}: {e}", exc_info=True)
            return None
    
    async def delete_member(self, member_id):
        """Supprime un membre (ou vide ses données)"""
        try:
            spreadsheet_id = CONFIG["API"]["MDR_SHEET_ID"]
            sheet_name = "Sheet1"
            
            result = await GoogleSheetsService.delete_row_by_id(
                spreadsheet_id,
                sheet_name,
                0,  # Colonne ID
                member_id
            )
            
            # Invalider le cache
            DataManager._cache.invalidate(f'member_{member_id}')
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du membre {member_id}: {e}", exc_info=True)
            return False
