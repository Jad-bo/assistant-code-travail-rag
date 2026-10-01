"""
Interface Streamlit (Phase 2 - Interrogation) pour l'assistant Code du travail.
Reutilise le moteur RAG de rag_engine.py.
Lance avec : streamlit run app.py
"""

import streamlit as st
from rag_engine import MoteurRAG

st.set_page_config(
    page_title="Assistant Code du travail",
    page_icon="⚖️",
    layout="centered",
)


@st.cache_resource
def charger_moteur():
    """
    Charge le moteur RAG une seule fois (mis en cache par Streamlit),
    pour eviter de recharger le modele d'embedding et de se reconnecter
    a ChromaDB a chaque interaction utilisateur.
    """
    return MoteurRAG()


# --- Interface ---
st.title("⚖️ Assistant Code du travail")
st.caption(
    "Posez une question sur le droit du travail francais. "
    "Les reponses sont basees exclusivement sur un corpus d'articles du Code du travail "
    "(archive LEGI du 13/07/2025)."
)

with st.spinner("Chargement du moteur RAG (modele d'embedding + connexion ChromaDB)..."):
    moteur = charger_moteur()

# Historique de la conversation (optionnel, simple affichage)
if "historique" not in st.session_state:
    st.session_state.historique = []

question = st.text_input(
    "Votre question :",
    placeholder="Ex : Quelle est la duree legale du preavis pour un CDI ?",
)

bouton_envoyer = st.button("Envoyer", type="primary")

if bouton_envoyer and question.strip():
    with st.spinner("Recherche dans le Code du travail et generation de la reponse..."):
        try:
            reponse = moteur.repondre(question)
            st.session_state.historique.append((question, reponse))
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

elif bouton_envoyer and not question.strip():
    st.warning("Merci de saisir une question avant d'envoyer.")

# --- Affichage de l'historique (le plus recent en premier) ---
if st.session_state.historique:
    st.divider()
    st.subheader("💬 Conversation")

    for q, r in reversed(st.session_state.historique):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(r)

# --- Bouton pour effacer l'historique ---
if st.session_state.historique:
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.historique = []
        st.rerun()
