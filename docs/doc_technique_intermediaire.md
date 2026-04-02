# Documentation technique intermédiaire – Projet Socket

## 1. Contexte et objectifs

Socket est une plateforme web de gestion d’incidents de sécurité destinée à un SOC (Security Operations Center) interne.  
L’objectif est de centraliser le cycle de vie d’un incident – de la détection à la clôture – afin de remplacer les pratiques dispersées (emails, Excel, tickets génériques) et de mieux tracer les actions des analystes.

Le prototype vise à :

- offrir une interface simple pour créer, suivre et clôturer des incidents ;
- structurer la collaboration entre analystes SOC (L1, L2, L3, manager) ;
- journaliser les actions pour préparer des scénarios d’investigation et de forensic ;
- poser les bases techniques pour un déploiement conteneurisé et automatisable.

## 2. Périmètre fonctionnel (MVP)

Le MVP Socket couvre les fonctionnalités suivantes :

- Authentification utilisateur (compte analyste / compte manager).
- Gestion des incidents :
  - création d’un incident (titre, description, gravité, statut, assignation) ;
  - consultation d’une liste d’incidents (filtrage par statut/priorité) ;
  - consultation du détail d’un incident ;
  - mise à jour du statut (nouveau, en cours, remédiation, clôturé).
- Collaboration :
  - ajout de commentaires sur un incident ;
  - affectation d’un incident à un analyste.
- Traçabilité :
  - journalisation des actions importantes dans une base NoSQL (création, changement de statut, affectation, connexion).

Fonctionnalités explicitement hors périmètre pour le MVP (mais prévues dans la roadmap) :

- automatisation avancée de réponse (SOAR) ;
- corrélation de logs SIEM ;
- dashboards de KPI avancés.

## 3. Architecture cible

L’architecture retenue est de type client–serveur, avec séparation claire des responsabilités :

- **Frontend** : application web (initialement maquette HTML/CSS, puis React) utilisée par les analystes SOC.
- **Backend API** : service Node.js / Express exposant des endpoints REST pour gérer l’authentification, les incidents et les journaux.
- **Base de données relationnelle (PostgreSQL)** : stockage des données structurées (utilisateurs, incidents, commentaires, playbooks).
- **Base NoSQL (MongoDB)** : stockage des logs d’audit et événements applicatifs sous forme de documents JSON.
- **Déploiement** : conteneurs Docker orchestrés via Docker Compose dans un premier temps.

Flux simplifié :

1. L’utilisateur se connecte via l’interface Socket.
2. Le frontend envoie les requêtes au backend (API REST).
3. Le backend applique les contrôles d’accès puis lit/écrit dans PostgreSQL.
4. Le backend enregistre en parallèle des événements de journalisation dans MongoDB.
5. Le résultat est renvoyé au frontend (liste d’incidents, détail, confirmation d’action…).

## 4. Choix technologiques

### Frontend

- **Technologie visée** : React.
- Motivation :
  - écosystème riche pour construire des interfaces de type dashboard ;
  - composants réutilisables (liste d’incidents, carte KPI, formulaire d’édition) ;
  - possibilité d’intégrer plus tard des graphiques (KPI SOC).

Pour l’instant, une maquette statique HTML/CSS (`frontend/socket-dashboard.html`) sert de base visuelle et de support de discussion avec les encadrants.

### Backend

- **Technologie** : Node.js + Express.
- Motivation :
  - simplicité de mise en place d’une API REST ;
  - nombreuses librairies pour la sécurité (auth, validation des entrées, headers de sécurité) ;
  - intégration aisée avec PostgreSQL et MongoDB via des librairies Node.

### Base relationnelle

- **SGBD** : PostgreSQL.
- Rôle :
  - stocker les entités structurées : utilisateurs, rôles, incidents, commentaires, playbooks.
- Avantages :
  - robustesse, transactions, intégrité référentielle ;
  - adapter pour requêtes complexes (filtrage incidents, recherche par champ).

### Base NoSQL

