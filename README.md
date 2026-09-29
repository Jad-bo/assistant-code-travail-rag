# Assistant Code du travail (RAG)

Projet de fin de module M2 MD5 — Assistant juridique répondant à des questions sur le droit du travail français, avec citation systématique des articles.

⚠️ **Avertissement juridique** : Cet assistant ne fournit pas de conseil juridique. Consultez un avocat ou l'inspection du travail pour votre situation personnelle.

## 🚧 État du projet

Projet en cours de développement. Actuellement complétés : constitution/préparation du corpus (Jalon 1), chunking/indexation (Jalon 2), validation du retrieval (Jalon 3).

## 📦 Constitution du corpus

Le corpus est extrait de la base **LEGI** officielle (archive `Freemium_legi_global_20250713-140000.tar.gz`, téléchargée sur echanges.dila.gouv.fr, référencée sur data.gouv.fr), au format XML — **Option B** des consignes du projet.

### Pipeline de préparation

1. **`extraire_code_travail.py`** : lit l'archive `.tar.gz` en streaming (sans décompression complète) et extrait uniquement les fichiers liés au Code du travail (identifiant `LEGITEXT000006072050`) — **59 755 fichiers** extraits sur 5 253 903 fichiers analysés dans l'archive globale.

2. **`preparer_corpus.py`** : parcourt les 52 384 fichiers XML d'articles, ne conserve que les versions **en vigueur** (balise `ETAT = VIGUEUR`), appartenant aux thèmes du projet, nettoie le texte (suppression des balises via `itertext()`, normalisation des espaces) et produit `data/corpus.json` : **557 articles, 6 thèmes**, avec métadonnées (id, numéro, thème, section, date de début, source).

3. **`ingest.py`** : encode chaque article avec le modèle d'embedding multilingue `paraphrase-multilingual-mpnet-base-v2` (vecteurs normalisés), et persiste le tout dans **ChromaDB** (`chroma_db/`), avec le nom du modèle tracé dans les métadonnées de la collection.

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

## 🔎 Validation du retrieval (Jalon 3)

Avant de brancher le LLM, nous avons validé la recherche seule sur 5 questions de test dont nous connaissions l'article attendu (`test_retrieval.py`).

**Résultat final : 4/5 questions réussies** (l'article attendu apparaît dans le top-5).

| Question | Article attendu | Résultat |
|---|---|---|
| Qu'est-ce que le harcèlement moral au travail ? | L1152-1 | ✅ Trouvé (position 2/5) |
| Quelle est la durée légale hebdomadaire du travail ? | L3121-27 | ✅ Trouvé (position 5/5) |
| Comment fonctionne la rupture conventionnelle ? | L1237-11 | ✅ Trouvé (position 3/5) |
| Quelle est la durée du congé payé annuel ? | L3141-3 | ❌ Non trouvé |
| Un CDD peut-il pourvoir un emploi permanent ? | L1242-1 | ✅ Trouvé (position 3/5) |

Le cas non résolu (congés payés) est documenté et gardé comme piste d'amélioration (recherche hybride, Jalon 6).

## 📝 Questions de réflexion

### Q1 — Granularité du chunking

**Un chunk = un article.** Les articles du Code du travail sont courts, denses et constituent la découpe naturelle du texte juridique. Cette approche donne une recherche précise : le chunk retrouvé est directement l'article à citer, sans ambiguïté sur la source exacte.

L'inconvénient est que les renvois entre articles (« au sens de l'article L1234-5... ») ne sont pas résolus automatiquement. Ce compromis est acceptable car le top-k ramène souvent les articles voisins d'une même section ensemble.

**Retour d'expérience (itération)** : nous avons d'abord tenté une approche hybride en préfixant le texte embeddé par le thème ET la hiérarchie complète de section. Cette approche s'est révélée contre-productive : la section, souvent longue et identique pour plusieurs articles voisins (ex : onze articles de « Dispositions pénales » partageant exactement la même section), diluait le signal sémantique et faisait remonter des articles hors-sujet (par exemple des articles pénaux sur le CDD remontaient pour des questions sur la durée du travail). Nous avons donc simplifié le préfixe au thème seul (`"{theme}. {texte}"`), ce qui a fait passer notre score de validation du retrieval de 2/5 à 4/5 sur nos questions de test, avec des distances de similarité nettement meilleures sur l'ensemble du corpus. La section complète reste disponible dans les métadonnées pour l'affichage et la traçabilité, sans être injectée dans le vecteur.

### Q2 — Traçabilité du numéro d'article

Le numéro d'article (champ `numero`, ex : `L1152-1`) est stocké dans les **métadonnées** de chaque document, à la fois dans `corpus.json` et dans la collection ChromaDB. C'est cette valeur, extraite directement de la structure XML officielle (balise `NUM`), qui sera affichée à l'utilisateur — jamais une valeur générée ou reformulée par le LLM.

Pour garantir que le LLM ne cite pas de numéros inventés : chaque chunk sera présenté dans le prompt sous la forme `[Article L1152-1] texte...`, et le prompt système interdira explicitement de citer un numéro absent du contexte fourni. Le code affichera lui-même la liste des articles sources depuis les métadonnées, indépendamment de ce que le LLM écrit dans sa réponse.

### Q3 — Fraîcheur du corpus

Le droit du travail évolue en permanence (lois, ordonnances). Notre corpus est figé à la date de l'archive LEGI utilisée : **le 13 juillet 2025**. Cette date est stockée dans le champ `source` de chaque document (`"LEGI - archive du 13/07/2025"`), et sera rappelée à l'utilisateur dans chaque réponse de l'assistant, avec une invitation à vérifier les évolutions récentes sur legifrance.gouv.fr.

Pour mettre à jour le corpus, il suffit de télécharger une archive LEGI plus récente et de relancer le pipeline complet (`extraire_code_travail.py` puis `preparer_corpus.py` puis `ingest.py`).

### Q4 — Réponses conditionnelles

*À compléter au Jalon 4 (génération avec le prompt système).*

### Q5 — Frontière du conseil juridique

*À compléter au Jalon 4 (génération avec le prompt système).*

## 🧠 Choix techniques

- **Modèle d'embedding** : `paraphrase-multilingual-mpnet-base-v2` (multilingue, 768 dimensions) — bon choix par défaut pour du contenu francophone.
- **Normalisation des vecteurs** : activée (`normalize_embeddings=True`), pour une similarité cosinus correcte.
- **Base vectorielle** : ChromaDB (locale, persistante), avec le nom du modèle d'embedding tracé dans les métadonnées de la collection pour éviter toute incohérence en cas de changement de modèle.
- **Texte embeddé** : `"{theme}. {texte de l'article}"` — préfixe minimal après itération (voir Q1).

## 🛠️ Installation

git clone https://github.com/Jad-bo/assistant-code-travail-rag.git
cd assistant-code-travail-rag
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

## 📂 Construction du corpus et de la base vectorielle (à faire une fois)

1. Télécharger l'archive `Freemium_legi_global_*.tar.gz` depuis echanges.dila.gouv.fr/OPENDATA/LEGI/ et la placer dans `data/`.
2. Extraction ciblée du Code du travail :

python extraire_code_travail.py

3. Nettoyage et filtrage par thème :

python preparer_corpus.py

4. Indexation dans ChromaDB (encodage + persistance) :

python ingest.py

## 🔎 Validation du retrieval (optionnel, contrôle qualité)

python test_retrieval.py

