# YeastarPBX iCal Sync

Interface web de gestion automatique des statuts de présence Yeastar en fonction de plannings/disponibilités importé au format iCal.

## Fonctionnalités

- **Configuration API Yeastar** : Connexion sécurisée à votre PBX avec chiffrement des credentials
- **Dashboard en temps réel** : Visualisation des extensions et leurs statuts actuels
- **Gestion de planning** : Import CSV/JSON et saisie manuelle des créneaux de disponibilité
- **Synchronisation automatique** : Mise à jour automatique des statuts selon les plannings (intervalle configurable)
- **Overrides manuels** : Possibilité de forcer un statut temporairement
- **Journalisation** : Historique complet de tous les changements de statut

## Prérequis

- Python 3.8 ou supérieur
- Accès à l'API Yeastar avec Client ID et Client Secret
- Système d'exploitation : Windows, Linux ou macOS

## Installation

### 1. Cloner ou télécharger le projet

```bash
cd /chemin/vers/Yeastar_status
```

### 2. Créer un environnement virtuel Python

**Windows :**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS :**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer l'application

**Copiez et éditez le fichier .env :**

```bash
cp .env.example .env
nano .env  # ou vim, ou tout autre éditeur
```

**Configurez au minimum :**

**API Yeastar :**
- `YEASTAR_PBX_URL` : URL de votre PBX (ex: https://xxx.xxx.xxx.xxx:8088)
- `YEASTAR_CLIENT_ID` : Votre Client ID Yeastar
- `YEASTAR_CLIENT_SECRET` : Votre Client Secret Yeastar

**Base de données (choisissez UNE option) :**

*Option SQLite (simple) :*
```bash
# Pas besoin de configurer, c'est le défaut
# Ou explicitement :
DB_TYPE=sqlite
```

*Option MariaDB/MySQL (recommandé) :*
```bash
DB_TYPE=mysql
DB_HOST=YOUR_URL
DB_PORT=3306
DB_NAME=yeastar
DB_USER=yeastar_user
DB_PASSWORD=votre_mot_de_passe
```

*Option PostgreSQL :*
```bash
DB_TYPE=postgresql
DB_HOST=YOUR_URL
DB_PORT=5432
DB_NAME=yeastar
DB_USER=yeastar_user
DB_PASSWORD=votre_mot_de_passe
```

**Toute la configuration se fait dans .env**

## Démarrage

### Mode développement

```bash
python run.py
```

L'application sera accessible sur `http://localhost:5000`

### Mode production (Linux)

Pour un déploiement en production, utilisez un serveur WSGI comme Gunicorn :

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### Déploiement avec systemd (Linux)

Créez un fichier `/etc/systemd/system/yeastar-manager.service` :

```ini
[Unit]
Description=Yeastar Presence Manager
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/yeastar-manager
Environment="PATH=/opt/yeastar-manager/venv/bin"
ExecStart=/opt/yeastar-manager/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Activez et démarrez le service :

```bash
sudo systemctl enable yeastar-manager
sudo systemctl start yeastar-manager
sudo systemctl status yeastar-manager
```

## Utilisation

### 1. Démarrer l'application

Après avoir configuré le `.env`, démarrez l'application :

```bash
python run.py  # ou via systemd
```

### 2. Accéder à l'interface

Ouvrez votre navigateur : `http://localhost:5000` ou `http://<ip-du-serveur>:5000`

### 3. Synchroniser les extensions

- Dans le Dashboard, cliquez sur "🔄 Rafraîchir depuis API"
- Les extensions sont importées automatiquement depuis votre PBX
- Elles s'affichent dans le tableau avec leurs statuts actuels

### 4. Configurer les plannings
   - **Option A - Synchronisation iCal/iPlanning** :
     - Cliquez sur "Planning" dans le menu
     - Sélectionnez une extension
     - Cliquez sur "Synchroniser iCal"
     - Entrez votre token iPlanning (format: `https://Your_URL/?u=VOTRE_TOKEN`)
     - Les plannings se synchronisent automatiquement toutes les minutes

   - **Option B - Import CSV/JSON** :
     - Cliquez sur "Planning" dans le menu
     - Cliquez sur "Importer planning"
     - Uploadez votre fichier CSV ou JSON (voir exemples ci-dessous)

   - **Option C - Saisie manuelle** :
     - Cliquez sur "Planning" dans le menu
     - Sélectionnez une extension
     - Cliquez sur "Ajouter un créneau"
     - Définissez jour, horaires et statut

5. **Activer le planning automatique** :
   - Dans le Dashboard, activez le toggle "Planning" pour chaque extension
   - Le système synchronisera automatiquement les statuts selon les plannings (toutes les 5 minutes par défaut)

### 5. Fonctionnalité Override

Le toggle "Override" permet d'ignorer temporairement le planning automatique :
- **Activé** : Le statut actuel est conservé, le planning est ignoré
- **Désactivé** : Le planning automatique s'applique normalement

## Format d'import de planning

### CSV

```csv
extension,day,start_time,end_time,status
2000,lundi,08:00,12:00,available
2000,lundi,14:00,18:00,available
2000,mardi,08:00,12:00,available
2001,monday,09:00,17:00,available
```

**Colonnes :**
- `extension` : Numéro d'extension
- `day` : Jour (français : lundi-dimanche, anglais : monday-sunday)
- `start_time` : Heure de début (HH:MM)
- `end_time` : Heure de fin (HH:MM)
- `status` : Statut (optionnel, défaut : `available`)

### JSON

```json
[
  {
    "extension": "2000",
    "schedules": [
      {"day": "monday", "start": "08:00", "end": "12:00", "status": "available"},
      {"day": "monday", "start": "14:00", "end": "18:00", "status": "available"},
      {"day": "tuesday", "start": "08:00", "end": "17:00", "status": "available"}
    ]
  },
  {
    "extension": "2001",
    "schedules": [
      {"day": "monday", "start": "09:00", "end": "17:00", "status": "available"}
    ]
  }
]
```

## Statuts disponibles

- `available` : Disponible
- `away` : Absent
- `do_not_disturb` : Ne pas déranger (DND)
- `business_trip` : Déplacement professionnel
- `face_a_face_pedagogique` : Face à face pédagogique
- `off_work` : Hors service

## Utilisation

### Synchronisation automatique

Le moteur de synchronisation s'exécute automatiquement en arrière-plan selon l'intervalle configuré (défaut : 5 minutes).

**Logique :**
- Vérifie chaque extension avec planning activé
- Si l'heure actuelle correspond à un créneau du planning → applique le statut du créneau
- Si hors planning → applique le statut par défaut (configurable, défaut : `do_not_disturb`)
- Les overrides manuels sont prioritaires sur le planning

### Overrides manuels

Pour forcer temporairement un statut :
1. Dans le Dashboard, cliquez sur "Override" pour une extension
2. Sélectionnez le statut souhaité
3. (Optionnel) Définissez une durée en heures
4. (Optionnel) Ajoutez une raison

L'override sera automatiquement supprimé après expiration.

### API REST

L'application expose également une API REST :

- `GET /api/extensions` : Liste toutes les extensions
- `GET /api/extensions/<id>` : Détails d'une extension
- `GET /api/logs` : Récupère les logs (pagination supportée)
- `GET /api/stats` : Statistiques globales

## Certificats SSL auto-signés

Si votre PBX utilise un certificat SSL auto-signé (typique pour les installations locales), l'application gère automatiquement la connexion en désactivant la vérification SSL pour les requêtes API.

**Note de sécurité :** Pour la production, il est recommandé d'utiliser des certificats SSL valides.

## Dépannage

### Erreur de connexion à l'API

- Vérifiez que l'URL du PBX est correcte
- Vérifiez que le Client ID et Secret sont valides
- Vérifiez que le PBX est accessible depuis le serveur
- Consultez les logs dans le Dashboard

### Les statuts ne se mettent pas à jour

- Vérifiez que le planning est activé pour l'extension (toggle dans Dashboard)
- Vérifiez que des créneaux sont définis dans le planning
- Forcez une synchronisation avec "Synchroniser maintenant"
- Consultez les logs pour voir les erreurs éventuelles

**Attention :** Ceci supprimera toutes les données (plannings, logs, etc.)

## Structure du projet

```
yeastar-presence-manager/
├── app/
│   ├── __init__.py              # Factory Flask et initialisation
│   ├── config.py                # Configuration de l'application
│   ├── models.py                # Modèles de base de données
│   ├── routes/
│   │   ├── dashboard.py         # Routes du dashboard
│   │   ├── config.py            # Routes de configuration
│   │   ├── planning.py          # Routes de gestion des plannings
│   │   └── api.py               # Routes API REST
│   ├── services/
│   │   ├── yeastar_api.py       # Client API Yeastar
│   │   ├── scheduler.py         # Moteur de synchronisation
│   │   └── planning_parser.py   # Parser CSV/JSON
│   ├── templates/               # Templates HTML
│   └── static/                  # Fichiers statiques (CSS, JS)
├── instance/
│   ├── app.db                   # Base de données SQLite
│   ├── secret.key               # Clé de chiffrement
│   └── uploads/                 # Fichiers uploadés
├── requirements.txt             # Dépendances Python
├── run.py                       # Point d'entrée
├── .env.example                 # Exemple de configuration
└── README.md                    # Ce fichier
```

## Sécurité

- Les Client Secret sont chiffrés avant d'être stockés en base de données (Fernet)
- La clé de chiffrement est générée automatiquement dans `instance/secret.key`
- **Important :** Protégez l'accès à l'application (reverse proxy avec authentification, firewall, etc.)

## Déploiement sur LXC Proxmox avec base de données distante

### Configuration avec MariaDB/MySQL distant (xxx.xxx.xxx.xxx)

1. **Préparer la base de données MariaDB** (via phpMyAdmin ou CLI) :
```sql
CREATE DATABASE yeastar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'yeastar_user'@'%' IDENTIFIED BY 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON yeastar.* TO 'yeastar_user'@'%';
FLUSH PRIVILEGES;
```

**Note :** Vérifiez que MariaDB accepte les connexions distantes (bind-address dans `/etc/mysql/mariadb.conf.d/50-server.cnf`).

2. **Installer dans le container LXC** :
```bash
# Installer Python et pip
apt update && apt install python3 python3-venv python3-pip git -y

# Cloner le projet
cd /opt
git clone <votre-repo-git> yeastar-manager
cd yeastar-manager

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances + MariaDB driver + Gunicorn
pip install -r requirements.txt
pip install PyMySQL gunicorn
```

3. **Créer et configurer le fichier .env** :
```bash
cp .env.example .env
nano .env
```

**Configurez les paramètres suivants :**
```bash
# API Yeastar
YEASTAR_PBX_URL=https://votre-pbx:8088
YEASTAR_CLIENT_ID=votre_client_id
YEASTAR_CLIENT_SECRET=votre_client_secret

# Base de données MariaDB distante (configuration propre, ligne par ligne)
DB_TYPE=mysql
DB_HOST=xxx.xxx.xxx.xxx
DB_PORT=3306
DB_NAME=yeastar
DB_USER=yeastar_user
DB_PASSWORD=votre_mot_de_passe

# Clé secrète Flask (générer avec: python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=votre-cle-secrete-unique

# Optionnel
SYNC_INTERVAL_MINUTES=5
DEFAULT_STATUS=available
```

4. **Tester la connexion à la base de données** :
```bash
python3 -c "from app import create_app; app = create_app(); print('✓ Connexion DB OK')"
```

5. **Créer le service systemd** :
```bash
nano /etc/systemd/system/yeastar-manager.service
```

```ini
[Unit]
Description=Yeastar Presence Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/yeastar-manager
Environment="PATH=/opt/yeastar-manager/venv/bin"
ExecStart=/opt/yeastar-manager/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

6. **Démarrer le service** :
```bash
systemctl daemon-reload
systemctl enable yeastar-manager
systemctl start yeastar-manager
systemctl status yeastar-manager
```

7. **Accéder à l'interface web** :
```
http://<ip-du-lxc>:5000
```

L'application est prête ! Synchronisez les extensions et configurez les plannings via l'interface.

8. **Vérifier les logs** (en cas de problème) :
```bash
journalctl -u yeastar-manager -f
```

### Configuration avec PostgreSQL distant

Similaire à MariaDB, mais :
- Installer : `pip install psycopg2-binary`
- DATABASE_URL dans .env : `postgresql://user:password@YOUR_URL:5432/yeastar`

### Mode SQLite (sans base distante)

Si vous n'avez pas de serveur MariaDB/PostgreSQL :
```bash
# Dans .env, utilisez SQLite
DATABASE_URL=sqlite:///instance/app.db
```

---

# README - English Version


Comming Soon

# License

Copyright (c) 2025 Gaetan PAVIOT

Licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

- ✅ Share and adapt the code
- ❌ Commercial use prohibited without permission
- 📝 Attribution required
- 🔄 Share-alike: modifications must use the same license

See [LICENSE](LICENSE) for full details.

## Licence

Copyright (c) 2025 Gaetan PAVIOT

Ce projet est sous licence **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.

**Vous êtes libre de :**
- Partager et redistribuer le code
- Adapter et modifier le code

**Sous les conditions suivantes :**
- **Attribution** : Vous devez mentionner l'auteur original (Gaetan PAVIOT)
- **Usage non commercial** : Utilisation commerciale interdite sans autorisation
- **Partage dans les mêmes conditions** : Vos modifications doivent utiliser la même licence

Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Auteur

**Gaetan PAVIOT**
- Développé pour le CFA MFEO
- Contact : contact@gaetan-paviot.fr