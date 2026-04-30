# Pathe Monitor

Script Python pour surveiller les films et événements dans les cinémas Pathé et envoyer des notifications Discord.

## Fonctionnalités

- Surveillance des films et événements
- Détection des **Avant-Premières** (avec option équipe)
- Détection des **Séances Spéciales**
- Notifications Discord avec embeds colorés
- Gestion d'état pour éviter les doublons
- **Sélection interactive de la ville** (47 villes disponibles)
- Configuration centralisée via fichier `.env.pathe`
- Utilisation de `python-dotenv` pour la gestion des variables d'environnement

## Prérequis

- Python 3.10+
- Bibliothèques : `requests`, `python-dotenv`

## Installation

1. Cloner le projet
2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Copier `.env.example` vers `.env.pathe` :
   ```bash
   cp .env.example .env.pathe
   ```
4. Configurer le webhook Discord dans `.env.pathe`

## Configuration

### Sélection de la ville

Lancez la configuration interactive pour choisir votre ville :

```bash
python pathe_monitor.py --config
```

Le script affiche la liste des villes disponibles (ex: "Paris (75)") et sauvegarde votre choix dans `.env.pathe` (variable `CINEMA_SLUGS`).

**Note :** La variable `CITY_SLUG` est conservée pour référence mais n'est plus utilisée dans le code.

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `CINEMA_SLUGS` | Slugs des cinémas séparés par virgule | Requis* |
| `WEBHOOK_URL` | URL du webhook Discord | Requis |
| `STATE_FILE` | Fichier de suivi des notifications | `pathe_movies_state.json` |
| `EVENT_COLOR` | Couleur des événements (hex) | `0x3498DB` |
| `AVP_COLOR` | Couleur des Avant-Premières (hex) | `0xFF6B00` |
| `SEANCE_SPECIALE_COLOR` | Couleur des Séances Spéciales (hex) | `0x9B59B6` |
| `COMING_SOON_COLOR` | Couleur des films à venir (hex) | `0xFFD700` |
| `AVP_FOOTER` | Texte du footer AVP | `Pathe - Avant-Premiere` |
| `SEANCE_SPECIALE_FOOTER` | Texte du footer Séance Spéciale | `Pathe - Seance Speciale` |
| `COMING_SOON_FOOTER` | Texte du footer À venir | `Pathe - Prochainement` |
| `NOTIFICATION_DELAY` | Délai entre les notifications (secondes) | `1` |

*Configuré automatiquement via `--config`

## Utilisation

### Configuration initiale
```bash
python pathe_monitor.py --config
```

### Exécution normale
```bash
python pathe_monitor.py
```

### Surveillance continue (crontab)
```bash
*/15 * * * * cd /path/to/pathe-monitor && python pathe_monitor.py
```

## Logs

Les logs sont affichés sur la sortie standard avec niveau INFO (timestamp, niveau, message). Les erreurs de lecture/écriture des fichiers sont maintenant gérées correctement.

## Structure du projet

```
pathe-monitor/
├── pathe_monitor.py      # Script principal
├── requirements.txt      # Dépendances Python
├── .env.pathe           # Configuration (non versionné)
├── .env.example         # Exemple de configuration
├── .gitignore           # Fichiers ignorés par git
├── pathe_movies_state.json  # État des notifications (non versionné)
└── README.md            # Ce fichier
```

## Tests

Un dossier `tests/` peut être ajouté pour les tests unitaires avec `pytest`.

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

MIT
