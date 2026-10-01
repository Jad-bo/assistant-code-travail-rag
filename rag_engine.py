"""
Moteur RAG (Phase 2 - Interrogation) pour l'assistant Code du travail.
Charge la base ChromaDB existante, cherche les chunks pertinents,
construit le prompt et appelle l'API Groq.

Ce script ne doit JAMAIS reindexer la base.
"""

import os
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

# --- Configuration ---
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY non trouvee ! Verifie que le fichier .env existe "
        "a la racine du projet et contient bien GROQ_API_KEY=ta_cle"
    )

DOSSIER_CHROMA = "chroma_db"
NOM_COLLECTION = "code_travail"
NOM_MODELE_EMBEDDING = "paraphrase-multilingual-mpnet-base-v2"
NOM_MODELE_LLM = "openai/gpt-oss-120b"
NOMBRE_CHUNKS = 8  # top-k

AVERTISSEMENT_JURIDIQUE = (
    "\n\n---\n"
    "⚠️ Cet assistant ne fournit pas de conseil juridique. "
    "Consultez un avocat ou l'inspection du travail pour votre situation personnelle.\n"
    "Corpus figé au 13/07/2025 : vérifiez les évolutions récentes sur legifrance.gouv.fr."
)

PROMPT_SYSTEME = """Tu es un assistant juridique specialise dans le droit du travail francais.

REGLES STRICTES A RESPECTER :
1. Tu ne reponds QU'A PARTIR du contexte fourni ci-dessous. N'utilise AUCUNE connaissance exterieure.
2. Chaque affirmation de ta reponse doit etre rattachee a un numero d'article precis PRESENT dans le contexte.
3. Cite les articles sous la forme [Article L1234-5] directement dans ta phrase.
4. N'INVENTE JAMAIS un numero d'article qui n'est pas dans le contexte fourni.
5. Si le contexte ne permet pas de repondre a la question, dis-le explicitement : "Je ne trouve pas cette information dans ma base de donnees." Ne tente pas de deviner.
6. Si la question depend de la taille de l'entreprise ou d'une convention collective, signale-le et donne la regle generale avec ses conditions.
7. Si la question demande une interpretation personnelle (ex: "mon licenciement est-il abusif ?"), donne les regles generales applicables SANS te prononcer sur le cas personnel, et recommande de consulter un professionnel.
8. Reponds en francais, de maniere claire et structuree.

CONTEXTE (articles du Code du travail) :
{contexte}
"""


class MoteurRAG:
    def __init__(self):
        print("🔌 Connexion a ChromaDB (sans reindexation)...")
        self.client_chroma = chromadb.PersistentClient(path=DOSSIER_CHROMA)
        self.collection = self.client_chroma.get_collection(NOM_COLLECTION)

        modele_trace = self.collection.metadata.get("modele_embedding")
        if modele_trace != NOM_MODELE_EMBEDDING:
            print(f"⚠️  ATTENTION : modele trace ({modele_trace}) different du modele attendu !")

        print(f"🧠 Chargement du modele d'embedding...")
        self.modele_embedding = SentenceTransformer(NOM_MODELE_EMBEDDING)

        print(f"🤖 Connexion a l'API Groq...")
        self.client_groq = Groq(api_key=GROQ_API_KEY)

        print("✅ Moteur RAG pret.\n")

    def rechercher_chunks(self, question):
        """Recherche les chunks les plus pertinents pour une question."""
        vecteur_question = self.modele_embedding.encode(
            [question],
            normalize_embeddings=True,
        )
        resultats = self.collection.query(
            query_embeddings=vecteur_question.tolist(),
            n_results=NOMBRE_CHUNKS,
        )
        return resultats

    def construire_contexte(self, resultats):
        """Construit le texte de contexte numerote a partir des chunks trouves."""
        documents = resultats["documents"][0]
        metadonnees = resultats["metadatas"][0]
        distances = resultats["distances"][0]

        blocs = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadonnees, distances), start=1):
            bloc = (
                f"[Chunk {i}] Article {meta['numero']} "
                f"(theme: {meta['theme']}, distance: {dist:.2f})\n"
                f"{meta['texte_original']}"
            )
            blocs.append(bloc)

        return "\n\n".join(blocs), metadonnees

    def repondre(self, question):
        """Pipeline complet : recherche -> prompt -> appel LLM -> reponse."""
        resultats = self.rechercher_chunks(question)
        contexte, metadonnees = self.construire_contexte(resultats)

        prompt_complet = PROMPT_SYSTEME.format(contexte=contexte)

        completion = self.client_groq.chat.completions.create(
            model=NOM_MODELE_LLM,
            messages=[
                {"role": "system", "content": prompt_complet},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        reponse_llm = completion.choices[0].message.content

        # Liste des articles sources, affichee par le CODE (pas par le LLM)
        articles_sources = [meta["numero"] for meta in metadonnees]

        reponse_finale = reponse_llm + AVERTISSEMENT_JURIDIQUE
        reponse_finale += f"\n\n📚 Articles consultes : {', '.join(articles_sources)}"

        return reponse_finale


if __name__ == "__main__":
    moteur = MoteurRAG()

    print("=" * 70)
    print("ASSISTANT CODE DU TRAVAIL - Mode test en ligne de commande")
    print("=" * 70)

    questions_test = [
        "Qu'est-ce que le harcelement moral au travail ?",
        "Combien de jours de conges payes ai-je droit chaque annee ?",
        "Mon employeur peut-il me faire travailler plus de 48h par semaine ?",
        "Quelle est la capitale de la France ?",  # question hors-sujet, pour tester le refus
    ]

    for question in questions_test:
        print(f"\n{'='*70}")
        print(f"❓ Question : {question}")
        print('='*70)
        reponse = moteur.repondre(question)
        print(f"\n💬 Reponse :\n{reponse}\n")

