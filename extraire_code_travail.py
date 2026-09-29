import tarfile
import os
from tqdm import tqdm

# --- Configuration ---
NOM_ARCHIVE = "data/Freemium_legi_global_20250713-140000.tar.gz"
IDENTIFIANT_CODE_TRAVAIL = "LEGITEXT000006072050"
DOSSIER_SORTIE = "data/code_travail_xml"


def extraire_code_travail():
    # 1. Vérifier que l'archive existe bien
    if not os.path.exists(NOM_ARCHIVE):
        print(f"❌ Erreur : le fichier {NOM_ARCHIVE} n'existe pas.")
        print("Vérifie qu'il est bien dans le dossier data/")
        return

    # 2. Créer le dossier de sortie s'il n'existe pas
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)

    print(f"📦 Ouverture de l'archive : {NOM_ARCHIVE}")
    print("⏳ Cette opération peut prendre plusieurs minutes, patience...")

    compteur_extraits = 0
    compteur_total = 0

    # 3. Ouvrir l'archive en mode streaming (lecture flux, mode "r|gz")
    #    Le "|" (au lieu de ":") est important : il force le mode streaming
    #    et évite de charger toute l'archive en mémoire.
    with tarfile.open(NOM_ARCHIVE, mode="r|gz") as archive:
        # tqdm affiche une barre de progression basée sur le nombre de fichiers traités
        for membre in tqdm(archive, desc="Analyse des fichiers", unit=" fichiers"):
            compteur_total += 1

            # 4. On ne garde que les fichiers dont le CHEMIN contient l'identifiant
            #    du Code du travail
            if IDENTIFIANT_CODE_TRAVAIL in membre.name:
                # On extrait ce fichier précis dans notre dossier de sortie
                archive.extract(membre, path=DOSSIER_SORTIE)
                compteur_extraits += 1

    print("\n✅ Extraction terminée !")
    print(f"   - Fichiers analysés dans l'archive : {compteur_total}")
    print(f"   - Fichiers extraits (Code du travail) : {compteur_extraits}")
    print(f"   - Résultat disponible dans : {DOSSIER_SORTIE}/")


if __name__ == "__main__":
    extraire_code_travail()