- **SGBD** : MongoDB.
- Rôle :
  - stocker les logs d’audit applicatifs (actions utilisateurs, événements de sécurité) ;
  - conserver des documents JSON souples, avec des structures potentiellement variables selon le type d’événement.

Exemple de document d’audit prévu :

```json
{
  "timestamp": "2026-04-02T15:00:00Z",
  "userId": 12,
  "action": "INCIDENT_STATUS_UPDATED",
  "incidentId": 45,
  "details": {
    "oldStatus": "new",
    "newStatus": "in_progress"
  },
  "sourceIp": "192.168.1.10"
}
```

### Déploiement et outillage

- **Conteneurisation** : Docker + Docker Compose.
  - Services prévus : `frontend`, `backend`, `postgres`, `mongo`, puis éventuellement un reverse proxy.
- **CI/CD** : GitHub Actions (à introduire dans une phase ultérieure).
  - Objectif : lint, tests, scans de sécurité de base et build des conteneurs.

## 5. Modèle de données (prévisionnel)

### Principales tables PostgreSQL

- `users` :
  - `id`, `email`, `password_hash`, `role`, `created_at`, `updated_at`.
- `incidents` :
  - `id`, `title`, `description`, `severity`, `status`, `created_at`, `updated_at`, `created_by`, `assigned_to`.
- `comments` :
  - `id`, `incident_id`, `author_id`, `content`, `created_at`.
- `playbooks` (prévu) :
  - `id`, `name`, `incident_type`, `description`.
- `playbook_steps` (prévu) :
  - `id`, `playbook_id`, `step_order`, `label`.

Ce modèle sera affiné au fur et à mesure de l’avancement (ajout de champs techniques, contraintes, index).

## 6. Exigences de sécurité (version intermédiaire)

Dès la conception, Socket doit prendre en compte les points suivants :

- **Authentification**
  - authentification obligatoire pour toute action sur les incidents ;
  - stockage des mots de passe sous forme hachée (ex : bcrypt) ;
  - sessions ou tokens sécurisés.

- **Autorisations**
  - gestion de rôles (analyste, lead, admin) ;
  - contrôle d’accès sur les routes (ex : seuls certains rôles peuvent clôturer un incident ou gérer les utilisateurs).

- **Validation des données**
  - validation systématique des entrées côté backend (type, longueur, format) ;
  - prévention des injections et XSS.

- **Journalisation**
  - journalisation des opérations sensibles (login, création/modification d’incident, changement de statut) dans MongoDB ;
  - conservation d’horodatages précis pour les futurs scénarios forensic.

- **Architecture**
  - séparation des services (frontend, backend, bases) ;
  - bases de données non exposées directement à l’extérieur (accès via backend uniquement) ;
  - utilisation ultérieure d’un reverse proxy pour gérer HTTPS et certains headers de sécurité.

## 7. Organisation du dépôt

Organisation cible du dépôt Git :

```text
Projet-SOCket/
├── README.md
├── frontend/
│   └── socket-dashboard.html
├── backend/          (à créer)
│   ├── src/
│   └── package.json
├── docs/
│   └── doc_technique_intermediaire.md
└── .github/
    └── workflows/    (CI/CD à venir)
```

Pour le moment, seules les parties `frontend/`, `docs/` et `README.md` sont en place. Les dossiers `backend/` et `.github/` seront ajoutés au fur et à mesure.

## 8. Prochaines étapes

À partir de cette base, les étapes techniques prévues sont :

1. Implémenter le backend Node/Express (routes incidents et auth basique).
2. Brancher PostgreSQL pour persister les incidents et les utilisateurs.
3. Mettre en place MongoDB pour les logs d’audit.
4. Conteneuriser le backend et les bases avec Docker Compose.
5. Migrer l’interface statique vers un vrai frontend (React) ou améliorer la maquette.
6. Renforcer la sécurité (validation, RBAC, durcissement) et préparer les scénarios d’audit / forensic.

Cette documentation sera enrichie au fur et à mesure (schémas détaillés, endpoints de l’API, scripts de déploiement, etc.).