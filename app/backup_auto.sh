#!/bin/bash

# Ce script tourne en boucle et fait une sauvegarde toutes les 6 heures
while true; do
    DATE=$(date +%Y%m%d_%H%M%S)
    DOSSIER="/app/data/backups/$DATE"
    mkdir -p "$DOSSIER"
    cp /app/socket.db "$DOSSIER/socket.db"
    echo "[$DATE] Sauvegarde SQLite effectuée dans $DOSSIER"
    sleep 21600
done