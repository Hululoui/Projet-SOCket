# SOCket

Plateforme de gestion d'incidents de sécurité (SOC) développée dans le cadre du projet fil rouge de Bachelor 3 Cybersécurité — Ynov.

## Objectif

SOCket a pour but de centraliser le suivi des incidents de sécurité depuis leur détection jusqu'à leur clôture, en remplaçant les pratiques dispersées (emails, tableurs, tickets génériques) par une plateforme unique, avec traçabilité complète des actions.

## État actuel du projet

Le projet a démarré avec un cadrage technique visant une stack React / Node.js / PostgreSQL / MongoDB (voir `docs/doc_technique_intermediaire.md` pour l'historique de cette réflexion).

Face à une contrainte de temps forte et à la réalisation en solo, le choix a été fait de prioriser un **prototype fonctionnel de bout en bout** plutôt qu'une architecture multi-services non finalisée. La stack a donc été simplifiée :

- **Framework web** : Python / Flask (au lieu de Node.js / Express)
- **Base de données** : SQLite (au lieu de PostgreSQL) — suffisante pour un prototype, sans serveur de base séparé à administrer
- **Logs d'audit** : fichier JSON Lines (`logs.jsonl`), qui illustre une approche NoSQL simple pour les événements de traçabilité (au lieu de MongoDB)

Ce choix permet de disposer d'une application **réellement fonctionnelle et testée**, plutôt que d'un squelette multi-technologies inachevé.

## Fonctionnalités implémentées

- **Authentification sécurisée** : comptes analystes, mots de passe hashés (PBKDF2 via `werkzeug.security`), sessions protégées
- **Gestion du cycle de vie des incidents** : création → détecté → qualifié → en traitement → clôturé
- **Contrôle d'accès** : toutes les routes sensibles nécessitent une authentification
- **Journalisation de sécurité** : traçabilité de chaque action sensible (connexion, création/modification d'incident) avec horodatage, consultable via l'interface (`/logs`)
- **Protection contre l'injection SQL** : toutes les requêtes utilisent des paramètres liés (`?`), jamais de concaténation de chaînes

## Structure du dépôt
SOCket/
├── README.md
├── .gitignore
├── app/
│   ├── app.py              # Application Flask (routes, logique métier, base de données)
│   └── requirements.txt    # Dépendances Python
└── docs/
└── doc_technique_intermediaire.md   # Cadrage technique initial (stack cible React/Node)

## Lancer le projet

```bash
cd app
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

L'application est accessible sur [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Sécurité — principes appliqués

- Mots de passe hashés, jamais stockés en clair
- Requêtes SQL paramétrées (protection contre l'injection SQL)
- Authentification obligatoire sur toutes les routes sensibles
- Traçabilité complète des actions (horodatage, utilisateur, type d'événement)

## Évolutions possibles

- Migration vers PostgreSQL / MongoDB si le projet devait être industrialisé (cadrage initial conservé dans `docs/`)
- Conteneurisation Docker
- Séparation des rôles (analyste / administrateur)
- Chiffrement TLS/HTTPS

## Auteur

COMTE Supreet — Projet Fil Rouge, Bachelor 3 Cybersécurité, Ynov.