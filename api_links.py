STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"  # авторизация через стим

def get_featured_categories_url(): # главная страница
    return "https://store.steampowered.com/api/featuredcategories/"

def get_player_summaries_url(): # информация о профиле
    return "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

def get_owned_games_url(): # список игр пользователя
    return "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"

def get_game_cover_url(appid): # шапка игры
    return f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
def get_player_achievements_url(): # ачивки пользователя
    return "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"

def get_game_schema_url(): # все достиджения игры
    return "http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"

def get_global_achievements_url(): # статистика по всем игрокам
    return "http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"

def get_app_details_url(): # данные об игре
    return "https://store.steampowered.com/api/appdetails"

def get_news_url(): # новости
    return "http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"

def get_game_icon_url(appid, icon_hash): # иконка игры
    return f"http://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_hash}.jpg"