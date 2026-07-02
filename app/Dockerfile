FROM python:3.12-slim-bookworm

# Utilisateur non-root : bonne pratique de sécurité (durcissement).
# Si l'appli est compromise, l'attaquant n'a pas les droits root du conteneur.
RUN groupadd -r socket && useradd -r -g socket socket

RUN apt-get update && apt-get install -y wget gnupg && \
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg && \
    echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir google-api-python-client google-auth google-auth-oauthlib requests

COPY . .

COPY client_secret_352847071573-8p7k0bkb0noqqmg2a578s7g78g4tcpmi.apps.googleusercontent.com.json /app/client_secret.json
COPY backup.sh /app/backup.sh
RUN chmod +x /app/backup.sh && mkdir -p /app/data/backups && chown -R socket:socket /app/data

RUN chown -R socket:socket /app
USER socket

EXPOSE 5000

ENV FLASK_APP=app.py

CMD ["python", "app.py"]