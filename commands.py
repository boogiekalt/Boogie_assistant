import json
import asyncio
import ctypes
import difflib
import os
from collections import deque
import re
import shutil
import subprocess
import tempfile
import threading
import time
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


VOICE_PROFILES = {
    "female_natural": {
        "label": "Féminine · naturelle",
        "neural_voice": "fr-FR-DeniseNeural",
        "neural_rate": "+8%",
        "neural_pitch": "+0Hz",
        "voice_gender": "female",
        "voice_rate": 180,
    },
    "male_natural": {
        "label": "Masculine · naturelle",
        "neural_voice": "fr-FR-HenriNeural",
        "neural_rate": "+8%",
        "neural_pitch": "+0Hz",
        "voice_gender": "male",
        "voice_rate": 180,
    },
    "high_comic": {
        "label": "Aiguë · comique",
        "neural_voice": "fr-FR-DeniseNeural",
        "neural_rate": "+25%",
        "neural_pitch": "+35Hz",
        "voice_gender": "female",
        "voice_rate": 220,
    },
    "deep_robotic": {
        "label": "Grave · robotique",
        "neural_voice": "fr-FR-HenriNeural",
        "neural_rate": "-8%",
        "neural_pitch": "-18Hz",
        "voice_gender": "male",
        "voice_rate": 160,
    },
}

VOICE_TERM_ALIASES = {
    "spotifai": "spotify",
    "spotifaille": "spotify",
    "spotifi": "spotify",
    "sportify": "spotify",
    "robloque": "roblox",
    "robloxe": "roblox",
    "robloks": "roblox",
    "robloc": "roblox",
    "stime": "steam",
    "steem": "steam",
    "mine craft": "minecraft",
    "minekraft": "minecraft",
    "fort night": "fortnite",
    "tayleur swift": "taylor swift",
    "tayleur swifte": "taylor swift",
    "tailor swift": "taylor swift",
    "tailleur swift": "taylor swift",
    "taylor swifte": "taylor swift",
    "taylors swift": "taylor swift",
    "the week end": "the weeknd",
    "week end": "weeknd",
    "bee yonce": "beyonce",
    "beyonsay": "beyonce",
    "ariana grandeh": "ariana grande",
    "billie eilishh": "billie eilish",
    "dua leepa": "dua lipa",
    "justin bieberr": "justin bieber",
    "rihanna": "rihanna",
    "rihannaah": "rihanna",
    "bruno marss": "bruno mars",
    "lady gagga": "lady gaga",
    "michael jacksonn": "michael jackson",
    "selena gomezz": "selena gomez",
    "shak ira": "shakira",
    "ed sheerann": "ed sheeran",
    "bad bounny": "bad bunny",
}
KNOWN_VOICE_TERMS = (
    "spotify",
    "roblox",
    "steam",
    "minecraft",
    "fortnite",
    "valorant",
    "league",
    "legends",
    "call",
    "duty",
    "taylor",
    "swift",
    "weeknd",
    "beyonce",
    "ariana",
    "grande",
    "billie",
    "eilish",
    "dua",
    "lipa",
    "justin",
    "bieber",
    "rihanna",
    "drake",
    "bruno",
    "mars",
    "lady",
    "gaga",
    "michael",
    "jackson",
    "selena",
    "gomez",
    "shakira",
    "eminem",
)


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _correct_known_terms(text):
    for misheard, corrected in VOICE_TERM_ALIASES.items():
        text = re.sub(
            rf"\b{re.escape(misheard)}\b",
            corrected,
            text,
        )

    words = text.split()
    for index, word in enumerate(words):
        if len(word) < 4:
            continue
        closest = difflib.get_close_matches(
            word,
            KNOWN_VOICE_TERMS,
            n=1,
            cutoff=0.82,
        )
        if closest and abs(len(word) - len(closest[0])) <= 2:
            words[index] = closest[0]
    return " ".join(words)


