import pandas as pd
from pathlib import Path
import logging


# ============================================================
# Configuration
# ============================================================


BASE_DIR = Path(__file__).resolve().parents[2]


CLEAN_FILE = (
    BASE_DIR /
    "data" /
    "clean" /
    "aqi_clean.csv"
)



logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)



# ============================================================
# Validation
# ============================================================


REQUIRED_COLUMNS = [

    "city",
    "country",
    "latitude",
    "longitude",
    "timestamp",
    "aqi"

]



def validate():


    if not CLEAN_FILE.exists():

        raise Exception(
            "Le fichier clean n'existe pas"
        )


    df = pd.read_csv(
        CLEAN_FILE
    )


    logging.info(
        f"{len(df)} lignes trouvées"
    )



    # colonnes

    for column in REQUIRED_COLUMNS:

        if column not in df.columns:

            raise Exception(
                f"Colonne absente : {column}"
            )


    logging.info(
        "Colonnes OK"
    )



    # doublons

    duplicates = df.duplicated(
        subset=[
            "city",
            "timestamp"
        ]
    ).sum()


    if duplicates > 0:

        raise Exception(
            f"{duplicates} doublons trouvés"
        )


    logging.info(
        "Aucun doublon"
    )



    # villes

    cities = df["city"].unique()


    logging.info(
        f"{len(cities)} villes détectées"
    )


    print(
        cities
    )


    logging.info(
        "Validation terminée avec succès"
    )



if __name__ == "__main__":

    validate()
