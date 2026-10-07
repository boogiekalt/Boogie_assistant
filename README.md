# Boogie

Assistant de bureau en français : reconnaissance vocale Vosk sur l'ordinateur,
recherche Web, commandes simples pour Chrome/Spotify et réponses vocales.

## Lancer l'application

Depuis le dossier du projet, installe les dépendances puis lance `main.py` :

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

`window.py` lance la même application complète. L'interface rouge de type HUD
affiche le cœur animé, le journal de la session, l'état du processeur, de la RAM,
du réseau local et de la batterie lorsqu'elle est détectée. L'icône de fenêtre
et de barre des tâches utilise `assets/logo.png`.

Le dossier `models/vosk_fr` contient le modèle de reconnaissance vocale local.
Le micro s'active automatiquement au démarrage et reste à l'écoute du wake word
**« Boogie »** tant que l'application est ouverte. Dis « Boogie », puis ta
demande ; si tu prononces seulement le wake word, Boogie attend ta demande
pendant 10 secondes. Tu peux aussi lui écrire directement.

Le profil vocal se choisit dans le panneau de droite : voix féminine ou masculine
naturelle, voix aiguë comique ou voix grave robotique. Les profils sont enregistrés
dans `boogie_config.json`. Les voix et effets Edge TTS nécessitent Internet ; en
cas d'indisponibilité, Boogie utilise la voix Windows installée correspondant au
genre choisi. Les effets de hauteur ne sont alors pas disponibles. Les profils
comiques sont des effets stylisés et ne reproduisent pas la voix d'un personnage.

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
