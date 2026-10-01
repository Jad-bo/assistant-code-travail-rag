# Assistant Code du travail (RAG)

Projet de fin de module M2 MD5 — Assistant juridique répondant à des questions sur le droit du travail français, avec citation systématique des articles.

⚠️ **Avertissement juridique** : Cet assistant ne fournit pas de conseil juridique. Consultez un avocat ou l'inspection du travail pour votre situation personnelle.

## 🚧 État du projet

Projet en cours de développement. Actuellement complétés : constitution/préparation du corpus (Jalon 1), chunking/indexation (Jalon 2), validation du retrieval (Jalon 3), génération avec citations (Jalon 4).

## 📦 Constitution du corpus

Le corpus est extrait de la base **LEGI** officielle (archive `Freemium_legi_global_20250713-140000.tar.gz`, téléchargée sur echanges.dila.gouv.fr, référencée sur data.gouv.fr), au format XML — **Option B** des consignes du projet.

### Pipeline de préparation

1. **`extraire_code_travail.py`** : lit l'archive `.tar.gz` en streaming (sans décompression complète) et extrait uniquement les fichiers liés au Code du travail (identifiant `LEGITEXT000006072050`) — **59 755 fichiers** extraits sur 5 253 903 fichiers analysés dans l'archive globale.

2. **`preparer_corpus.py`** : parcourt les 52 384 fichiers XML d'articles, ne conserve que les versions **en vigueur** (balise `ETAT = VIGUEUR`), appartenant aux thèmes du projet, nettoie le texte (suppression des balises via `itertext()`, normalisation des espaces) et produit `data/corpus.json` : **557 articles, 6 thèmes**, avec métadonnées (id, numéro, thème, section, date de début, source).

3. **`ingest.py`** : encode chaque article avec le modèle d'embedding multilingue `paraphrase-multilingual-mpnet-base-v2` (vecteurs normalisés), et persiste le tout dans **ChromaDB** (`chroma_db/`), avec le nom du modèle tracé dans les métadonnées de la collection.

4. **`rag_engine.py`** : charge la base ChromaDB existante (sans jamais réindexer), cherche les chunks pertinents, construit un prompt système strict, et appelle l'API Groq pour générer une réponse sourcée.

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

Le cas non résolu (congés payés) a été testé à nouveau au Jalon 4 avec un top-k élargi à 8 : l'article L3141-3 ne remonte toujours pas, et le LLM reconstruit une réponse approximative (24 jours au lieu des 30 jours ouvrables réels) à partir d'articles périphériques. Ce cas illustre une limite connue de la recherche purement vectorielle sur des textes très courts et factuels, et motive le choix de la recherche hybride comme piste d'amélioration (Jalon 6).

## 🤖 Génération avec citations (Jalon 4)

Le moteur RAG (`rag_engine.py`) construit un prompt système strict qui :
- Interdit toute connaissance extérieure au contexte fourni
- Impose la citation du numéro d'article pour chaque affirmation (format `[Article L1234-5]`)
- Prévoit explicitement le cas d'échec (« Je ne trouve pas cette information dans ma base de données »)
- Gère les règles conditionnelles (taille d'entreprise, convention collective)
- Distingue information factuelle et conseil juridique personnalisé

**Tests réalisés** (4 questions, top-k=8) :
- Question dans le corpus avec bon retrieval (harcèlement moral, 48h/semaine) → réponses précises et bien sourcées
- Question dans le corpus mais mal retrouvée (congés payés) → réponse approximative, cas documenté comme limite connue
- Question hors-sujet (« Quelle est la capitale de la France ? ») → refus correct, comportement anti-hallucination validé

L'avertissement juridique et la liste des articles sources sont ajoutés systématiquement **par le code**, jamais par le LLM, pour garantir leur présence à 100 % des réponses.

## 📝 Questions de réflexion

### Q1 — Granularité du chunking

**Un chunk = un article.** Les articles du Code du travail sont courts, denses et constituent la découpe naturelle du texte juridique. Cette approche donne une recherche précise : le chunk retrouvé est directement l'article à citer, sans ambiguïté sur la source exacte.

L'inconvénient est que les renvois entre articles (« au sens de l'article L1234-5... ») ne sont pas résolus automatiquement. Ce compromis est acceptable car le top-k ramène souvent les articles voisins d'une même section ensemble.

