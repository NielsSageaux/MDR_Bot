from discord import Embed
from config import CONFIG

def create_success_embed(boss_name, success_data):
    """Crée un embed pour afficher les informations d'un succès"""
    
    success_name = list(success_data.keys())[0]
    success_info = success_data[success_name]
    
    embed = Embed(
        title=f"{boss_name} - {success_name}",
        color=CONFIG["COLORS"]["GUILDEUX"]
    )
    
    # Ajouter l'icône du boss si disponible
    if boss_name in CONFIG.get('BOSS_ICONS', {}):
        embed.set_thumbnail(url=CONFIG['BOSS_ICONS'][boss_name])
    
    # Ajouter les passeurs
    passeurs = success_info.get("passeurs", [])
    if passeurs:
        embed.add_field(
            name="Passeurs",
            value="\n".join([f"• {passeur}" for passeur in passeurs]),
            inline=True
        )
    
    # Ajouter les prix
    prix = success_info.get("prix", ["", "", ""])
    prix_kamas = prix[0]
    prix_reduc = prix[1]
    prix_coins = prix[2]
    
    if prix_kamas or prix_reduc or prix_coins:
        prix_text = []
        if prix_kamas:
            prix_text.append(f"Normal: {prix_kamas} kamas")
        if prix_reduc:
            prix_text.append(f"Réduit: {prix_reduc} kamas")
        if prix_coins:
            prix_text.append(f"Coins: {prix_coins}")
        
        embed.add_field(
            name="Prix",
            value="\n".join(prix_text),
            inline=True
        )
    
    embed.set_footer(text="Guildeux Bot | Service de passages")
    return embed
