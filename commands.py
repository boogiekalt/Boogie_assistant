import json
import asyncio
import ctypes
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unicodedata
import asyncio
import ctypes
from datetime import datetime
from html.parser import HTMLParser
from xml.etree import ElementTree
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date, timedelta
from pathlib import Path


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _clean_recognized_text(text):
    if text is None:
        return ""
    cleaned = _normalize(text)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s'-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    for wrong, right in {
        "cuisine": "squeezie",
        "cuisines": "squeezie",
        "cuizine": "squeezie",
        "squeezi": "squeezie",
        "squeezie sur youtube": "squeezie",
        "squeezie youtube": "squeezie",
    }.items():
        cleaned = re.sub(rf"\b{re.escape(wrong)}\b", right, cleaned)

    cleaned = re.sub(
        r"\b(epstein)(?:\s+(?:en|et|putain|ptn|heu|hein|euh|bon|donc|alors|genre|bah))*\b",
        r"\1",
        cleaned,
    )
    cleaned = re.sub(
        r"\b(?:euh|heu|hein|bon|donc|alors|genre|bah|voila|voile|en|et|putain|ptn|ca|c est|cest)\b",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.!?;:-")
    if not cleaned:
        return ""
    return cleaned


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _strip_markup(text):
    parser = _PlainText()
    parser.feed(text)
    return " ".join(" ".join(parser.parts).split())


def _decode_search_response(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


class AssistantEngine:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.config = self._load_config()
        self._pending_weather_prompt = None
        self._speech_stop_event = threading.Event()

    def _load_config(self):
        config_path = self.project_dir / "boogie_config.json"
        if not config_path.exists() or not config_path.read_text(encoding="utf-8").strip():
            return {}
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
        if not isinstance(config, dict):
            raise ValueError("boogie_config.json doit contenir un objet JSON.")
        return config

    def process(self, prompt, status_callback=None):
        normalized = _normalize(prompt)

        if self._pending_weather_prompt is not None:
            location = self._extract_weather_location(prompt)
            if location is None:
                location = prompt.strip(" \t\r\n,.;!?")
            weather_prompt = self._pending_weather_prompt
            self._pending_weather_prompt = None
            return self._get_weather(location, weather_prompt)

        if self._is_weather_question(normalized):
            location = self.config.get("weather_location") or self._extract_weather_location(prompt)
            if not location:
                self._pending_weather_prompt = normalized
                return (
                    "Bien sûr — pour quelle ville veux-tu la météo de demain ?"
                )
            return self._get_weather(location, normalized)

        if self._is_time_question(normalized):
            current_time = datetime.now().strftime("%H:%M")
            hour, minute = current_time.split(":")
            return f"Il est {hour} h {minute}."

        spotify_action = (
            "spotify" in normalized
            and normalized.startswith(
                ("mets ", "lance ", "joue ", "ecoute ", "ouvre ", "cherche ")
            )
        )
        if spotify_action:
            return self._open_spotify(prompt)
        if self._is_youtube_request(normalized):
            return self._open_youtube(prompt)
        if self._is_close_request(normalized):
            return self._close_app(prompt)
        if any(term in normalized for term in ("nouvel onglet", "ouvre chrome", "ouvre google")):
            return self._open_chrome(prompt)
        if normalized.startswith(("recherche ", "cherche sur google ", "fais une recherche")):
            return self._google_search(prompt)

        if status_callback is not None:
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

    @staticmethod
    def _clean_recognized_text(text):
        return _clean_recognized_text(text)

    @staticmethod
    def _is_time_question(normalized):
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = " ".join(normalized.split())
        return any(
            re.search(pattern, normalized)
            for pattern in (
                r"\bquelle heure\b",
                r"\bquelle heure est il\b",
                r"\b(?:donne|dis|indique) moi l heure\b",
                r"\btu as l heure\b",
                r"\bil est quelle heure\b",
                r"\bheure actuelle\b",
                r"\bheure qu il est\b",
            )
        )

    @staticmethod
    def _is_weather_question(normalized):
        return any(
            re.search(pattern, normalized)
            for pattern in (
                r"\bmeteo\b",
                r"\btemps\b",
                r"\btemperature\b",
                r"\btemperatures\b",
                r"\bpluie\b",
                r"\bpleuvra\b",
                r"\bneigera\b",
                r"\bprevisions? meteorologiques?\b",
            )
        )

    @staticmethod
    def _extract_weather_location(prompt):
        normalized = _normalize(prompt)
        match = re.search(
            r"\b(?:a|pour|sur|dans)\s+"
            r"([a-z0-9][a-z0-9 '\-]{0,60})",
            normalized,
        )
        if not match:
            return None
        location = match.group(1).strip(" \t\r\n,.;!?")
        location = re.split(
            r"\b(?:demain|aujourd hui|ce soir|cette nuit|"
            r"la semaine prochaine|maintenant)\b",
            location,
            maxsplit=1,
        )[0].strip()
        if location in {"la", "le", "les", "l", "quelle", "quel", "quels", "quelles"}:
            return None
        return location or None

    def _get_weather(self, location, normalized_prompt):
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search?" + (
            urllib.parse.urlencode(
                {"name": location, "count": 5, "language": "fr", "format": "json"}
            )
        )
        try:
            place_request = urllib.request.Request(
                geocoding_url,
                headers={"User-Agent": "BoogieAssistant/1.0"},
            )
            with urllib.request.urlopen(place_request, timeout=12) as response:
                places = json.loads(response.read().decode("utf-8")).get("results", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Le service météo est momentanément inaccessible. Réessaie dans "
                "quelques instants."
            ) from exc

        if not places:
            return (
                f"Je ne trouve pas la ville « {location} ». Peux-tu vérifier "
                "son nom ou préciser le pays ?"
            )
        place = max(places, key=lambda result: result.get("population", 0))
        timezone = place.get("timezone", "auto")
        forecast_url = "https://api.open-meteo.com/v1/forecast?" + (
            urllib.parse.urlencode(
                {
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max"
                    ),
                    "current": "temperature_2m",
                    "forecast_days": 3,
                    "timezone": timezone,
                }
            )
        )
        try:
            forecast_request = urllib.request.Request(
                forecast_url,
                headers={"User-Agent": "BoogieAssistant/1.0"},
            )
            with urllib.request.urlopen(forecast_request, timeout=12) as response:
                forecast = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "Je n’ai pas pu récupérer les prévisions météo pour le moment."
            ) from exc

        daily = forecast.get("daily", {})
        dates = daily.get("time", [])
        if not dates:
            raise RuntimeError("Le service météo n’a pas fourni de prévisions.")

        local_today = date.fromisoformat(dates[0])
        target_date = local_today
        if any(word in normalized_prompt for word in ("demain", "lendemain")):
            target_date += timedelta(days=1)
        target_index = next(
            (
                index
                for index, forecast_date in enumerate(dates)
                if forecast_date == target_date.isoformat()
            ),
            None,
        )
        if target_index is None:
            raise RuntimeError("La prévision demandée n’est pas disponible.")

        code = daily["weather_code"][target_index]
        description = self._weather_description(code)
        high = daily["temperature_2m_max"][target_index]
        low = daily["temperature_2m_min"][target_index]
        precipitation = daily["precipitation_probability_max"][target_index]
        day_label = "demain" if target_index else "aujourd’hui"
        country = place.get("country", "")
        location_label = place["name"]
        if country:
            location_label += f", {country}"
        return (
            f"Météo prévue {day_label} à {location_label} : {description}, "
            f"entre {round(low)} et {round(high)} °C. "
            f"Risque maximal de précipitations : {precipitation} %.\n"
            f"Source : https://open-meteo.com/"
        )

    @staticmethod
    def _weather_description(code):
        descriptions = {
            0: "ciel dégagé",
            1: "principalement dégagé",
            2: "partiellement nuageux",
            3: "couvert",
            45: "brouillard",
            48: "brouillard givrant",
            51: "bruine légère",
            53: "bruine modérée",
            55: "bruine dense",
            56: "bruine verglaçante légère",
            57: "bruine verglaçante dense",
            61: "pluie légère",
            63: "pluie modérée",
            65: "forte pluie",
            66: "pluie verglaçante légère",
            67: "forte pluie verglaçante",
            71: "faibles chutes de neige",
            73: "chutes de neige modérées",
            75: "fortes chutes de neige",
            77: "grains de neige",
            80: "averses de pluie légères",
            81: "averses de pluie modérées",
            82: "fortes averses de pluie",
            85: "averses de neige légères",
            86: "fortes averses de neige",
            95: "orage",
            96: "orage avec grêle légère",
            99: "orage avec forte grêle",
        }
        return descriptions.get(code, "conditions météo variables")

    @staticmethod
    def _is_youtube_request(normalized):
        if "youtube" in normalized or "yt" in normalized:
            return True
        return (
            "video" in normalized or "videos" in normalized
        ) and any(
            verb in normalized
            for verb in (
                "lance ", "ouvre ", "joue ", "mets ", "cherche ", "recherche ",
                "ecoute ", "écoute ", "regarde ", "regarder ", "play "
            )
        )

    @staticmethod
    def _is_close_request(normalized):
        if "ferme" not in normalized and "fermer" not in normalized and "close" not in normalized:
            return False
        return any(term in normalized for term in ("edge", "browser", "chrome", "google chrome", "microsoft edge"))

    def _close_app(self, prompt):
        normalized = _normalize(prompt)
        if "edge" in normalized or "microsoft edge" in normalized:
            app_name = "Microsoft Edge"
            exe_names = ("msedge.exe", "microsoftedge.exe")
        elif "chrome" in normalized or "google chrome" in normalized:
            app_name = "Google Chrome"
            exe_names = ("chrome.exe",)
        else:
            app_name = "le navigateur"
            exe_names = ("msedge.exe", "microsoftedge.exe", "chrome.exe")

        found = False
        for exe_name in exe_names:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", exe_name],
                capture_output=True,
                text=True,
                shell=True,
            )
            if result.returncode in (0, 128):
                found = True

        if not found:
            raise RuntimeError(f"Je n’ai pas trouvé {app_name} ouvert pour le fermer.")
        display_name = "Edge" if app_name == "Microsoft Edge" else app_name
        return f"C’est fait : j’ai fermé {display_name}."

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

    def _open_youtube(self, prompt):
        cleaned = prompt.strip()
        cleaned = re.sub(r"^(?:lance|ouvre|joue|mets|cherche|recherche|ecoute|écoute|regarde|play)\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^(?:une\s+)?(?:vid[ée]o|video)\s+(?:de|du|d')?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+sur\s+(?:youtube|yt)\s*$", "", cleaned, flags=re.I)
        cleaned = cleaned.strip(" .!?")
        if not cleaned:
            raise RuntimeError("Je n’ai pas pu identifier la vidéo demandée.")

        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(cleaned)
        if not webbrowser.open_new_tab(url):
            raise RuntimeError("Je n’ai pas pu ouvrir YouTube.")
        return f"J’ai ouvert YouTube pour chercher « {cleaned} » dans les résultats de recherche."

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
        search_query = self._clean_search_query(query)
        search_url = self.config.get(
            "web_search_url", "https://www.bing.com/search?format=rss&q={query}"
        )
        request_url = search_url.format(query=urllib.parse.quote_plus(search_query))
        request = urllib.request.Request(
            request_url,
            headers={"User-Agent": "BoogieAssistant/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = _decode_search_response(response.read())
            root = ElementTree.fromstring(payload)
            results = []
            for item in root.findall("./channel/item"):
                title = _strip_markup(item.findtext("title", ""))
                url = item.findtext("link", "").strip()
                snippet = _strip_markup(item.findtext("description", ""))
                if title and url.startswith(("https://", "http://")):
                    results.append(
                        {"title": title, "url": url, "snippet": snippet}
                    )
                if len(results) == 5:
                    break
        except (urllib.error.URLError, TimeoutError, ElementTree.ParseError):
            results = []

        topic_terms = self._search_terms(search_query)
        wikipedia_results = self._search_wikipedia(search_query)
        for result in wikipedia_results:
            title_terms = set(re.findall(r"\w+", _normalize(result["title"])))
            required_matches = min(2, len(topic_terms))
            if required_matches and len(topic_terms & title_terms) < required_matches:
                continue
            if not any(
                existing["url"].rstrip("/") == result["url"].rstrip("/")
                for existing in results
            ):
                results.append(result)
        if topic_terms:
            results.sort(
                key=lambda result: (
                    2 * len(topic_terms & set(re.findall(r"\w+", _normalize(result["title"]))))
                    + len(topic_terms & set(re.findall(r"\w+", _normalize(result["snippet"])))),
                    len(result.get("snippet", "")),
                ),
                reverse=True,
            )
        return results[:5]

    @staticmethod
    def _clean_search_query(query):
        cleaned = _normalize(query).strip()
        cleaned = re.sub(
            r"^(?:dis moi|donne moi|indique moi|explique moi|"
            r"quelle est|quel est|quels sont|quelles sont|"
            r"qui est|qui sont|qu est ce que|c est quoi)\s+",
            "",
            cleaned,
        )
        cleaned = re.sub(r"[^\w\s'-]", " ", cleaned)
        stopwords = {
            "la", "le", "les", "un", "une", "des", "du", "de", "d",
            "en", "a", "au", "aux", "et", "est", "sont", "il", "elle",
            "ils", "elles", "qui", "que", "quoi", "pour", "avec", "sur",
            "dans", "par", "ce", "cette", "ces", "mon", "ma", "mes",
        }
        terms = [term for term in cleaned.split() if term not in stopwords]
        return " ".join(terms).strip() or query

    @staticmethod
    def _search_terms(query):
        ignored_terms = {
            "les", "des", "une", "pour", "avec", "dans", "sur", "qui",
            "que", "quoi", "est", "sont", "etre", "avoir", "fait",
            "comment", "pourquoi", "quand", "quel", "quelle", "quels",
            "quelles", "donne", "dis", "moi", "mon", "ma", "mes",
            "sera", "demain", "aujourd", "hui",
        }
        return {
            term
            for term in re.findall(r"\w+", _normalize(query))
            if len(term) > 2 and term not in ignored_terms
        }

    def _search_wikipedia(self, query):
        parameters = urllib.parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 3,
                "format": "json",
                "utf8": 1,
            }
        )
        url = f"https://fr.wikipedia.org/w/api.php?{parameters}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "BoogieAssistant/1.0 (personal desktop assistant)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []

        results = []
        for item in payload.get("query", {}).get("search", [])[:2]:
            title = item.get("title", "").strip()
            if not title:
                continue
            summary_url = (
                "https://fr.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(title.replace(" ", "_"))
            )
            summary_request = urllib.request.Request(
                summary_url,
                headers={"User-Agent": "BoogieAssistant/1.0 (personal desktop assistant)"},
            )
            try:
                with urllib.request.urlopen(summary_request, timeout=8) as response:
                    summary = json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                continue

            extract = summary.get("extract", "").strip()
            page_url = summary.get("content_urls", {}).get("desktop", {}).get(
                "page", ""
            )
            if extract and page_url:
                results.append(
                    {"title": title, "url": page_url, "snippet": extract}
                )
        return results

    def _answer_with_local_model(self, prompt, results):
        try:
            return self._ask_local_model(prompt, results)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            return self._format_web_results(results)

    @staticmethod
    def _format_web_results(results):
        excerpts = []
        for result in results[:5]:
            snippet = result.get("snippet", "").strip()
            if snippet:
                excerpts.append(
                    f"• {result['title']}\n{snippet}\nSource : {result['url']}"
                )
        if not excerpts:
            return (
                "Je n’ai pas trouvé de réponse exploitable dans les sources Web "
                "consultées. Essaie de reformuler ta question."
            )
        return (
            "Voici les informations trouvées en ligne :\n\n"
            + "\n\n".join(excerpts)
            + "\n\nCes extraits viennent des sources citées ci-dessus."
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

    def request_stop(self):
        self._speech_stop_event.set()

    def speak(self, text):
        self._speech_stop_event.clear()
        speech_text = re.sub(r"https?://\S+", "", text)
        speech_text = re.sub(r"(?i)\bsource\s*:\s*", "", speech_text)
        neural_error = None
        try:
            self._speak_neural(speech_text)
            return ""
        except Exception as exc:
            neural_error = exc

        try:
            self._speak_local(speech_text)
            return (
                "La voix neuronale en ligne était indisponible ; "
                "la voix Windows locale a été utilisée."
            )
        except Exception as exc:
            return (
                f"La synthèse vocale est indisponible (voix en ligne : "
                f"{neural_error} ; voix locale : {exc})."
            )

    def _speak_neural(self, text):
        import edge_tts

        voice = self.config.get("neural_voice", "fr-FR-DeniseNeural")
        rate = self.config.get("neural_rate", "+0%")
        pitch = self.config.get("neural_pitch", "-2Hz")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_path = Path(audio_file.name)
        try:
            asyncio.run(
                edge_tts.Communicate(
                    text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume="+0%",
                ).save(str(audio_path))
            )
            self._play_mp3(audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

    def _play_mp3(self, audio_path):
        try:
            winmm = ctypes.WinDLL("winmm")
        except AttributeError as exc:
            raise OSError(
                "La lecture audio MP3 de Boogie est configurée pour Windows."
            ) from exc
        send_command = winmm.mciSendStringW
        send_command.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_void_p,
        ]
        send_command.restype = ctypes.c_uint
        get_error = winmm.mciGetErrorStringW
        get_error.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
        get_error.restype = ctypes.c_int
        alias = f"boogietts{threading.get_ident()}"

        def send(command):
            error_code = send_command(command, None, 0, None)
            if error_code:
                message = ctypes.create_unicode_buffer(256)
                get_error(error_code, message, len(message))
                raise OSError(message.value or f"Erreur MCI {error_code}")

        opened = False
        try:
            send(f'open "{audio_path}" type mpegvideo alias {alias}')
            opened = True

            def play_audio():
                send(f"play {alias} wait")

            player = threading.Thread(target=play_audio, daemon=True)
            player.start()
            while player.is_alive():
                if self._speech_stop_event.is_set():
                    send(f"stop {alias}")
                    send(f"close {alias}")
                    opened = False
                    return
                time.sleep(0.05)
        finally:
            if opened:
                send(f"close {alias}")

    def _speak_local(self, text):
        import pyttsx3

        speaker = pyttsx3.init()
        try:
            speaker.setProperty("rate", self.config.get("voice_rate", 145))
            speaker.setProperty("volume", 0.88)
            voices = speaker.getProperty("voices")
            female_voices = [
                voice
                for voice in voices
                if str(getattr(voice, "gender", "")).casefold() == "female"
            ]
            configured_name = self.config.get("voice_name", "").strip()
            if configured_name:
                selected_voice = next(
                    (
                        voice
                        for voice in female_voices
                        if _normalize(configured_name)
                        in _normalize(f"{voice.id} {voice.name}")
                    ),
                    None,
                )
                if selected_voice is None:
                    raise RuntimeError(
                        f"La voix féminine configurée « {configured_name} » "
                        "n’est pas installée."
                    )
            else:
                selected_voice = next(
                    (
                        voice
                        for voice in female_voices
                        if "fr" in _normalize(
                            " ".join(str(language) for language in voice.languages)
                        )
                    ),
                    None,
                )
                if selected_voice is None and female_voices:
                    selected_voice = female_voices[0]
            if selected_voice is None:
                raise RuntimeError(
                    "Aucune voix féminine n’est installée dans Windows."
                )
            speaker.setProperty("voice", selected_voice.id)
            speaker.say(text)

            def run_speech():
                speaker.runAndWait()

            worker = threading.Thread(target=run_speech, daemon=True)
            worker.start()
            while worker.is_alive():
                if self._speech_stop_event.is_set():
                    speaker.stop()
                    return
                time.sleep(0.05)
        finally:
            speaker.stop()