def _clean_recognized_text(text):
    if text is None:
        return ""
    cleaned = _normalize(text)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s'-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = _correct_known_terms(cleaned)

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
        self.conversation_history = deque(maxlen=8)

    def _load_config(self):
        config_path = self.project_dir / "boogie_config.json"
        if not config_path.exists() or not config_path.read_text(encoding="utf-8").strip():
            return {}
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
        if not isinstance(config, dict):
            raise ValueError("boogie_config.json doit contenir un objet JSON.")
        return config

    @property
    def voice_profile(self):
        configured_profile = self.config.get("voice_profile")
        if isinstance(configured_profile, str) and configured_profile in VOICE_PROFILES:
            return configured_profile
        configured_voice = self.config.get("neural_voice", "fr-FR-DeniseNeural")
        return (
            "male_natural"
            if configured_voice == VOICE_PROFILES["male_natural"]["neural_voice"]
            else "female_natural"
        )

    def set_voice_profile(self, profile):
        if not isinstance(profile, str) or profile not in VOICE_PROFILES:
            raise ValueError(f"Profil vocal inconnu : {profile}")

        updated_config = {
            **self.config,
            **VOICE_PROFILES[profile],
            "voice_name": "",
            "voice_profile": profile,
        }
        config_path = self.project_dir / "boogie_config.json"
        config_path.write_text(
            json.dumps(updated_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.config = updated_config

    def process(self, prompt, status_callback=None, mode="assistant"):
        prompt = _correct_known_terms(_normalize(prompt))
        normalized = prompt

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

        if self._is_spotify_request(normalized):
            return self._open_spotify(prompt)
        if self._is_youtube_request(normalized):
            return self._open_youtube(prompt)
        if self._is_close_request(normalized):
            return self._close_app(prompt)
        if any(term in normalized for term in ("nouvel onglet", "ouvre chrome", "ouvre google")):
            return self._open_chrome(prompt)
        if normalized.startswith(("recherche ", "cherche sur google ", "fais une recherche")):
            return self._google_search(prompt)

        if mode == "conversation" and not self._is_direct_command(normalized):
            if status_callback is not None:
                status_callback("Je te réponds en conversation…")
            try:
                response = self._ask_local_model(prompt, [])
                self.conversation_history.append((prompt, response))
                return response
            except (OSError, urllib.error.URLError, TimeoutError, ValueError):
                response = self._fallback_conversation_reply(prompt)
                self.conversation_history.append((prompt, response))
                return response

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
    def _is_direct_command(normalized):
        return any(
            marker in normalized
            for marker in (
                "ouvre ",
                "cherche ",
                "recherche ",
                "google",
                "chrome",
                "spotify",
                "youtube",
                "meteo",
                "météo",
                "temps",
                "heure",
                "ferme",
                "stop",
            )
        )

    @staticmethod
    def _is_spotify_request(normalized):
        has_spotify = re.search(r"\bspotify\b", normalized)
        has_play_intent = re.search(
            r"\b(?:mets?|lance|joue|cherche|ecoute|ouvre|demarre)\b",
            normalized,
        )
        return bool(has_spotify and has_play_intent)

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
        normalized = _correct_known_terms(_normalize(prompt))
        match = re.search(
            r"\b(?:mets?|lance|joue|cherche|ecoute|ouvre|demarre)\b"
            r"\s+(?:moi\s+)?(.+?)"
            r"(?:\s+(?:sur|dans|avec)\s+spotify|\s+spotify\b)",
            normalized,
        )
        if match:
            query = match.group(1).strip()
        else:
            reversed_match = re.search(
                r"\bspotify\b[\s,;:.-]*(?:mets?|lance|joue|cherche|ecoute)"
                r"\s+(?:moi\s+)?(.+)$",
                normalized,
            )
            query = reversed_match.group(1).strip() if reversed_match else ""
        query = re.sub(
            r"^(?:(?:de\s+la\s+)?musique(?:\s+de)?|du\s+son(?:\s+de)?|"
            r"le\s+titre\s+de|la\s+chanson\s+de)\s+",
            "",
            query,
        ).strip()
        query = re.sub(
            r"\s+(?:s il te plait|s il vous plait|stp|svp)$",
            "",
            query,
        ).strip()
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
            ranked_results = []
            for result in results:
                title_terms = set(
                    re.findall(r"\w+", _normalize(result["title"]))
                )
                snippet_terms = set(
                    re.findall(r"\w+", _normalize(result.get("snippet", "")))
                )
                matching_terms = topic_terms & (title_terms | snippet_terms)
                if not matching_terms:
                    continue
                score = (
                    3 * len(topic_terms & title_terms)
                    + len(topic_terms & snippet_terms)
                )
                ranked_results.append(
                    (
                        score,
                        len(result.get("snippet", "")),
                        result,
                    )
                )
            ranked_results.sort(key=lambda item: (item[0], item[1]), reverse=True)
            results = [item[2] for item in ranked_results]
        return results[:5]

    @staticmethod
    def _clean_search_query(query):
        cleaned = _normalize(query).strip()
        cleaned = re.sub(
            r"^(?:dis moi|donne moi|indique moi|explique moi|parle moi de|"
            r"parle moi|parle de|raconte moi|"
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
            "sera", "demain", "aujourd", "hui", "parle", "raconte",
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

    def _fallback_conversation_reply(self, prompt):
        normalized = _normalize(prompt).casefold()
        if self.conversation_history:
            last_user, _ = self.conversation_history[-1]
            if any(term in normalized for term in ("qu est ce que je viens de te demander", "que je viens de te demander", "ce que je viens de te demander", "qu est ce que j ai dit", "ce que j ai dit")):
                return f"Tu viens de me demander : « {last_user} » ."
        if any(term in normalized for term in ("comment ca va", "comment sa va", "comment tu vas", "ca va", "comment allez vous")):
            return "Ça va, merci de demander. Et toi, comment se passe ta journée ?"
        if any(term in normalized for term in ("comment je m appelle", "tu sais comment je m appelle", "je m appelle")):
            return "Je ne peux pas savoir ton nom sans que tu me le dises. Comment tu t'appelles ?"
        if any(term in normalized for term in ("qui suis je", "qui je suis", "qui est ce que je suis")):
            return "Tu es l'utilisateur de cet assistant. Et moi, je suis là pour discuter avec toi et t'aider, pas seulement pour gérer ton ordinateur."
        if any(term in normalized for term in ("bonjour", "salut", "bonsoir")):
            return "Bonjour ! Ravi de te parler. En quoi puis-je t’aider aujourd’hui ?"
        if any(term in normalized for term in ("tu peux parler normalement", "parler normalement", "discussion", "comme une vraie ia", "comme un vrai assistant")):
            return "Oui, on peut parler normalement. Je peux discuter avec toi comme une vraie IA, répondre aux questions, expliquer des idées, et même t’aider quand tu veux."
        if "merci" in normalized:
            return "Avec plaisir. Tu veux aller plus loin sur un sujet ?"
        if "qu est ce que tu peux faire" in normalized or "que peux tu faire" in normalized:
            return "Je peux discuter avec toi, répondre à des questions, t’expliquer des sujets, et aussi t’aider à gérer ton ordinateur ou à faire des recherches quand besoin."
        if any(term in normalized for term in ("blague", "joke", "raconte", "dis quelque chose")):
            return "Pourquoi les développeurs aiment-ils les chats ? Parce qu’ils adorent le code source et les souris."
        return "Oui, bien sûr. On peut parler comme à un vrai chat : pose-moi une question, parle-moi d’un sujet, et je te répondrai naturellement."

    def _ask_local_model(self, prompt, results):
        endpoint = self.config.get("ollama_url", "http://127.0.0.1:11434")
        model = self.config.get("ollama_model", "llama3.2")
        sources = "\n".join(
            f"- {item['title']}: {item.get('snippet', '')} ({item['url']})"
            for item in results
        )
        context = sources or "Aucune source Web n’a été trouvée."
        recent_history = []
        if self.conversation_history:
            recent_history = [
                f"Utilisateur : {user}\nAssistant : {answer}"
                for user, answer in list(self.conversation_history)[-4:]
            ]
        recent_history_text = "\n\n".join(recent_history) if recent_history else "Aucun historique récent."
        payload = json.dumps(
            {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es Boogie, assistant francophone. Réponds en français, "
                            "de façon claire, structurée et concise. Tu peux discuter "
                            "naturellement comme une vraie IA. Gardez la mémoire des "
                            "échanges récents. Pour toute info factuelle récente, base-toi "
                            "sur le contexte Web fourni et cite les URLs pertinentes. "
                            "N’invente pas de sources. Si les sources ne suffisent pas, "
                            "dis-le."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question : {prompt}\n\nHistorique récent :\n{recent_history_text}\n\nContexte Web :\n{context}"
                        ),
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
        rate = self.config.get("neural_rate", "+12%")
        pitch = self.config.get("neural_pitch", "+2Hz")
        volume = self.config.get("neural_volume", "+12%")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_path = Path(audio_file.name)
        try:
            asyncio.run(
                edge_tts.Communicate(
                    text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume,
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

        def send(command, result_buffer=None):
            buffer_length = len(result_buffer) if result_buffer is not None else 0
            error_code = send_command(
                command,
                result_buffer,
                buffer_length,
                None,
            )
            if error_code:
                message = ctypes.create_unicode_buffer(256)
                get_error(error_code, message, len(message))
                raise OSError(message.value or f"Erreur MCI {error_code}")

        opened = False
        try:
            send(f'open "{audio_path}" type mpegvideo alias {alias}')
            opened = True
            send(f"play {alias}")
            while True:
                if self._speech_stop_event.is_set():
                    send(f"stop {alias}")
                    return
                mode = ctypes.create_unicode_buffer(32)
                send(f"status {alias} mode", mode)
                if mode.value.casefold() != "playing":
                    break
                time.sleep(0.05)
        finally:
            if opened:
                send(f"close {alias}")

    def _speak_local(self, text):
        import pyttsx3

        speaker = pyttsx3.init()
        try:
            speaker.setProperty("rate", self.config.get("voice_rate", 180))
            speaker.setProperty("volume", self.config.get("voice_volume", 1.0))
            voices = speaker.getProperty("voices")
            preferred_gender = self.config.get("voice_gender", "female").casefold()
            preferred_voices = [
                voice
                for voice in voices
                if str(getattr(voice, "gender", "")).casefold() == preferred_gender
            ]
            configured_name = self.config.get("voice_name", "").strip()
            if configured_name:
                selected_voice = next(
                    (
                        voice
                        for voice in preferred_voices
                        if _normalize(configured_name)
                        in _normalize(f"{voice.id} {voice.name}")
                    ),
                    None,
                )
                if selected_voice is None:
                    raise RuntimeError(
                        f"La voix configurée « {configured_name} » "
                        "n’est pas installée."
                    )
            else:
                selected_voice = next(
                    (
                        voice
                        for voice in preferred_voices
                        if "fr" in _normalize(
                            " ".join(str(language) for language in voice.languages)
                        )
                    ),
                    None,
                )
                if selected_voice is None and preferred_voices:
                    selected_voice = preferred_voices[0]
            if selected_voice is None:
                raise RuntimeError(
                    f"Aucune voix {preferred_gender} n’est installée dans Windows."
                )
            speaker.setProperty("voice", selected_voice.id)
            speaker.say(text)

            speech_errors = []

            def run_speech():
                try:
                    speaker.runAndWait()
                except Exception as exc:
                    speech_errors.append(exc)

            worker = threading.Thread(target=run_speech, daemon=True)
            worker.start()
            while worker.is_alive():
                if self._speech_stop_event.is_set():
                    speaker.stop()
                    return
                time.sleep(0.05)
            if speech_errors:
                raise RuntimeError(
                    f"La lecture de la voix Windows a échoué : {speech_errors[0]}"
                ) from speech_errors[0]
        finally:
            speaker.stop()
