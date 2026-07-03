import sqlite3
import json
import os
import smtplib
import time
import requests
from email.mime.text import MIMEText
from pymongo import MongoClient
from datetime import datetime
from flask import Flask, g, request, redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cle-secrete-a-changer"
DATABASE = "/app/data/socket.db"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/socket_logs")
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client.get_database()
logs_collection = mongo_db["logs"]
_derniers_envois = []

def log_event(event_type, username, details=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "username": username,
        "details": details,
        "source_ip": request.remote_addr
    }
    logs_collection.insert_one(entry)

def peut_envoyer_email():
    global _derniers_envois
    maintenant = time.time()
    _derniers_envois = [t for t in _derniers_envois if maintenant - t < 60]
    if len(_derniers_envois) >= 5:
        return False
    _derniers_envois.append(maintenant)
    return True

def envoyer_email(destinataire, sujet, contenu):
    serveur = os.environ.get("MAILCOW_SERVEUR")
    port = int(os.environ.get("MAILCOW_PORT", 587))
    adresse = os.environ.get("MAILCOW_ADRESSE")
    mot_de_passe = os.environ.get("MAILCOW_MOT_DE_PASSE")

    if not serveur or not adresse:
        return

    message = MIMEText(contenu)
    message["Subject"] = sujet
    message["From"] = adresse
    message["To"] = destinataire

    try:
        with smtplib.SMTP(serveur, port) as smtp:
            smtp.starttls()
            smtp.login(adresse, mot_de_passe)
            smtp.sendmail(adresse, destinataire, message.as_string())
    except Exception as e:
        log_event("EMAIL_FAILED", "system", f"Echec envoi vers {destinataire}: {str(e)}")

def stats_rspamd():
    url = os.environ.get("RSPAMD_URL")
    password = os.environ.get("RSPAMD_PASSWORD")
    if not url or not password:
        return None
    try:
        reponse = requests.get(f"{url}/stat", headers={"Password": password}, timeout=5)
        if reponse.status_code == 200:
            return reponse.json()
    except Exception as e:
        log_event("RSPAMD_STATS_FAILED", "system", str(e))
    return None

@app.before_request
def log_toutes_requetes():
    username = session.get("username", "anonyme")
    log_event("HTTP_REQUEST", username, f"{request.method} {request.path}")


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
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'analyst'
        );
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            criticite TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'detecte',
            assigne_a TEXT
        );
        CREATE TABLE IF NOT EXISTS commentaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            auteur TEXT NOT NULL,
            contenu TEXT NOT NULL,
            date_creation TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents(id)
        );
        CREATE TABLE IF NOT EXISTS tentatives_echouees (
            username TEXT PRIMARY KEY,
            nombre INTEGER NOT NULL DEFAULT 0,
            derniere_tentative TEXT
        );
        CREATE TABLE IF NOT EXISTS playbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            type_incident TEXT NOT NULL,
            description TEXT NOT NULL,
            etapes TEXT NOT NULL,
            auteur TEXT NOT NULL,
            date_creation TEXT NOT NULL
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


def admin_requis(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return "Accès refusé : réservé aux administrateurs.", 403
        return f(*args, **kwargs)
    return wrapper


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db()
        username = request.form["username"]
        email = request.form["email"]

        existe_deja = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
        ).fetchone()

        if existe_deja:
            return render_template("register.html", erreur="Ce nom d'utilisateur ou cet email existe deja.")

        db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(request.form["password"]))
        )
        db.commit()
        log_event("USER_CREATED", username)
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        username = request.form["username"]

        # Vérifie si le compte est actuellement bloqué
        tentative = db.execute(
            "SELECT * FROM tentatives_echouees WHERE username = ?", (username,)
        ).fetchone()
        if tentative and tentative["nombre"] >= 5:
            log_event("LOGIN_BLOCKED", username, "Compte temporairement bloqué (5 échecs)")
            return render_template("login.html", erreur="Compte temporairement bloqué après plusieurs échecs. Réessayez plus tard.")

        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], request.form["password"]):
            # Connexion réussie : on réinitialise le compteur d'échecs
            db.execute("DELETE FROM tentatives_echouees WHERE username = ?", (username,))
            db.commit()
            session["username"] = user["username"]
            session["role"] = user["role"]
            log_event("LOGIN_SUCCESS", user["username"])
            return redirect(url_for("accueil"))

        # Échec : on incrémente le compteur
        db.execute("""
            INSERT INTO tentatives_echouees (username, nombre, derniere_tentative)
            VALUES (?, 1, ?)
            ON CONFLICT(username) DO UPDATE SET
                nombre = nombre + 1,
                derniere_tentative = excluded.derniere_tentative
        """, (username, datetime.utcnow().isoformat()))
        db.commit()
        log_event("LOGIN_FAILED", username)
        return render_template("login.html", erreur="Identifiants incorrects.")
    return render_template("login.html")


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
    stats = {
        "total": len(incidents),
        "ouverts": len([i for i in incidents if i["statut"] != "cloture"]),
        "critiques": len([i for i in incidents if i["criticite"] == "critique"]),
        "clotures": len([i for i in incidents if i["statut"] == "cloture"]),
        "non_assignes": len([i for i in incidents if not i["assigne_a"]]),
    }
    nb_playbooks = db.execute("SELECT COUNT(*) FROM playbooks").fetchone()[0]
    return render_template("accueil.html", incidents=incidents, stats=stats, nb_playbooks=nb_playbooks)


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
    return render_template("nouveau_incident.html")


