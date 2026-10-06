import json
import os
import re
import shutil
import subprocess
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from html.parser import HTMLParser
from pathlib import Path


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class _SearchResults(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._title = None
        self._snippet = None
        self._snippet_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            self._title = {"text": [], "url": attributes.get("href", "")}
        elif tag == "a" and self._title is not None:
            self._title["depth"] = self._title.get("depth", 1) + 1
        if "result__snippet" in classes:
            self._snippet = []
            self._snippet_depth = 1
        elif self._snippet_depth:
            self._snippet_depth += 1

    def handle_data(self, data):
        if self._title is not None:
            self._title["text"].append(data)
        if self._snippet is not None:
            self._snippet.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._title is not None:
            depth = self._title.get("depth", 1) - 1
            if depth <= 0:
                result = {
                    "title": " ".join("".join(self._title["text"]).split()),
                    "url": self._title["url"],
                }
                if result["title"] and result["url"]:
                    self.results.append(result)
                self._title = None
            else:
                self._title["depth"] = depth
        if self._snippet_depth:
            self._snippet_depth -= 1
            if self._snippet_depth == 0 and self._snippet is not None:
                snippet = " ".join("".join(self._snippet).split())
                if snippet and self.results:
                    self.results[-1]["snippet"] = snippet
                self._snippet = None


class AssistantEngine:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.config = self._load_config()

    def _load_config(self):
        config_path = self.project_dir / "boogie_config.json"
        if not config_path.exists() or not config_path.read_text(encoding="utf-8").strip():
            return {}
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
        if not isinstance(config, dict):
            raise ValueError("boogie_config.json doit contenir un objet JSON.")
        return config

    def process(self, prompt, status_callback=lambda _status: None):
        normalized = _normalize(prompt)

        spotify_action = (
            "spotify" in normalized
            and normalized.startswith(
                ("mets ", "lance ", "joue ", "ecoute ", "ouvre ", "cherche ")
            )
        )
        if spotify_action:
            return self._open_spotify(prompt)
        if any(term in normalized for term in ("nouvel onglet", "ouvre chrome", "ouvre google")):
            return self._open_chrome(prompt)
        if normalized.startswith(("recherche ", "cherche sur google ", "fais une recherche")):
            return self._google_search(prompt)

        status_callback("Je cherche des informations sur le Web…")
        results = self._search_web(prompt)
        if results:
            return self._answer_with_local_model(prompt, results)

        try:
            return self._ask_local_model(prompt, [])
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(
                "Je n’ai trouvé aucun résultat Web et Ollama n’est pas disponible. "
                "Vérifie ta connexion Internet ou lance Ollama en local."
            ) from exc

    def _open_chrome(self, prompt):
        chrome_path = shutil.which("chrome")
        if not chrome_path and os.name == "nt":
            import winreg

            app_paths = (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            )
            for key_path in app_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                        chrome_path = winreg.QueryValue(key, None)
                        break
                except FileNotFoundError:
                    continue
            if not chrome_path:
                candidates = (
                    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
                    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
                    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
                )
                chrome_path = next((str(path) for path in candidates if path.is_file()), None)

        if not chrome_path:
            raise RuntimeError("Je ne trouve pas Google Chrome sur cet ordinateur.")

        url = "https://www.google.com"
        match = re.search(r"(?:recherche|cherche)\s+(?:sur\s+google\s+)?(.+)", prompt, re.I)
        if match:
            url += "/search?q=" + urllib.parse.quote_plus(match.group(1))
        subprocess.Popen([chrome_path, "--new-tab", url])
        return "C’est fait : j’ai ouvert un nouvel onglet dans Chrome."

    def _open_spotify(self, prompt):
        normalized = _normalize(prompt)
        match = re.search(r"(?:mets|lance|joue|cherche)\s+(.+?)\s+(?:sur\s+)?spotify", normalized)
        query = match.group(1).strip() if match else ""
        if query:
            url = "https://open.spotify.com/search/" + urllib.parse.quote(query)
            description = f"la recherche Spotify pour « {query} »"
        else:
            url = "https://open.spotify.com/"
            description = "Spotify"
        if not webbrowser.open(url):
            raise RuntimeError("Je n’ai pas pu ouvrir Spotify dans ton navigateur.")
        return f"J’ai ouvert {description}. Tu peux lancer la lecture depuis Spotify."

    def _google_search(self, prompt):
        query = re.sub(
            r"^(?:recherche(?: sur google)?|cherche sur google|fais une recherche(?: sur google)?)\s*",
            "",
            prompt,
            flags=re.I,
        ).strip()
        if not query:
            query = prompt
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        if not webbrowser.open_new_tab(url):
            raise RuntimeError("Je n’ai pas pu ouvrir les résultats Google.")
        return f"J’ai lancé une recherche Google sur « {query} »."

    def _search_web(self, query):
        search_url = self.config.get(
            "web_search_url", "https://html.duckduckgo.com/html/?q={query}"
        )
        request_url = search_url.format(query=urllib.parse.quote_plus(query))
        request = urllib.request.Request(
            request_url,
            headers={"User-Agent": "BoogieAssistant/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                page = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError):
            return []

        parser = _SearchResults()
        parser.feed(page)
        results = []
        for result in parser.results[:5]:
            url = result["url"]
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc.endswith("duckduckgo.com") and parsed_url.path == "/l/":
                url = urllib.parse.parse_qs(parsed_url.query).get("uddg", [url])[0]
            result["url"] = url
            results.append(result)
        return results

    def _answer_with_local_model(self, prompt, results):
        try:
            return self._ask_local_model(prompt, results)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            excerpts = []
            for index, result in enumerate(results[:3], start=1):
                snippet = result.get("snippet", "Résumé indisponible.")
                excerpts.append(
                    f"{index}. {result['title']}\n{snippet}\nSource : {result['url']}"
                )
            return (
                "Voici ce que j’ai trouvé en ligne :\n\n"
                + "\n\n".join(excerpts)
                + "\n\nPour une synthèse par IA, lance Ollama en local et "
                "vérifie le modèle configuré dans boogie_config.json."
            )

    def _ask_local_model(self, prompt, results):
        endpoint = self.config.get("ollama_url", "http://127.0.0.1:11434")
        model = self.config.get("ollama_model", "llama3.2")
        sources = "\n".join(
            f"- {item['title']}: {item.get('snippet', '')} ({item['url']})"
            for item in results
        )
        context = sources or "Aucune source Web n’a été trouvée."
        payload = json.dumps(
            {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es Boogie, assistant francophone. Réponds en français, "
                            "de façon claire, structurée et concise. Pour toute info "
                            "factuelle récente, base-toi sur le contexte Web fourni et "
                            "cite les URLs pertinentes. N’invente pas de sources. "
                            "Si les sources ne suffisent pas, dis-le."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question : {prompt}\n\nContexte Web :\n{context}",
                    },
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result.get("message", {}).get("content", "").strip()
        if not answer:
            raise ValueError("Ollama a renvoyé une réponse vide.")
        return answer

    def speak(self, text):
        try:
            import pyttsx3

            speaker = pyttsx3.init()
            speaker.setProperty("rate", 175)
            french_voice = next(
                (
                    voice
                    for voice in speaker.getProperty("voices")
                    if "fr" in _normalize(f"{voice.id} {voice.name}")
                ),
                None,
            )
            if french_voice:
                speaker.setProperty("voice", french_voice.id)
            speaker.say(text)
            speaker.runAndWait()
            speaker.stop()
            return ""
        except Exception as exc:
            return f"La réponse vocale n’est pas disponible : {exc}"