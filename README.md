# WebService Tester

Outil de test de webservices avec interface graphique, similaire à Postben.
Aucune dépendance externe — fonctionne avec Python 3 stdlib uniquement.

## Prérequis

- Python 3.6+

Vérifiez votre version :

```bash
python3 --version
```

## Installation

```bash
git clone <url-du-repo>
cd postben
```

Ou sans git, téléchargez et décompressez l'archive, puis :

```bash
cd postben
```

C'est tout — pas de `pip install`, pas de `node_modules`.

## Lancement

**Au premier plan** (s'arrête à la fermeture du terminal) :

```bash
python3 app.py
```

**En arrière-plan avec `nohup`** (persiste après fermeture du terminal) :

```bash
nohup python3 app.py > logs.txt 2>&1 &
echo $! > app.pid
```

Les logs sont écrits dans `logs.txt`. Le PID est sauvegardé dans `app.pid`.

Ouvrez ensuite **http://localhost:5000** dans votre navigateur.

Pour utiliser un port différent, modifiez la ligne `port = 5000` dans `app.py`.

## Arrêt

Si lancé au premier plan :

```bash
Ctrl+C
```

Si lancé avec `nohup` :

```bash
kill $(cat app.pid)
```

Ou sans le fichier PID :

```bash
pkill -f "python3 app.py"
```

## Consulter les logs

```bash
tail -f logs.txt
```

## Docker

### Prérequis

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (inclus avec Docker Desktop)

### Lancement avec Docker Compose (recommandé)

```bash
docker compose up -d
```

L'interface est disponible sur **http://localhost:5000**.  
Les données (collections, historique, environnements) sont persistées dans le dossier `./data` de la machine hôte.

### Arrêt

```bash
docker compose down
```

### Logs

```bash
docker compose logs -f
```

### Changer le port

Modifiez le mapping dans `docker-compose.yml` :

```yaml
ports:
  - "8080:5000"   # accessible sur http://localhost:8080
```

### Sans Docker Compose

```bash
# Build
docker build -t wstester .

# Lancement
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data --name wstester wstester

# Arrêt
docker stop wstester && docker rm wstester
```

## Structure du projet

```
postben/
├── app.py               # Serveur HTTP + proxy de requêtes
├── Dockerfile
├── docker-compose.yml
├── static/
│   └── index.html       # Interface graphique (HTML/CSS/JS)
└── data/                # Données persistantes (créé automatiquement)
    ├── collections.json
    ├── history.json
    └── environments.json
```

## Fonctionnalités

### Requêtes HTTP
- Méthodes : GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- Corps : Raw/JSON, Form URL-encoded, JSON clé/valeur
- Authentification : Bearer Token, Basic Auth
- Paramètres et en-têtes activables/désactivables

### Réponse
- Coloration syntaxique JSON
- Onglets Corps / En-têtes
- Temps de réponse, taille, code HTTP
- Copier dans le presse-papier, télécharger

### Collections
Sauvegardez vos requêtes par collection et rechargez-les en un clic depuis la barre latérale.

### Historique
Les 100 dernières requêtes sont conservées automatiquement.

### Environnements
Définissez des variables réutilisables (`{{BASE_URL}}`, `{{TOKEN}}`...) et switchez entre environnements (Local, Staging, Production).