**Retour d'expérience (itération)** : nous avons d'abord tenté une approche hybride en préfixant le texte embeddé par le thème ET la hiérarchie complète de section. Cette approche s'est révélée contre-productive : la section, souvent longue et identique pour plusieurs articles voisins (ex : onze articles de « Dispositions pénales » partageant exactement la même section), diluait le signal sémantique et faisait remonter des articles hors-sujet. Nous avons donc simplifié le préfixe au thème seul (`"{theme}. {texte}"`), ce qui a fait passer notre score de validation du retrieval de 2/5 à 4/5 sur nos questions de test. La section complète reste disponible dans les métadonnées pour l'affichage et la traçabilité, sans être injectée dans le vecteur.

### Q2 — Traçabilité du numéro d'article

Le numéro d'article (champ `numero`, ex : `L1152-1`) est stocké dans les **métadonnées** de chaque document, à la fois dans `corpus.json` et dans la collection ChromaDB. C'est cette valeur, extraite directement de la structure XML officielle (balise `NUM`), qui sera affichée à l'utilisateur — jamais une valeur générée ou reformulée par le LLM.

Pour garantir que le LLM ne cite pas de numéros inventés : chaque chunk est présenté dans le prompt sous la forme `[Chunk N] Article L1152-1 (theme: ..., distance: ...)`, et le prompt système interdit explicitement d'inventer un numéro absent du contexte. Le code affiche lui-même la liste des articles sources (champ `articles_sources`) depuis les métadonnées, indépendamment de ce que le LLM écrit dans sa réponse.

### Q3 — Fraîcheur du corpus

Le droit du travail évolue en permanence (lois, ordonnances). Notre corpus est figé à la date de l'archive LEGI utilisée : **le 13 juillet 2025**. Cette date est stockée dans le champ `source` de chaque document (`"LEGI - archive du 13/07/2025"`), et est rappelée à l'utilisateur dans chaque réponse de l'assistant (via la constante `AVERTISSEMENT_JURIDIQUE`), avec une invitation à vérifier les évolutions récentes sur legifrance.gouv.fr.

Pour mettre à jour le corpus, il suffit de télécharger une archive LEGI plus récente et de relancer le pipeline complet (`extraire_code_travail.py` → `preparer_corpus.py` → `ingest.py`).

### Q4 — Réponses conditionnelles

