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

Boogie utilise par défaut la voix neuronale française Microsoft `fr-FR-DeniseNeural`
pour une diction plus naturelle. Cela nécessite Internet : le texte de chaque
réponse vocale est transmis au service Microsoft Edge TTS pour générer l'audio.
Si ce service ou la connexion échoue, Boogie bascule sur la voix féminine locale
de Windows (Microsoft Hortense sur ce PC). La voix, le débit et la hauteur sont
réglables via `neural_voice`, `neural_rate` et `neural_pitch` dans
`boogie_config.json`.

## Réponses IA locales

Les recherches d'informations utilisent Bing RSS, avec un repli sur les
résumés de Wikipédia si le moteur de recherche n'est pas disponible. Boogie
essaie de synthétiser les sources avec Ollama sur `http://127.0.0.1:11434`.
Ollama est facultatif : s'il n'est pas installé ou ne répond pas, Boogie affiche
les extraits Web trouvés et leurs liens au lieu d'échouer. Le moteur de
recherche, le modèle Ollama et le débit vocal sont réglables dans
`boogie_config.json`.

Les questions météo utilisent les prévisions Open-Meteo. Précise une ville
(par exemple « Quelle sera la météo demain à Paris ? ») ; si tu ne la donnes
pas, Boogie te la demandera. Une ville par défaut peut aussi être définie avec
`weather_location` dans `boogie_config.json`.

## Actions reconnues

- « Ouvre un nouvel onglet Chrome » (ou une recherche formulée avec Chrome).
- « Cherche sur Google … » pour ouvrir une recherche dans le navigateur.
- « Mets [artiste ou titre] sur Spotify » pour ouvrir sa recherche Spotify.

La lecture musicale est à démarrer dans Spotify. Les commandes du PC sont
limitées à ces ouvertures ; aucune commande arbitraire n'est exécutée.
