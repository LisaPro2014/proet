import requests
import json
import urllib.parse
import re
from datetime import datetime
import api_links
from data.game import Game
from data.user_game import UserGame


def fetch_json(url, params=None):  # переделала под словарь
    response = requests.get(url, params=params, timeout=10)
    return response.json() if response.status_code == 200 else {}


def get_player_data(api_key, steam_id):  # информация о профиле игрока
    url = api_links.get_player_summaries_url()
    query_params = {"key": api_key, "steamids": steam_id}
    data = fetch_json(url, params=query_params)
    players = data.get("response", {}).get("players", [])
    return players[0] if players else {}


def get_processed_games(api_key, steam_id):
    url = api_links.get_owned_games_url()
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }
    data = fetch_json(url, params=params)
    games = data.get("response", {}).get("games", [])
    if not games:
        return []
    for game in games:
        game["hours"] = round(game.get("playtime_forever", 0) / 60, 1)

        last_played = game.get("rtime_last_played", 0)
        if last_played > 0:
            game["last_played"] = datetime.fromtimestamp(last_played).strftime(
                "%d.%m.%Y"
            )
        else:
            game["last_played"] = "Никогда"

        game["cover"] = api_links.get_game_cover_url(game["appid"])

        icon_hash = game.get("img_icon_url")
        if icon_hash:
            game["icon_url"] = api_links.get_game_icon_url(game["appid"], icon_hash)
        else:
            game["icon_url"] = ""

    games.sort(key=lambda x: x.get("playtime_forever", 0), reverse=True)
    return games


def get_full_achievement_data(api_key, steam_id, appid):  # обработка достиджений
    ach_params = {"key": api_key, "steamid": steam_id, "appid": appid}
    schema_params = {"key": api_key, "appid": appid}
    global_params = {"gameid": appid}

    player_data = fetch_json(
        api_links.get_player_achievements_url(), params=ach_params
    ).get("playerstats", {})
    if not player_data.get("success"):
        return [], 0, 0, 0

    schema_list = (
        fetch_json(api_links.get_game_schema_url(), params=schema_params)
        .get("game", {})
        .get("availableGameStats", {})
        .get("achievements", [])
    )
    global_list = (
        fetch_json(api_links.get_global_achievements_url(), params=global_params)
        .get("achievementpercentages", {})
        .get("achievements", [])
    )

    schema_dict = {a["name"]: a for a in schema_list}
    global_dict = {a["name"]: a["percent"] for a in global_list}

    final_list = []
    unlocked = 0

    for a in player_data.get("achievements", []):
        name = a["apiname"]
        is_won = a["achieved"] == 1
        if is_won:
            unlocked += 1

        info = schema_dict.get(name, {})
        icon_url = info.get("icon", "") if is_won else info.get("icongray", "")

        if not icon_url:
            icon_url = info.get("icon", "")
        try:
            percent_val = float(global_dict.get(name, 0))
        except:
            percent_val = 0.0

        final_list.append(
            {
                "display_name": info.get("displayName", name),
                "description": info.get("description", ""),
                "icon": icon_url,
                "unlocked": is_won,
                "percent": round(percent_val, 1),
            }
        )

    total = len(final_list)
    rate = round((unlocked / total * 100)) if total > 0 else 0
    return final_list, unlocked, total, rate


def build_openid_login_url(base_url, return_to, realm):
    openid_params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{base_url}?{urllib.parse.urlencode(openid_params)}"


def validate_openid_auth(base_url, request_args):  # POST запрос в Steam
    args = dict(request_args)
    args["openid.mode"] = "check_authentication"
    response = requests.post(base_url, data=args)
    return "is_valid:true" in response.text


def extract_steam_id(claimed_id):  # steam_id
    match = re.search(r"https://steamcommunity.com/openid/id/(\d+)", claimed_id)
    return match.group(1) if match else None


def get_game_store_info(appid):  # детальная информация об игре
    url = api_links.get_app_details_url()
    params = {"appids": appid, "l": "russian", "cc": "kz"}
    data = fetch_json(url, params=params)
    return data.get(str(appid), {}).get("data", {})


def fetch_raw_featured_games():  # список игр с главной страницы Steam
    params = {"cc": "kz", "l": "russian"}
    f_resp = fetch_json(api_links.get_featured_categories_url(), params=params)
    raw_recs = []
    if "top_sellers" in f_resp:
        raw_recs.extend(f_resp["top_sellers"]["items"])
    if "specials" in f_resp:
        raw_recs.extend(f_resp["specials"]["items"])
    if "new_releases" in f_resp:
        raw_recs.extend(f_resp["new_releases"]["items"])
    return raw_recs


def filter_unowned_recommendations(api_key, steam_id, raw_recs, limit=32):
    url = api_links.get_owned_games_url()
    params = {"key": api_key, "steamid": steam_id, "include_appinfo": 0}
    g_resp = fetch_json(url, params=params)

    owned_appids = set(g["appid"] for g in g_resp.get("response", {}).get("games", []))

    unique_recs = {}
    for item in raw_recs:
        if item["id"] not in owned_appids and item["id"] not in unique_recs:
            unique_recs[item["id"]] = item

    return list(unique_recs.values())[:limit]


def get_user_news_feed(
    api_key, steam_id, games_limit=5, news_limit=3
):  # форматирует ленту новостей
    url = api_links.get_owned_games_url()
    params = {"key": api_key, "steamid": steam_id, "include_appinfo": 1}
    g_resp = fetch_json(url, params=params)
    owned_games = g_resp.get("response", {}).get("games", [])

    owned_games.sort(key=lambda x: x.get("rtime_last_played", 0), reverse=True)
    recent_games = owned_games[:games_limit]

    all_news = []
    news_base_url = api_links.get_news_url()
    for game in recent_games:
        news_params = {"appid": game["appid"], "count": news_limit}
        n_resp = fetch_json(news_base_url, params=news_params)
        news_items = n_resp.get("appnews", {}).get("newsitems", [])

        for item in news_items:
            item["game_name"] = game.get("name", "Неизвестная игра")
            all_news.append(item)

    all_news.sort(key=lambda x: x.get("date", 0), reverse=True)

    for item in all_news:
        item["date_str"] = datetime.fromtimestamp(item["date"]).strftime(
            "%d.%m.%Y %H:%M"
        )

    return all_news


def sync_user_games(db_sess, user_id, processed_games):  # синхронизация данных
    for g_data in processed_games:
        appid = g_data["appid"]
        name = g_data.get("name", "Неизвестная игра")
        playtime = g_data.get("playtime_forever", 0)

        last_played_ts = g_data.get("rtime_last_played", 0)
        last_played_dt = (
            datetime.fromtimestamp(last_played_ts) if last_played_ts > 0 else None
        )

        game_obj = db_sess.query(Game).filter(Game.id == appid).first()
        if not game_obj:
            game_obj = Game(id=appid, name=name, cover_url=g_data.get("cover", ""))
            db_sess.add(game_obj)
        link = (
            db_sess.query(UserGame)
            .filter(UserGame.user_id == user_id, UserGame.game_id == appid)
            .first()
        )
        if not link:
            link = UserGame(
                user_id=user_id,
                game_id=appid,
                playtime_forever=playtime,
                last_played=last_played_dt,
            )
            db_sess.add(link)
        else:
            link.playtime_forever = playtime
            link.last_played = last_played_dt

    db_sess.commit()
