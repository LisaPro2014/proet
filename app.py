from flask import Flask, request, redirect, session, render_template, flash, url_for
from datetime import datetime
from data.steam_cache import SteamCache
from datetime import datetime, timedelta
from werkzeug.exceptions import HTTPException
import json
from werkzeug.security import generate_password_hash, check_password_hash
from forms.forms import RegisterForm, EditProfileForm
import os
from dotenv import load_dotenv
import data.db_session as db_session
from data.user import User
import api_links
import steam_utils

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")
STEAM_API_KEY = os.getenv("API_KEY")
BASE_URL=os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')
basedir = os.path.abspath(os.path.dirname(__file__))  # путь до папки
sql_folder = os.path.join(basedir, "sql")
db_path = os.path.join(sql_folder, "steam_users.db")
db_session.global_init(db_path)


def get_user_context():
    db_sess = db_session.create_session()
    user_id = session.get("user_id")
    user = db_sess.get(User, user_id) if user_id else None
    return db_sess, user


@app.route("/")
def index():
    db_sess, user = get_user_context()
    # загружаем рекомендации  без привязки к акку
    raw_recs = steam_utils.fetch_raw_featured_games()
    recommendations = list({item["id"]: item for item in raw_recs}.values())[:15]
    return render_template("index.html", user=user, recs=recommendations)


@app.route("/login")
def login():
    url = steam_utils.build_openid_login_url(
        api_links.STEAM_OPENID_URL,
        f"{BASE_URL}/authorize",
        BASE_URL,
    )
    return redirect(url)


@app.route("/authorize")
def authorize():
    if steam_utils.validate_openid_auth(api_links.STEAM_OPENID_URL, request.args):
        steam_id = steam_utils.extract_steam_id(
            request.args.get("openid.claimed_id", "")
        )

        if steam_id:
            player_data = steam_utils.get_player_data(STEAM_API_KEY, steam_id)
            player_json_str = json.dumps(player_data, ensure_ascii=False)

            db_sess, current_user = get_user_context()
            user_with_steam = (
                db_sess.query(User).filter(User.steam_id == steam_id).first()
            )

            if current_user:
                if user_with_steam and user_with_steam.id != current_user.id:
                    flash(
                        "Этот профиль Steam уже привязан к другому аккаунту!", "danger"
                    )
                    return redirect(url_for("profile"))

                current_user.steam_id = steam_id
                current_user.nickname = player_data.get(
                    "personaname", current_user.nickname
                )
                current_user.avatar_url = player_data.get(
                    "avatarfull", current_user.avatar_url
                )
                current_user.profile_json = player_json_str
                db_sess.commit()

                flash("Steam успешно привязан!", "success")
                return redirect(url_for("profile"))

            else:
                if user_with_steam:
                    user_with_steam.profile_json = player_json_str
                    db_sess.commit()
                    session["user_id"] = user_with_steam.id
                    flash(f"С возвращением, {user_with_steam.nickname}!", "success")
                    return redirect(url_for("index"))
                else:
                    new_user = User(
                        steam_id=steam_id,
                        nickname=player_data.get("personaname", "Новый игрок"),
                        avatar_url=player_data.get("avatarfull", ""),
                        profile_json=player_json_str,
                    )
                    db_sess.add(new_user)
                    db_sess.commit()
                    session["user_id"] = new_user.id
                    flash("Аккаунт успешно создан через Steam!", "success")
                    return redirect(url_for("index"))

    flash("Не удалось подтвердить авторизацию Steam.", "danger")
    return redirect(url_for("login_email"))


@app.route("/games")
def games():
    db_sess, user = get_user_context()
    if not user:
        return redirect("/login_email")
    if not user.steam_id:
        return redirect("/profile")
    processed_games = steam_utils.get_processed_games(STEAM_API_KEY, user.steam_id)
    steam_utils.sync_user_games(db_sess, user.id, processed_games)

    return render_template("games.html", user=user, games=processed_games)


@app.route("/game/<int:appid>")
def game_details(appid):
    db_sess, user = get_user_context()
    if not user:
        return redirect("/login_email")
    if not user.steam_id:
        return redirect("/profile")

    game_info = steam_utils.get_game_store_info(appid)
    achievements, unlocked, total, rate = steam_utils.get_full_achievement_data(
        STEAM_API_KEY, user.steam_id, appid
    )

    return render_template(
        "game_details.html",
        game=game_info,
        user=user,
        achievements=achievements,
        unlocked=unlocked,
        total=total,
        rate=rate,
    )


