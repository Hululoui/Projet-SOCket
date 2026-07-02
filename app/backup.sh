#!/bin/bash

# Ce script sauvegarde la base SQLite et les données MongoDB de SOCket
# À lancer depuis la racine du projet, ex : docker exec socket-app bash /app/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
DOSSIER_SAUVEGARDE="/app/data/backups/$DATE"

mkdir -p "$DOSSIER_SAUVEGARDE"

# Sauvegarde de la base SQLite (comptes, incidents)
cp /app/data/socket.db "$DOSSIER_SAUVEGARDE/socket.db"

# Sauvegarde de MongoDB (les logs de sécurité)
mongodump --uri="$MONGO_URI" --out="$DOSSIER_SAUVEGARDE/mongo"

echo "Sauvegarde terminée : $DOSSIER_SAUVEGARDE"
python3 /app/upload_backup.py "$DOSSIER_SAUVEGARDE/socket.db" "socket_$DATE.db"