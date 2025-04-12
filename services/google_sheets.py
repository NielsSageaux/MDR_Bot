from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import json

from config import CONFIG
from utils.logger import setup_logger

logger = setup_logger('google_sheets')

class GoogleSheetsService:
    """Service pour interagir avec l'API Google Sheets avec fonctionnalités CRUD simplifiées"""
    
    @staticmethod
    def get_credentials():
        """Récupère les informations d'identification pour l'API Google Sheets"""
        if os.path.exists('credentials.json'):
            return service_account.Credentials.from_service_account_file(
                'credentials.json', 
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        elif os.environ.get('GOOGLE_CREDENTIALS'):
            credentials_info = json.loads(os.environ['GOOGLE_CREDENTIALS'])
            return service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            raise Exception("Aucune méthode d'authentification disponible")
    
    @staticmethod
    def get_service():
        """Retourne un service pour toutes les opérations avec le compte de service"""
        try:
            creds = GoogleSheetsService.get_credentials()
            service = build('sheets', 'v4', credentials=creds)
            return service.spreadsheets()
        except Exception as e:
            logger.error(f"Erreur d'initialisation du service: {e}", exc_info=True)
            return None
    
    # =========== OPÉRATIONS CRUD DE BASE ===========
    
    @staticmethod
    async def read_all_rows(spreadsheet_id, sheet_name):
        """
        Récupère toutes les lignes d'une feuille spécifique.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            
        Returns:
            list: Liste de toutes les lignes avec leurs valeurs, ou None en cas d'erreur.
        """
        try:
            sheets = GoogleSheetsService.get_service()
            if not sheets:
                logger.error("Impossible d'initialiser le service")
                return None
            
            range_name = f"{sheet_name}"
            result = sheets.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {sheet_name}: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def read_row_by_id(spreadsheet_id, sheet_name, id_column, id_value):
        """
        Récupère une ligne spécifique basée sur la valeur d'ID dans une colonne.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            id_column (int): Numéro de la colonne contenant l'ID (0 pour A, 1 pour B, etc.).
            id_value (str): Valeur de l'ID à rechercher.
            
        Returns:
            list: La ligne trouvée ou None si non trouvée ou en cas d'erreur.
        """
        try:
            all_data = await GoogleSheetsService.read_all_rows(spreadsheet_id, sheet_name)
            if not all_data:
                return None
                
            for row in all_data:
                if len(row) > id_column and str(row[id_column]) == str(id_value):
                    return row
            
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de ligne avec ID {id_value}: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def find_row_index(spreadsheet_id, sheet_name, id_column, id_value):
        """
        Trouve l'index (numéro de ligne) d'une entrée spécifique.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            id_column (int): Numéro de la colonne contenant l'ID (0 pour A, 1 pour B, etc.).
            id_value (str): Valeur de l'ID à rechercher.
            
        Returns:
            int: L'index de la ligne (0-based) ou -1 si non trouvé ou erreur.
        """
        try:
            all_data = await GoogleSheetsService.read_all_rows(spreadsheet_id, sheet_name)
            if not all_data:
                return -1
                
            for i, row in enumerate(all_data):
                if len(row) > id_column and str(row[id_column]) == str(id_value):
                    return i
            
            return -1
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de l'index avec ID {id_value}: {e}", exc_info=True)
            return -1
    
    @staticmethod
    async def create_row(spreadsheet_id, sheet_name, row_data):
        """
        Ajoute une nouvelle ligne à la fin de la feuille.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            row_data (list): Liste des valeurs à ajouter dans la ligne.
            
        Returns:
            bool: True si succès, False sinon.
        """
        try:
            sheets = GoogleSheetsService.get_service()
            if not sheets:
                logger.error("Impossible d'initialiser le service")
                return False
            
            range_name = f"{sheet_name}"
            body = {
                'values': [row_data]
            }
            
            sheets.values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création de ligne: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def update_row_by_id(spreadsheet_id, sheet_name, id_column, id_value, new_row_data):
        """
        Met à jour une ligne existante basée sur l'ID.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            id_column (int): Numéro de la colonne contenant l'ID (0 pour A, 1 pour B, etc.).
            id_value (str): Valeur de l'ID à rechercher.
            new_row_data (list): Nouvelle liste de valeurs pour la ligne.
            
        Returns:
            bool: True si succès, False sinon.
        """
        try:
            row_index = await GoogleSheetsService.find_row_index(
                spreadsheet_id, sheet_name, id_column, id_value
            )
            
            if row_index == -1:
                logger.error(f"Ligne avec ID {id_value} non trouvée")
                return False
            
            # Convertir l'index en numéro de ligne (1-based) pour Google Sheets
            row_number = row_index + 1
            
            sheets = GoogleSheetsService.get_service()
            if not sheets:
                logger.error("Impossible d'initialiser le service")
                return False
            
            range_name = f"{sheet_name}!A{row_number}"
            body = {
                'values': [new_row_data]
            }
            
            sheets.values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de ligne: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def update_cell(spreadsheet_id, sheet_name, row, column, value):
        """
        Met à jour une cellule spécifique.
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            row (int): Index de la ligne (1-based).
            column (int): Index de la colonne (0-based, A=0, B=1, etc.).
            value (any): Nouvelle valeur pour la cellule.
            
        Returns:
            bool: True si succès, False sinon.
        """
        try:
            # Convertir l'index de colonne en lettre (A, B, C...)
            column_letter = chr(65 + column)  # 65 est le code ASCII pour 'A'
            
            sheets = GoogleSheetsService.get_service()
            if not sheets:
                logger.error("Impossible d'initialiser le service")
                return False
            
            range_name = f"{sheet_name}!{column_letter}{row}"
            body = {
                'values': [[value]]
            }
            
            sheets.values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de cellule: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def delete_row_by_id(spreadsheet_id, sheet_name, id_column, id_value):
        """
        Efface le contenu d'une ligne (la ligne reste mais ses cellules sont vides).
        
        Args:
            spreadsheet_id (str): ID du document Google Sheets.
            sheet_name (str): Nom de la feuille (ex: "Membres").
            id_column (int): Numéro de la colonne contenant l'ID (0 pour A, 1 pour B, etc.).
            id_value (str): Valeur de l'ID à rechercher.
            
        Returns:
            bool: True si succès, False sinon.
        """
        try:
            row_index = await GoogleSheetsService.find_row_index(
                spreadsheet_id, sheet_name, id_column, id_value
            )
            logger.info(f"Row index: {row_index}")
            
            if row_index == -1:
                logger.error(f"Ligne avec ID {id_value} non trouvée")
                return False
            
            sheets = GoogleSheetsService.get_service()
            if not sheets:
                logger.error("Impossible d'initialiser le service")
                return False
            
            spreadsheet = sheets.get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = None

            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                logger.error(f"Feuille {sheet_name} non trouvée dans le document")
                return False

            body = {
                "requests": [
                    {    
                        "deleteDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": row_index,
                                "endIndex": row_index + 1
                            }
                        }
                    }
                ]
            }

            sheets.batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Erreur lors de la suppression de ligne: {e}", exc_info=True)
            return False