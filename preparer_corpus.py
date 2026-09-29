"""
Script de préparation du corpus du Code du travail.
Parcourt les fichiers XML extraits, ne garde que les articles
EN VIGUEUR appartenant aux thèmes choisis, nettoie le texte,
et génère data/corpus.json.
"""

import os
import re
import json
import xml.etree.ElementTree as ET
from tqdm import tqdm

DOSSIER_XML = "data/code_travail_xml"
FICHIER_SORTIE = "data/corpus.json"

# --- Définition de nos thèmes et de leurs plages d'articles ---
# Chaque thème est associé à une liste de préfixes de numéros d'articles.
THEMES = {
    "Contrat de travail (CDI, CDD)": ["L1221-", "L1222-", "L1223-", "L1224-",
                                        "L1225-", "L1226-", "L1227-", "L1228-",
                                        "L1229-", "L1231-1", "L1242-", "L1243-",
                                        "L1244-", "L1245-", "L1246-", "L1247-", "L1248-"],
    "Licenciement": ["L1232-", "L1233-", "L1234-", "L1235-", "L1236-", "L1237-2",
                      "L1237-3", "L1237-4", "L1237-5", "L1237-6", "L1237-7",
                      "L1237-8", "L1237-9"],
    "Durée du travail et heures supplémentaires": ["L3121-"],
    "Congés payés": ["L3141-"],
    "Rupture conventionnelle": ["L1237-11", "L1237-12", "L1237-13", "L1237-14",
                                  "L1237-15", "L1237-16", "L1237-17", "L1237-18", "L1237-19"],
    "Harcèlement et discrimination": ["L1152-", "L1153-", "L1154-", "L1155-"],
}


def nettoyer_texte(element_contenu):
    """
    Extrait tout le texte d'un élément XML (BLOC_TEXTUEL > CONTENU),
    en ignorant les balises (comme <br/>) et en normalisant les espaces.
    """
    if element_contenu is None:
        return ""
    # itertext() récupère tout le texte, même à l'intérieur des balises imbriquées
    texte_brut = " ".join(element_contenu.itertext())
    # On remplace les espaces multiples / retours à la ligne par un seul espace
    texte_propre = re.sub(r"\s+", " ", texte_brut).strip()
    return texte_propre


def identifier_theme(numero_article):
    """
    Regarde si le numéro d'article correspond à un de nos thèmes choisis.
    Retourne le nom du thème, ou None si aucun thème ne correspond.
    """
    if not numero_article:
        return None
    for theme, prefixes in THEMES.items():
        for prefixe in prefixes:
            if numero_article.startswith(prefixe):
                return theme
    return None


def extraire_section(element_contexte):
    """
    Récupère la hiérarchie des sections (Livre > Titre > Chapitre...)
    en parcourant les balises TITRE_TM imbriquées dans CONTEXTE.
    """
    if element_contexte is None:
        return ""
    titres = element_contexte.findall(".//TITRE_TM")
    chemin = [titre.text.strip() for titre in titres if titre.text]
    return " > ".join(chemin)


def parser_fichier_xml(chemin_fichier):
    """
    Parse un fichier XML d'article et retourne un dictionnaire
    avec les infos utiles, ou None si l'article n'est pas exploitable.
    """
    try:
        arbre = ET.parse(chemin_fichier)
        racine = arbre.getroot()
    except ET.ParseError:
        return None

    # Navigation dans la structure pour récupérer les métadonnées
    meta_article = racine.find(".//META_ARTICLE")
    if meta_article is None:
        return None

    etat = meta_article.findtext("ETAT", default="")
    if etat != "VIGUEUR":
        return None  # On ignore tout ce qui n'est pas en vigueur

    numero = meta_article.findtext("NUM", default="").strip()
    theme = identifier_theme(numero)
    if theme is None:
        return None  # Cet article n'appartient à aucun de nos thèmes

    identifiant = racine.findtext(".//META_COMMUN/ID", default="")
    date_debut = meta_article.findtext("DATE_DEBUT", default="")

    contexte = racine.find(".//CONTEXTE")
    section = extraire_section(contexte)

    bloc_contenu = racine.find(".//BLOC_TEXTUEL/CONTENU")
    texte = nettoyer_texte(bloc_contenu)

    if not texte:
        return None  # On ignore les articles vides (souvent juste des renvois)

    return {
        "id": identifiant,
        "numero": numero,
        "theme": theme,
        "section": section,
        "date_debut": date_debut,
        "texte": texte,
        "source": "LEGI - archive du 13/07/2025",
    }


def preparer_corpus():
    print(f"📂 Recherche des fichiers XML dans {DOSSIER_XML}...")

    # On récupère la liste de tous les fichiers .xml (peut prendre un moment)
    chemins_fichiers = []
    for racine_dossier, _, fichiers in os.walk(DOSSIER_XML):
        for fichier in fichiers:
            if fichier.endswith(".xml"):
                chemins_fichiers.append(os.path.join(racine_dossier, fichier))

    print(f"🔍 {len(chemins_fichiers)} fichiers XML trouvés. Analyse en cours...")

    corpus = []
    for chemin in tqdm(chemins_fichiers, desc="Traitement des articles", unit=" fichiers"):
        resultat = parser_fichier_xml(chemin)
        if resultat is not None:
            corpus.append(resultat)

    # Sauvegarde du corpus final au format JSON
    os.makedirs(os.path.dirname(FICHIER_SORTIE), exist_ok=True)
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    # Statistiques finales
    print(f"\n✅ Corpus généré : {FICHIER_SORTIE}")
    print(f"   - Total d'articles retenus : {len(corpus)}")

    compteur_par_theme = {}
    for article in corpus:
        compteur_par_theme[article["theme"]] = compteur_par_theme.get(article["theme"], 0) + 1

    print("\n📊 Répartition par thème :")
    for theme, nombre in compteur_par_theme.items():
        print(f"   - {theme} : {nombre} articles")


if __name__ == "__main__":
    preparer_corpus()
