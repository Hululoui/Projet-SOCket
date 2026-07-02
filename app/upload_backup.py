"""
Ce script envoie une sauvegarde vers Google Drive (via OAuth) et vers un depot GitHub prive.
"""
import sys
import os
import requests
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

DOSSIER_DRIVE_NOM = "SOCket-Backups"
SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = "/app/data/google_token.json"
import glob
_fichiers_secret = glob.glob("/app/client_secret*.json")
CLIENT_SECRET_PATH = _fichiers_secret[0] if _fichiers_secret else None


def obtenir_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url(prompt="consent")
            print(f"\n\nVeuillez ouvrir ce lien dans votre navigateur :\n{auth_url}\n")
            code = input("Collez ici le code fourni par Google : ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return creds


def trouver_dossier(service, nom, parent_id=None):
    requete = f"name='{nom}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        requete += f" and '{parent_id}' in parents"
    resultats = service.files().list(q=requete, fields="files(id, name)").execute()
    dossiers = resultats.get("files", [])
    return dossiers[0]["id"] if dossiers else None


def upload_vers_drive(chemin_fichier, nom_fichier):
    creds = obtenir_credentials()
    service = build("drive", "v3", credentials=creds)

    ynov_id = trouver_dossier(service, "Ynov")
    if not ynov_id:
        print("Dossier 'Ynov' introuvable.")
        return

    filrouge_id = trouver_dossier(service, "Fil-rouge", ynov_id)
    if not filrouge_id:
        print("Dossier 'Fil-rouge' introuvable dans Ynov.")
        return

    backup_id = trouver_dossier(service, DOSSIER_DRIVE_NOM, filrouge_id)
    if not backup_id:
        print(f"Dossier '{DOSSIER_DRIVE_NOM}' introuvable dans Ynov/Fil-rouge.")
        return

    metadata = {"name": nom_fichier, "parents": [backup_id]}
    media = MediaFileUpload(chemin_fichier, resumable=True)
    fichier = service.files().create(body=metadata, media_body=media, fields="id").execute()
    print(f"Envoye vers Google Drive : {nom_fichier} (id: {fichier.get('id')})")


def upload_vers_github(chemin_fichier, nom_fichier):
    token = os.environ.get("GITHUB_BACKUP_TOKEN")
    depot = "Hululoui/socket-backups"

    with open(chemin_fichier, "rb") as f:
        contenu = base64.b64encode(f.read()).decode("utf-8")

    url = f"https://api.github.com/repos/{depot}/contents/{nom_fichier}"
    headers = {"Authorization": f"token {token}"}
    data = {"message": f"backup: {nom_fichier}", "content": contenu}

    reponse = requests.put(url, json=data, headers=headers)
    if reponse.status_code in (200, 201):
        print(f"Envoye vers GitHub : {nom_fichier}")
    else:
        print(f"Echec envoi GitHub : {reponse.status_code} - {reponse.text}")


if __name__ == "__main__":
    chemin = sys.argv[1]
    nom = sys.argv[2]
    try:
        upload_vers_drive(chemin, nom)
    except Exception as e:
        print(f"Echec envoi Google Drive : {e}")
    try:
        upload_vers_github(chemin, nom)
    except Exception as e:
        print(f"Echec envoi GitHub : {e}")