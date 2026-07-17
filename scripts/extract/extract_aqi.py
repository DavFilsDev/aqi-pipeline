import json
from pathlib import Path


# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fichiers utilisés
CITIES_FILE = PROJECT_ROOT / "data" / "cities.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_cities() -> list[dict]:
    """
    Charge la liste des villes depuis data/cities.json.
    """
    with open(CITIES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    cities = load_cities()

    print(f"{len(cities)} villes trouvées :")

    for city in cities:
        print(
            f"- {city['name']} ({city['country']}) "
            f"[{city['latitude']}, {city['longitude']}]"
        )


if __name__ == "__main__":
    main()