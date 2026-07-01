import sqlite3
import json
from datetime import datetime
from flask import Flask, g, request, redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cle-secrete-a-changer"
DATABASE = "socket.db"


def log_event(event_type, username, details=""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "username": username,
        "details": details,
        "source_ip": request.remote_addr
    }
    with open("logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


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
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'analyst'
        );
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            criticite TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'detecte'
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
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (request.form["username"], generate_password_hash(request.form["password"]))
        )
        db.commit()
        log_event("USER_CREATED", request.form["username"])
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
    }
    return render_template("accueil.html", incidents=incidents, stats=stats)


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
    return render_template("voir_incident.html", incident=incident, commentaires=commentaires)


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
    entries = []
    try:
        with open("logs.jsonl", "r", encoding="utf-8") as f:
            entries = [json.loads(l) for l in f.readlines()]
    except FileNotFoundError:
        pass
    entries.reverse()
    return render_template("logs.html", entries=entries)


@app.route("/admin/utilisateurs")
@login_requis
@admin_requis
def liste_utilisateurs():
    db = get_db()
    users = db.execute("SELECT id, username, role FROM users").fetchall()
    return render_template("liste_utilisateurs.html", users=users)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", debug=True)