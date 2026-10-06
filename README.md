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
Clique sur **Parler** pour activer le micro ; Boogie n'écoute pas en permanence.
Clique à nouveau pour couper l'écoute. Tu peux aussi lui écrire directement.

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