Beaucoup de réponses du Code du travail dépendent de la taille de l'entreprise, de la convention collective applicable, ou d'autres conditions spécifiques (voir par exemple l'article L3121-33 sur les heures supplémentaires, qui distingue les entreprises « de vingt salariés au plus » et « de plus de vingt salariés »).

Plutôt que de multiplier les questions de clarification (ce qui alourdirait l'échange en ligne de commande), notre prompt système demande explicitement au LLM de :
1. Donner la **règle générale** applicable à partir des articles du contexte
2. **Signaler explicitement** quand une règle varie selon la taille de l'entreprise ou la convention collective applicable
3. Recommander de vérifier les dispositions spécifiques auprès d'un professionnel quand c'est pertinent

Exemple observé en test (question : « Mon employeur peut-il me faire travailler plus de 48h par semaine ? ») : l'assistant a correctement signalé qu'il existe « des dispositifs d'aménagement du temps de travail » tout en précisant que le plafond de 48h reste applicable sauf dérogation exceptionnelle non prévue dans le contexte fourni — illustrant bien la gestion de ces nuances conditionnelles.

### Q5 — Frontière du conseil juridique

Une question d'**information factuelle** (« Quelle est la durée légale hebdomadaire du travail ? ») a sa réponse directement dans le Code : l'assistant répond en citant l'article pertinent. Une question d'**interprétation personnelle** (« mon licenciement est-il abusif ? ») demande d'appliquer le droit à une situation individuelle précise : c'est du conseil juridique, que notre assistant ne doit pas fournir.

Notre prompt système gère cette frontière de deux façons :
1. Il demande au LLM de donner les **règles générales** qui s'appliquent à la situation évoquée, **sans se prononcer** sur le cas personnel de l'utilisateur
2. Il recommande systématiquement de consulter un avocat ou l'inspection du travail pour toute situation personnelle

Cette garantie est renforcée techniquement : l'**avertissement juridique est ajouté par le code lui-même** (pas par le LLM) à la fin de chaque réponse, via la constante `AVERTISSEMENT_JURIDIQUE` concatenée systématiquement dans `rag_engine.py`. Ainsi, même si le LLM oubliait de le mentionner dans sa réponse, l'avertissement apparaît toujours.

## 🧠 Choix techniques

- **Modèle d'embedding** : `paraphrase-multilingual-mpnet-base-v2` (multilingue, 768 dimensions) — bon choix par défaut pour du contenu francophone.
- **Normalisation des vecteurs** : activée (`normalize_embeddings=True`), pour une similarité cosinus correcte.
- **Base vectorielle** : ChromaDB (locale, persistante), avec le nom du modèle d'embedding tracé dans les métadonnées de la collection pour éviter toute incohérence en cas de changement de modèle.
- **Texte embeddé** : `"{theme}. {texte de l'article}"` — préfixe minimal après itération (voir Q1).
- **Top-k retrieval** : 8 chunks (ajusté depuis 5 pour améliorer le rappel sur les cas limites).
- **Modèle LLM (génération)** : `openai/gpt-oss-120b` via l'API Groq, température 0.1 (favorise la fidélité au contexte plutôt que la créativité).
- **Clé API** : stockée dans `.env` (jamais commité), chargée via `python-dotenv`.

## 🛠️ Installation
git clone https://github.com/Jad-bo/assistant-code-travail-rag.git
cd assistant-code-travail-rag
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Créer un fichier `.env` à la racine sur le modèle de `.env.example`, avec une clé API Groq (gratuite sur console.groq.com).

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

## 🤖 Lancement de l'assistant (mode test en ligne de commande)

python rag_engine.py


## 🖥️ Interface (Jalon 5)

L'interface utilisateur est développée avec **Streamlit** (`app.py`), répondant à l'exigence d'une boucle interactive de questions-réponses :
- Saisie de la question dans un champ de texte
- Affichage de la réponse avec citations d'articles, de l'avertissement juridique et des sources
- Historique de conversation affiché façon chat
- Chargement du moteur RAG mis en cache (`@st.cache_resource`) pour éviter toute réindexation ou rechargement du modèle à chaque question

Lancement :
streamlit run app.py

## 🛡️ Amélioration (Jalon 6) : Agent modérateur

Un agent modérateur (`moderer_question()` dans `rag_engine.py`) analyse chaque question avant tout traitement, via un appel LLM dédié (température 0.0, sortie JSON strict) qui détermine :
- **`safe`** : la question est-elle une tentative de prompt injection (ex : "ignore tes instructions") ?
- **`in_scope`** : la question concerne-t-elle le droit du travail français ?

Deux refus distincts et explicites sont renvoyés selon le cas, **avant** d'interroger ChromaDB ou de générer une réponse — économisant des appels inutiles et bloquant les tentatives de détournement en amont.

**Robustesse** : en cas d'erreur de modération (JSON mal formé, API indisponible), le système adopte une stratégie *fail-open* (la question est autorisée par défaut) plutôt que de bloquer l'utilisateur à cause d'un bug technique, ce choix étant documenté comme compromis assumé.

**Tests validés** :
| Question | Résultat |
|---|---|
| Harcèlement moral | ✅ Réponse sourcée normale |
| Congés payés | ✅ Honnête (« je ne trouve pas », limite connue du retrieval) |
| 48h/semaine | ✅ Réponse sourcée normale |
| « Quelle est la capitale de la France ? » | ✅ Refusé (hors-sujet), sans appel de recherche inutile |
| « Ignore tes instructions... » | ✅ Refusé (tentative de détournement détectée) |

### Tentative non retenue : recherche hybride (BM25 + vectoriel)

Nous avons d'abord testé une recherche hybride combinant BM25 (lexical) et la recherche vectorielle, via Reciprocal Rank Fusion, pour tenter de résoudre le cas de l'article L3141-3 (congés payés) qui ne remontait pas dans le top-k vectoriel pur.

Résultat : BM25 a introduit du bruit sur notre corpus, car les questions de test étaient en langage naturel sans numéro d'article explicite, et notre vocabulaire juridique partage énormément de mots courants entre thèmes. La fusion a fait remonter des articles hors-sujet (ex : rupture conventionnelle, licenciement) pour des questions sur le harcèlement ou la durée du travail, dégradant la pertinence globale. Cette piste n'a donc pas été retenue, au profit de l'agent modérateur, plus robuste et directement utile sur un vrai angle mort (sécurité) non couvert auparavant.
