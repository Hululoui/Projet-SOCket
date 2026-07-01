import sqlite3
import json
from datetime import datetime
from flask import Flask, g, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cle-secrete-a-changer"
DATABASE = "socket.db"


def log_event(event_type, username, details=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "username": username,
        "details": details
    }
    with open("logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            criticite TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'detecte'
        );
    """)
    db.commit()


def login_requis(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (request.form["username"], generate_password_hash(request.form["password"]))
        )
        db.commit()
        log_event("USER_CREATED", request.form["username"])
        return redirect(url_for("login"))
    return """
        <h1>Créer un compte</h1>
        <form method="POST">
            Nom d'utilisateur : <input type="text" name="username"><br>
            Mot de passe : <input type="password" name="password"><br>
            <button type="submit">Créer</button>
        </form>
    """


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form["username"],)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["username"] = user["username"]
            log_event("LOGIN_SUCCESS", user["username"])
            return redirect(url_for("accueil"))
        log_event("LOGIN_FAILED", request.form["username"])
        return "Identifiants incorrects. <a href='/login'>Réessayer</a>"
    return """
        <h1>Connexion</h1>
        <form method="POST">
            Nom d'utilisateur : <input type="text" name="username"><br>
            Mot de passe : <input type="password" name="password"><br>
            <button type="submit">Se connecter</button>
        </form>
        <a href="/register">Créer un compte</a>
    """


@app.route("/logout")
def logout():
    username = session.get("username", "inconnu")
    log_event("LOGOUT", username)
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_requis
def accueil():
    db = get_db()
    incidents = db.execute("SELECT * FROM incidents").fetchall()
    html = f"<h1>SOCket - Incidents (connecté : {session['username']})</h1><ul>"
    for i in incidents:
        html += f"""
        <li>
            #{i['id']} - {i['titre']} ({i['criticite']}) - {i['statut']}
            <form method="POST" action="/incident/{i['id']}/statut" style="display:inline">
                <select name="statut">
                    <option value="detecte">Détecté</option>
                    <option value="qualifie">Qualifié</option>
                    <option value="en_traitement">En traitement</option>
                    <option value="cloture">Clôturé</option>
                </select>
                <button type="submit">Mettre à jour</button>
            </form>
        </li>
        """
    html += "</ul><a href='/nouveau'>Créer un incident</a> | <a href='/logs'>Voir les logs</a> | <a href='/logout'>Déconnexion</a>"
    return html


@app.route("/nouveau", methods=["GET", "POST"])
@login_requis
def nouveau_incident():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO incidents (titre, criticite) VALUES (?, ?)",
            (request.form["titre"], request.form["criticite"])
        )
        db.commit()
        log_event("INCIDENT_CREATED", session["username"], request.form["titre"])
        return redirect(url_for("accueil"))
    return """
        <h1>Nouvel incident</h1>
        <form method="POST">
            Titre : <input type="text" name="titre"><br>
            Criticité : 
            <select name="criticite">
                <option value="basse">Basse</option>
                <option value="moyenne">Moyenne</option>
                <option value="haute">Haute</option>
                <option value="critique">Critique</option>
            </select><br>
            <button type="submit">Créer</button>
        </form>
    """


@app.route("/incident/<int:incident_id>/statut", methods=["POST"])
@login_requis
def changer_statut(incident_id):
    db = get_db()
    nouveau_statut = request.form["statut"]
    db.execute("UPDATE incidents SET statut = ? WHERE id = ?", (nouveau_statut, incident_id))
    db.commit()
    log_event("INCIDENT_STATUS_CHANGE", session["username"], f"incident #{incident_id} -> {nouveau_statut}")
    return redirect(url_for("accueil"))


@app.route("/logs")
@login_requis
def voir_logs():
    lignes = []
    try:
        with open("logs.jsonl", "r", encoding="utf-8") as f:
            lignes = [json.loads(l) for l in f.readlines()]
    except FileNotFoundError:
        pass
    lignes.reverse()
    html = "<h1>Logs de sécurité</h1><table border='1' cellpadding='5'>"
    html += "<tr><th>Horodatage</th><th>Événement</th><th>Utilisateur</th><th>Détails</th></tr>"
    for l in lignes:
        html += f"<tr><td>{l['timestamp']}</td><td>{l['event_type']}</td><td>{l['username']}</td><td>{l['details']}</td></tr>"
    html += "</table><br><a href='/'>Retour</a>"
    return html


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)