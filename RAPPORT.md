# Rapport de projet — Pipeline AQI

## Méthode de travail

Équipe de 5, travail en parallèle sur des dossiers séparés (voir `TASK.md` pour le
détail des interfaces partagées) afin de ne pas se bloquer mutuellement :
- Coordination mixte : points d'étape réguliers en équipe + échanges asynchrones
  (Discord/WhatsApp) le reste du temps pour débloquer rapidement les questions
  d'interface (format des fichiers `data/raw/`, colonnes du CSV clean, schéma SQL).
- Un fichier partagé, `data/cities.json`, comme unique source de vérité pour la
  liste des villes — personne ne la duplique dans son propre code.
- Développement sur des branches `feature/<nom>-<tâche>`, fusionnées dans `main`
  via pull request.
- Projet mené du 16 au 31 juillet 2026 (historique Git), avec un socle
  fonctionnel posé en 2-3 jours puis un backfill + une collecte en continu
  poursuivis sur la durée pour accumuler ~5 mois de données historiques.

## Répartition des tâches

| Tâche | Membre | Périmètre |
|---|---|---|
| 1 — Orchestration & CI/CD | David | `.github/workflows/` (pipeline horaire + backfill manuel) |
| 2 — Extraction API | Fenohasina | `scripts/extract/`, `data/cities.json` |
| 3 — Transformation | Sarobidy | `scripts/transform/build_clean.py` |
| 4 — Data warehouse | Valisoa | `sql/`, `scripts/load/` |
| 5 — Qualité, docs, vidéo | Zinedis | `validate_clean.py`, `README.md`, ce rapport, la vidéo |

Chacun a testé sa propre partie avant intégration (commandes de test listées dans
`TASK.md`), ce qui a limité les conflits d'interface une fois les 5 parties
assemblées.

## Difficultés rencontrées et solutions

### 1. Migration Airflow/Docker → GitHub Actions
Le projet a démarré avec Airflow en local via Docker Compose (voir l'historique Git :
Dockerfile Airflow, `docker-compose`, DAG `dags/hello_etl.py`), avec un déploiement
prévu sur une VM Oracle Cloud (architecture initiale mentionnée dans le sujet).
Deux difficultés distinctes ont motivé l'abandon de cette voie :
- La création du compte Oracle Cloud n'a pas abouti (le compte n'a pas pu être
  activé), rendant impossible le déploiement d'une VM pour héberger Airflow.
- Un vrai problème de résolution DNS a par ailleurs été rencontré avec Docker
  **[À COMPLÉTER : détail exact à récupérer auprès de Fenohasina/David — quel
  conteneur ne résolvait pas quel nom d'hôte, et dans quel contexte]**.

Ces deux blocages ont conduit l'équipe à basculer vers GitHub Actions : plus de
serveur à provisionner, pas de dépendance à l'environnement Docker de chacun, et
l'historique des runs sert directement de preuve d'exécution automatique pour le
rendu. Les dossiers `dags/`, `logs/`, `plugins/` restent dans le dépôt comme trace
de cette étape mais ne sont plus utilisés.

### 2. Bug `execute_values(..., fetch=True)` dans le chargement de l'entrepôt
Signalé et corrigé par Valisoa (Task 4) : sans `fetch=True`, la clause `RETURNING`
d'un batch `execute_values` ne remonte que la dernière page de résultats, pas
l'ensemble — ce qui provoquait un `KeyError` lors du mapping des IDs générés vers
les lignes du CSV. Le paramètre `fetch=True` force la récupération de toutes les
pages.

### 3. CSV clean périmé sans qu'aucune alerte ne se déclenche
En reprenant `validate_clean.py` (Task 5) pour y ajouter les contrôles manquants
(nulls, ordre chronologique, une ligne par ville+heure — la version initiale ne
vérifiait que les colonnes et les doublons), on a découvert que `data/clean/aqi_clean.csv`
n'avait pas été reconstruit depuis le 25/07 alors que les fichiers `data/raw/`
allaient jusqu'au 31/07. La cause était un bug silencieux dans `build_clean.py` :
`pd.to_datetime()` infère un seul format de date à partir de la première valeur de
la colonne ; les timestamps des runs horaires réels (avec microsecondes, ex.
`...T19:24:00.689362+00:00`) ne correspondaient pas au format des timestamps de
backfill (heure pile, ex. `...T04:00:00+00:00`) et étaient donc silencieusement
convertis en `NaT` puis supprimés — sans erreur, sans log. Corrigé en passant
`format="mixed"` à `pd.to_datetime()`. Comme la validation d'origine ne vérifiait
pas la fraîcheur des données, le pipeline continuait de "réussir" (coche verte sur
GitHub Actions) tout en ne progressant plus réellement depuis plusieurs jours.

### 4. Lignes avec mesures nulles
Certains appels à l'API historique d'OpenWeather renvoient un `200 OK` avec une
`list` vide (aucune mesure disponible pour cette heure) plutôt qu'une erreur.
`build_clean.py` gardait ces appels comme des lignes avec `aqi`/`pm25`/etc. à
`null`, ce qui viole le contrat de données (pas de nulls dans les colonnes
requises). Corrigé en excluant ces lignes explicitement : une heure sans mesure
est un trou documenté dans le README, pas une ligne vide dans le CSV.

### 5. `timestamp_utc` non arrondi à l'heure
Dans le même mouvement, `build_clean.py` écrivait l'heure exacte de l'appel API
(ex. `19:24:00`) au lieu de l'heure arrondie utilisée pour le regroupement,
cassant la règle "une ligne par ville+heure". Corrigé en réutilisant la colonne
`hour` (déjà calculée pour le dédoublonnage) comme valeur de sortie de
`timestamp_utc`.

### 6. Trous d'exécution récents du pipeline horaire
L'analyse de `data/raw/` montre 882 heures sans aucun fichier brut (98 par ville,
identiques sur les 9 villes), concentrées à partir du 25/07 — dont une coupure
d'environ 25h le 25-26/07. Comme le motif est identique sur toutes les villes, la
cause est côté exécution du workflow (`pipeline.yml`), pas côté API.
**[À COMPLÉTER : cause exacte à vérifier avec David dans l'historique Actions —
runners indisponibles, dépassement de temps, conflit de commit non résolu par le
retry, etc.]**

## Choix techniques justifiés

Voir `ARCHITECTURE.md` pour le tableau complet (orchestrateur, stockage,
warehouse, déploiement). En résumé : GitHub Actions pour un orchestrateur sans
serveur à maintenir, `data/raw/` et `data/clean/` versionnés dans Git faute
d'autre stockage persistant sur des runners éphémères, Neon (Postgres serverless)
comme entrepôt pour rester accessible sans hébergement dédié.