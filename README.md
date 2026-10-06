# Boogie

Assistant de bureau en français : reconnaissance vocale Vosk sur l'ordinateur,
recherche Web, commandes simples pour Chrome/Spotify et réponses vocales.

## Lancer l'application

Depuis le dossier du projet, installe les dépendances puis lance `main.py` :

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

Le dossier `models/vosk_fr` contient le modèle de reconnaissance vocale local.
Le micro s'active automatiquement au démarrage et reste à l'écoute du wake word
**« Boogie »** tant que l'application est ouverte. Dis « Boogie », puis ta
demande ; si tu prononces seulement le wake word, Boogie attend ta demande
pendant 10 secondes. Tu peux aussi lui écrire directement.

La synthèse vocale choisit une voix féminine française installée dans Windows
(sur ce PC, Microsoft Hortense Desktop - French). Tu peux définir `voice_name`
dans `boogie_config.json` pour sélectionner une autre voix féminine installée.

## Réponses IA locales

Les recherches d'informations utilisent DuckDuckGo, puis Boogie demande une
synthèse à Ollama sur `http://127.0.0.1:11434`. Installe et démarre Ollama,
télécharge le modèle indiqué dans `boogie_config.json` (par défaut `llama3.2`),
et modifie cette configuration si nécessaire. Sans Ollama, Boogie affiche les
résultats Web trouvés avec leurs sources.

## Actions reconnues

- « Ouvre un nouvel onglet Chrome » (ou une recherche formulée avec Chrome).
- « Cherche sur Google … » pour ouvrir une recherche dans le navigateur.
- « Mets [artiste ou titre] sur Spotify » pour ouvrir sa recherche Spotify.

La lecture musicale est à démarrer dans Spotify. Les commandes du PC sont
limitées à ces ouvertures ; aucune commande arbitraire n'est exécutée.