@app.route("/recommendations")
def recommendations():
    db_sess, user = get_user_context()
    if not user:
        return redirect("/login_email")
    if not user.steam_id:
        return redirect("/profile")

    cache_key = "featured_games"
    cache_entry = (
        db_sess.query(SteamCache).filter(SteamCache.key_name == cache_key).first()
    )
    now = datetime.now()
    raw_recs = []

    # эту часть кода не получилось вынести
    if cache_entry and (now - cache_entry.updated_at) < timedelta(days=3):
        try:
            raw_recs = json.loads(cache_entry.data_json)
        except json.JSONDecodeError:
            raw_recs = []

    if not raw_recs:
        raw_recs = steam_utils.fetch_raw_featured_games()
        if raw_recs:
            if not cache_entry:
                cache_entry = SteamCache(key_name=cache_key)
                db_sess.add(cache_entry)
            cache_entry.data_json = json.dumps(raw_recs, ensure_ascii=False)
            cache_entry.updated_at = now
            db_sess.commit()
        elif cache_entry:
            raw_recs = json.loads(cache_entry.data_json)

    final_recs = steam_utils.filter_unowned_recommendations(
        STEAM_API_KEY, user.steam_id, raw_recs
    )
    return render_template("recommendations.html", user=user, recs=final_recs)


@app.route("/news")
def news_page():
    db_sess, user = get_user_context()
    if not user:
        return redirect("/login_email")
    if not user.steam_id:
        return redirect("/profile")
    all_news = steam_utils.get_user_news_feed(STEAM_API_KEY, user.steam_id)
    return render_template("news.html", user=user, news=all_news)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        db_sess, _ = get_user_context()
        if db_sess.query(User).filter(User.email == email).first():
            flash("Пользователь с такой почтой уже существует", "warning")
            return redirect(url_for("register"))
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db_sess.add(new_user)
        db_sess.commit()
        session["user_id"] = new_user.id
        return redirect(url_for("profile"))
    return render_template("register.html", form=form)


@app.route("/login_email", methods=["GET", "POST"])
def login_email():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db_sess, _ = get_user_context()
        user = db_sess.query(User).filter(User.email == email).first()

        if (
            user
            and user.password_hash
            and check_password_hash(user.password_hash, password)
        ):
            session["user_id"] = user.id
            return redirect(url_for("index"))

        flash("Неверная почта или пароль", "danger")
        return redirect(url_for("login_email"))

    return render_template("login_email.html")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    db_sess, user = get_user_context()
    if not user:
        return redirect("/login_email")

    form = EditProfileForm()

    if request.method == "GET":
        form.email.data = user.email

    if form.validate_on_submit():
        new_email = form.email.data
        current_password = form.current_password.data
        new_password = form.new_password.data

        password_valid = True
        if user.password_hash:
            if not current_password or not check_password_hash(user.password_hash, current_password):
                form.current_password.errors.append("Неверный текущий пароль.")
                password_valid = False

        if password_valid:
            if new_email and new_email != user.email:
                user.email = new_email

            if new_password:
                user.password_hash = generate_password_hash(new_password)

            db_sess.commit()
            flash("Данные профиля успешно обновлены!", "success")
            return redirect(url_for("profile"))

    full_info = {}
    if user.profile_json:
        try:
            full_info = json.loads(user.profile_json)
        except Exception:
            pass

    return render_template("profile.html", user=user, info=full_info, form=form)

@app.route("/register_steam", methods=["GET", "POST"])
def register_steam():
    steam_id = session.get("pending_steam_id")
    if not steam_id:
        return redirect("/login_email")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        db_sess, _ = get_user_context()
        if db_sess.query(User).filter(User.email == email).first():
            flash("Эта почта уже занята.", "warning")
            return redirect(url_for("register_steam"))

        steam_data = session.get("pending_steam_data", {})

        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            steam_id=steam_id,
            nickname=steam_data.get("nickname"),
            avatar_url=steam_data.get("avatar"),
            profile_json=steam_data.get("raw_json"),
        )
        db_sess.add(new_user)
        db_sess.commit()

        session.pop("pending_steam_id", None)
        session.pop("pending_steam_data", None)
        session["user_id"] = new_user.id
        return redirect("/")

    return render_template("register_steam.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")


@app.errorhandler(404) # обработка при ошибке 404
def page_not_found(e):
    try:
        db_sess, user = get_user_context()
    except Exception:
        user = None
    return (
        render_template(
            "error.html", user=user, error_code=404, error_message="Страница не найдена"
        ),
        404,
    )


@app.errorhandler(Exception) # при остальных ошибках
def handle_exception(e):
    try:
        db_sess, user = get_user_context()
    except Exception:
        user = None
    code = 500
    if isinstance(e, HTTPException):
        code = e.code

    error_message = "Упс! Что-то пошло не так."
    if code == 403:
        error_message = "Доступ запрещен."
    elif code == 500:
        error_message = "Внутренняя ошибка сервера."

    return (
        render_template(
            "error.html", user=user, error_code=code, error_message=error_message
        ),
        code,
    )


if __name__ == "__main__":
    app.run(port=5000)