@app.route("/incident/<int:incident_id>")
@login_requis
def voir_incident(incident_id):
    db = get_db()
    incident = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    commentaires = db.execute(
        "SELECT * FROM commentaires WHERE incident_id = ? ORDER BY date_creation", (incident_id,)
    ).fetchall()
    utilisateurs = db.execute("SELECT username FROM users ORDER BY username").fetchall()
    return render_template("voir_incident.html", incident=incident, commentaires=commentaires, utilisateurs=utilisateurs)


@app.route("/incident/<int:incident_id>/commentaire", methods=["POST"])
@login_requis
def ajouter_commentaire(incident_id):
    db = get_db()
    db.execute(
        "INSERT INTO commentaires (incident_id, auteur, contenu, date_creation) VALUES (?, ?, ?, ?)",
        (incident_id, session["username"], request.form["contenu"], datetime.utcnow().isoformat())
    )
    db.commit()
    log_event("COMMENT_ADDED", session["username"], f"incident #{incident_id}")
    return redirect(url_for("voir_incident", incident_id=incident_id))


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
    entries = list(logs_collection.find().sort("timestamp", -1).limit(200))
    for e in entries:
        e["_id"] = str(e["_id"])
    return render_template("logs.html", entries=entries)


@app.route("/admin/utilisateurs")
@login_requis
@admin_requis
def liste_utilisateurs():
    db = get_db()
    users = db.execute("SELECT id, username, role FROM users").fetchall()
    return render_template("liste_utilisateurs.html", users=users)

@app.route("/incident/<int:incident_id>/assigner", methods=["POST"])
@login_requis
def assigner_incident(incident_id):
    db = get_db()
    analyste = request.form["assigne_a"]
    db.execute("UPDATE incidents SET assigne_a = ? WHERE id = ?", (analyste, incident_id))
    db.commit()
    log_event("INCIDENT_ASSIGNED", session["username"], f"incident #{incident_id} assigné à {analyste}")

    utilisateur = db.execute("SELECT email FROM users WHERE username = ?", (analyste,)).fetchone()
    if utilisateur and utilisateur["email"]:
        incident = db.execute("SELECT titre FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        envoyer_email(
            utilisateur["email"],
            f"SOCket - Nouvel incident assigne : {incident['titre']}",
            f"Bonjour,\n\nL'incident #{incident_id} ({incident['titre']}) vous a ete assigne par {session['username']}.\n\nConnectez-vous a SOCket pour plus de details.\n\n- L'equipe SOCket"
        )

    return redirect(url_for("voir_incident", incident_id=incident_id))

@app.route("/playbooks")
@login_requis
def liste_playbooks():
    db = get_db()
    playbooks = db.execute("SELECT * FROM playbooks ORDER BY date_creation DESC").fetchall()
    return render_template("playbooks.html", playbooks=playbooks)


@app.route("/playbooks/nouveau", methods=["GET", "POST"])
@login_requis
def nouveau_playbook():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO playbooks (titre, type_incident, description, etapes, auteur, date_creation) VALUES (?, ?, ?, ?, ?, ?)",
            (request.form["titre"], request.form["type_incident"], request.form["description"],
             request.form["etapes"], session["username"], datetime.utcnow().isoformat())
        )
        db.commit()
        log_event("PLAYBOOK_CREATED", session["username"], request.form["titre"])
        return redirect(url_for("liste_playbooks"))
    return render_template("nouveau_playbook.html")


@app.route("/playbooks/<int:playbook_id>")
@login_requis
def voir_playbook(playbook_id):
    db = get_db()
    playbook = db.execute("SELECT * FROM playbooks WHERE id = ?", (playbook_id,)).fetchone()
    return render_template("voir_playbook.html", playbook=playbook)

@app.route("/dashboard")
@login_requis
def dashboard():
    db = get_db()
    incidents = db.execute("SELECT * FROM incidents").fetchall()

    stats_tickets = {
        "total": len(incidents),
        "ouverts": len([i for i in incidents if i["statut"] != "cloture"]),
        "critiques": len([i for i in incidents if i["criticite"] == "critique"]),
        "hautes": len([i for i in incidents if i["criticite"] == "haute"]),
        "moyennes": len([i for i in incidents if i["criticite"] == "moyenne"]),
        "basses": len([i for i in incidents if i["criticite"] == "basse"]),
        "clotures": len([i for i in incidents if i["statut"] == "cloture"]),
        "non_assignes": len([i for i in incidents if not i["assigne_a"]]),
    }

    stats_mail = stats_rspamd()

    return render_template("dashboard.html", stats_tickets=stats_tickets, stats_mail=stats_mail)

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", debug=True)
