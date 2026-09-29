import json
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

FICHIER_CORPUS = "data/corpus.json"
DOSSIER_CHROMA = "chroma_db"
NOM_COLLECTION = "code_travail"
NOM_MODELE_EMBEDDING = "paraphrase-multilingual-mpnet-base-v2"


def charger_corpus():
    print(f"📂 Chargement de {FICHIER_CORPUS}...")
    with open(FICHIER_CORPUS, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    print(f"✅ {len(corpus)} articles charges.")
    return corpus


def construire_texte_embedding(article):
    """
    Construit le texte qui sera transforme en vecteur.
    Prefixe minimal (juste le theme, court) pour donner un peu
    de contexte SANS diluer le signal avec la hierarchie complete
    de section (trop longue et souvent repetee a l'identique
    sur plusieurs articles, ce qui polluait la recherche).
    """
    return f"{article['theme']}. {article['texte']}"



def indexer():
    corpus = charger_corpus()

    # 1. Charger le modele d'embedding
    print(f"🧠 Chargement du modele d'embedding : {NOM_MODELE_EMBEDDING}...")
    print("   (telechargement possible la premiere fois, patience...)")
    modele = SentenceTransformer(NOM_MODELE_EMBEDDING)

    # 2. Preparer les listes pour ChromaDB
    ids = []
    documents = []
    metadonnees = []

    for article in corpus:
        ids.append(article["id"])
        documents.append(construire_texte_embedding(article))
        metadonnees.append({
            "numero": article["numero"],
            "theme": article["theme"],
            "section": article["section"],
            "date_debut": article["date_debut"],
            "source": article["source"],
            "texte_original": article["texte"],  # utile pour l'affichage final
        })

    # 3. Encoder tous les textes en vecteurs normalises
    print(f"🔢 Encodage de {len(documents)} articles en vecteurs...")
    embeddings = modele.encode(
        documents,
        show_progress_bar=True,
        normalize_embeddings=True,  # OBLIGATOIRE : voir cours section 3
    )

    # 4. Creer / ouvrir la base ChromaDB persistante
    print(f"💾 Ecriture dans ChromaDB ({DOSSIER_CHROMA})...")
    client = chromadb.PersistentClient(path=DOSSIER_CHROMA)

    # On supprime la collection si elle existe deja (reindexation volontaire)
    try:
        client.delete_collection(NOM_COLLECTION)
        print("   (ancienne collection supprimee, reindexation complete)")
    except Exception:
        pass  # la collection n'existait pas encore, pas grave

    collection = client.create_collection(
        name=NOM_COLLECTION,
        metadata={"modele_embedding": NOM_MODELE_EMBEDDING},  # tracabilite du modele
    )

    # 5. Ajouter les documents (ChromaDB accepte des listes, par lots si besoin)
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadonnees,
    )

    print(f"\n✅ Indexation terminee !")
    print(f"   - {collection.count()} articles indexes dans la collection '{NOM_COLLECTION}'")
    print(f"   - Modele d'embedding trace : {NOM_MODELE_EMBEDDING}")
    print(f"   - Base persistee dans : {DOSSIER_CHROMA}/")


if __name__ == "__main__":
    indexer()
