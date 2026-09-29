import chromadb
from sentence_transformers import SentenceTransformer

DOSSIER_CHROMA = "chroma_db"
NOM_COLLECTION = "code_travail"
NOM_MODELE_EMBEDDING = "paraphrase-multilingual-mpnet-base-v2"

# Nos questions de test avec l'article qu'on s'attend a trouver
QUESTIONS_TEST = [
    ("Qu'est-ce que le harcelement moral au travail ?", "L1152-1"),
    ("Quelle est la duree legale hebdomadaire du travail ?", "L3121-27"),
    ("Comment fonctionne la rupture conventionnelle ?", "L1237-11"),
    ("Quelle est la duree du conge paye annuel ?", "L3141-3"),
    ("Un CDD peut-il pourvoir un emploi permanent dans l'entreprise ?", "L1242-1"),
]


NOMBRE_RESULTATS = 5  # top-k


def tester_retrieval():
    print("🔌 Connexion a la base ChromaDB existante (sans reindexation)...")
    client = chromadb.PersistentClient(path=DOSSIER_CHROMA)
    collection = client.get_collection(NOM_COLLECTION)

    # On verifie que le modele stocke correspond bien au notre
    modele_trace = collection.metadata.get("modele_embedding")
    print(f"📌 Modele trace dans la collection : {modele_trace}")
    if modele_trace != NOM_MODELE_EMBEDDING:
        print("⚠️  ATTENTION : le modele ne correspond pas ! Resultats potentiellement faux.")

    print(f"🧠 Chargement du modele d'embedding pour encoder les questions...")
    modele = SentenceTransformer(NOM_MODELE_EMBEDDING)

    print(f"\n{'='*70}")
    print(f"TEST DE RETRIEVAL SUR {len(QUESTIONS_TEST)} QUESTIONS")
    print(f"{'='*70}\n")

    nombre_succes = 0

    for question, article_attendu in QUESTIONS_TEST:
        # On encode la question avec le MEME modele et la MEME normalisation
        vecteur_question = modele.encode(
            [question],
            normalize_embeddings=True,
        )

        resultats = collection.query(
            query_embeddings=vecteur_question.tolist(),
            n_results=NOMBRE_RESULTATS,
        )

        numeros_trouves = [meta["numero"] for meta in resultats["metadatas"][0]]
        distances = resultats["distances"][0]

        trouve = article_attendu in numeros_trouves
        if trouve:
            nombre_succes += 1
            position = numeros_trouves.index(article_attendu) + 1
            statut = f"✅ TROUVE (position {position}/{NOMBRE_RESULTATS})"
        else:
            statut = "❌ NON TROUVE"

        print(f"Question : {question}")
        print(f"Article attendu : {article_attendu} → {statut}")
        print(f"Top-{NOMBRE_RESULTATS} trouves : {numeros_trouves}")
        print(f"Distances : {[round(d, 2) for d in distances]}")
        print("-" * 70)

    print(f"\n📊 RESULTAT GLOBAL : {nombre_succes}/{len(QUESTIONS_TEST)} questions reussies")


if __name__ == "__main__":
    tester_retrieval()
