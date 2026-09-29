# Assistant Code du travail (RAG)

Projet de fin de module M2 MD5 — Assistant juridique répondant à des questions sur le droit du travail français, avec citation systématique des articles.

⚠️ **Avertissement juridique** : Cet assistant ne fournit pas de conseil juridique. Consultez un avocat ou l'inspection du travail pour votre situation personnelle.

## 🚧 État du projet

Projet en cours de développement. Actuellement complété : constitution et préparation du corpus (Jalon 1).

## 📦 Constitution du corpus

Le corpus est extrait de la base **LEGI** officielle (archive `Freemium_legi_global_20250713-140000.tar.gz`, téléchargée sur echanges.dila.gouv.fr, référencée sur data.gouv.fr), au format XML — **Option B** des consignes du projet.

### Pipeline de préparation

1. **`extraire_code_travail.py`** : lit l'archive `.tar.gz` en streaming (sans décompression complète) et extrait uniquement les fichiers liés au Code du travail (identifiant `LEGITEXT000006072050`) — **59 755 fichiers** extraits sur 5 253 903 fichiers analysés dans l'archive globale.

2. **`preparer_corpus.py`** : parcourt les 52 384 fichiers XML d'articles, ne conserve que les versions **en vigueur** (balise `ETAT = VIGUEUR`), appartenant aux thèmes du projet, nettoie le texte (suppression des balises via `itertext()`, normalisation des espaces) et produit `data/corpus.json` : **557 articles, 6 thèmes**, avec métadonnées (id, numéro, thème, section, date de début, source).

### Thèmes couverts (6 sur 8 proposés)

| Thème | Articles |
|---|---|
| Contrat de travail (CDI, CDD) | 227 |
| Licenciement | 178 |
| Durée du travail et heures supplémentaires | 70 |
| Congés payés | 38 |
| Rupture conventionnelle | 28 |
| Harcèlement et discrimination | 16 |

Les thèmes **Salaire minimum (SMIC)** et **Représentation du personnel** n'ont pas été retenus pour ce projet.

## 📝 Questions de réflexion

### Q1 — Granularité du chunking

**Un chunk = un article.** Les articles du Code du travail sont courts, denses et constituent la découpe naturelle du texte juridique. Cette approche donne une recherche précise : le chunk retrouvé est directement l'article à citer, sans ambiguïté sur la source exacte.

L'inconvénient est que les renvois entre articles (« au sens de l'article L1234-5... ») ne sont pas résolus automatiquement : si un article en cite un autre, seul l'article trouvé par la recherche est récupéré, pas celui qu'il référence. Ce compromis est acceptable car le top-k ramène souvent les articles voisins d'une même section ensemble.

Une approche hybride est envisagée : préfixer le texte embeddé par le thème et la section de l'article (via nos métadonnées `theme` et `section`), pour redonner du contexte sans perdre la précision du découpage par article.

### Q2 — Traçabilité du numéro d'article

Le numéro d'article (champ `numero`, ex: `L1152-1`) est stocké dans les **métadonnées** de chaque document dans `corpus.json`. C'est cette valeur, extraite directement de la structure XML officielle (balise `NUM`), qui sera affichée à l'utilisateur — jamais une valeur générée ou reformulée par le LLM.

Pour garantir que le LLM ne cite pas de numéros inventés : chaque chunk sera présenté dans le prompt sous la forme `[Article L1152-1] texte...`, et le prompt système interdira explicitement de citer un numéro absent du contexte fourni. Le code affichera lui-même la liste des articles sources depuis les métadonnées, indépendamment de ce que le LLM écrit dans sa réponse.

### Q3 — Fraîcheur du corpus

Le droit du travail évolue en permanence (lois, ordonnances). Notre corpus est figé à la date de l'archive LEGI utilisée : **le 13 juillet 2025**. Cette date est stockée dans le champ `source` de chaque document (`"LEGI - archive du 13/07/2025"`), et sera rappelée à l'utilisateur dans chaque réponse de l'assistant, avec une invitation à vérifier les évolutions récentes sur legifrance.gouv.fr.

Pour mettre à jour le corpus, il suffit de télécharger une archive LEGI plus récente et de relancer le pipeline (`extraire_code_travail.py` puis `preparer_corpus.py`).

### Q4 — Réponses conditionnelles

*À compléter au Jalon 4 (génération avec le prompt système).*

### Q5 — Frontière du conseil juridique

*À compléter au Jalon 4 (génération avec le prompt système).*

## 🛠️ Installation

git clone https://github.com/Jad-bo/assistant-code-travail-rag.git
cd assistant-code-travail-rag
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

## 📂 Construction du corpus (à faire une fois)

1. Télécharger l'archive `Freemium_legi_global_*.tar.gz` depuis echanges.dila.gouv.fr/OPENDATA/LEGI/ et la placer dans `data/`.
2. Lancer l'extraction ciblée :

python extraire_code_travail.py

3. Lancer le nettoyage et le filtrage par thème :

python preparer_corpus.py

## 🚀 Prochaines étapes

- [ ] Jalon 2 : Chunking et indexation (ChromaDB, embeddings normalisés)
- [ ] Jalon 3 : Validation du retrieval
- [ ] Jalon 4 : Génération avec citations (API Groq)
- [ ] Jalon 5 : Interface (Streamlit)
- [ ] Jalon 6 : Amélioration (à définir)
