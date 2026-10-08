import json
import sys
import threading
import tempfile
import time as time_module
import types
import urllib.error
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_qtcore = types.ModuleType("PyQt5.QtCore")
fake_qtcore.Qt = type(
    "Qt",
    (),
    {
        "KeepAspectRatio": 0,
        "SmoothTransformation": 0,
        "AlignCenter": 0,
        "NoPen": 0,
    },
)
class _Signal:
    def connect(self, *args, **kwargs):
        return None

fake_qtcore = types.ModuleType("PyQt5.QtCore")
fake_qtcore.Qt = type(
    "Qt",
    (),
    {
        "KeepAspectRatio": 0,
        "SmoothTransformation": 0,
        "AlignCenter": 0,
        "NoPen": 0,
    },
)
fake_qtcore.QThread = type("QThread", (), {})
fake_qtcore.QPropertyAnimation = type("QPropertyAnimation", (), {})
fake_qtcore.QRectF = type("QRectF", (), {})
fake_qtcore.QTimer = type("QTimer", (), {"__init__": lambda self, *args, **kwargs: None, "timeout": _Signal(), "start": lambda *args, **kwargs: None})
fake_qtcore.pyqtSignal = lambda *args, **kwargs: _Signal()

fake_qtgui = types.ModuleType("PyQt5.QtGui")
fake_qtgui.QColor = type("QColor", (), {})
fake_qtgui.QIcon = type("QIcon", (), {"__init__": lambda self, *args, **kwargs: None})
fake_qtgui.QPainter = type("QPainter", (), {})
fake_qtgui.QPen = type("QPen", (), {})
fake_qtgui.QPixmap = type("QPixmap", (), {"__init__": lambda self, *args, **kwargs: None, "isNull": lambda self: True})
fake_qtgui.QRadialGradient = type("QRadialGradient", (), {})
fake_qtgui.QTextCursor = type("QTextCursor", (), {})

fake_qtwidgets = types.ModuleType("PyQt5.QtWidgets")
fake_qtwidgets.QApplication = type("QApplication", (), {})
fake_qtwidgets.QFrame = type("QFrame", (), {"__init__": lambda self, *args, **kwargs: None, "setObjectName": lambda *args, **kwargs: None, "setFixedWidth": lambda *args, **kwargs: None, "setFixedSize": lambda *args, **kwargs: None, "setStyleSheet": lambda *args, **kwargs: None})
fake_qtwidgets.QComboBox = type("QComboBox", (), {"__init__": lambda self, *args, **kwargs: setattr(self, "_items", []), "addItem": lambda self, *args, **kwargs: self._items.append((args[0], args[1] if len(args) > 1 else None)), "findData": lambda self, value: next((index for index, (_, item_value) in enumerate(self._items) if item_value == value), 0), "setCurrentIndex": lambda self, index: setattr(self, "_current_index", index), "currentData": lambda self: self._items[self._current_index][1] if hasattr(self, "_current_index") and self._current_index < len(self._items) else None, "currentIndexChanged": _Signal()})
fake_qtwidgets.QGraphicsOpacityEffect = type("QGraphicsOpacityEffect", (), {"__init__": lambda self, *args, **kwargs: None, "setOpacity": lambda *args, **kwargs: None})
fake_qtwidgets.QHBoxLayout = type("QHBoxLayout", (), {"__init__": lambda self, *args, **kwargs: None, "setContentsMargins": lambda *args, **kwargs: None, "setSpacing": lambda *args, **kwargs: None, "addWidget": lambda *args, **kwargs: None, "addLayout": lambda *args, **kwargs: None, "addStretch": lambda *args, **kwargs: None})
fake_qtwidgets.QLabel = type("QLabel", (), {"__init__": lambda self, *args, **kwargs: None, "lower": lambda *args, **kwargs: None, "setGraphicsEffect": lambda *args, **kwargs: None, "setPixmap": lambda *args, **kwargs: None, "setFixedSize": lambda *args, **kwargs: None, "setAlignment": lambda *args, **kwargs: None, "setStyleSheet": lambda *args, **kwargs: None, "setObjectName": lambda *args, **kwargs: None, "setText": lambda self, value: setattr(self, "_text", value), "setWordWrap": lambda *args, **kwargs: None, "setMinimumHeight": lambda *args, **kwargs: None})
fake_qtwidgets.QLineEdit = type("QLineEdit", (), {"__init__": lambda self, *args, **kwargs: None, "setPlaceholderText": lambda *args, **kwargs: None, "setText": lambda self, value: setattr(self, "_text", value), "text": lambda self: getattr(self, "_text", ""), "clear": lambda *args, **kwargs: None})
fake_qtwidgets.QPushButton = type("QPushButton", (), {"__init__": lambda self, *args, **kwargs: None, "setMinimumWidth": lambda *args, **kwargs: None, "setMinimumHeight": lambda *args, **kwargs: None, "clicked": _Signal(), "setText": lambda self, value: setattr(self, "_text", value), "text": lambda self: getattr(self, "_text", ""), "setStyleSheet": lambda *args, **kwargs: None, "setEnabled": lambda *args, **kwargs: None, "setVisible": lambda self, value: setattr(self, "_visible", value), "isHidden": lambda self: not getattr(self, "_visible", True), "hide": lambda self: setattr(self, "_visible", False)})
fake_qtwidgets.QProgressBar = type("QProgressBar", (), {"__init__": lambda self, *args, **kwargs: None, "setTextVisible": lambda *args, **kwargs: None, "setRange": lambda *args, **kwargs: None, "setValue": lambda *args, **kwargs: None})
fake_qtwidgets.QTextBrowser = type("QTextBrowser", (), {"__init__": lambda self, *args, **kwargs: None, "setOpenExternalLinks": lambda *args, **kwargs: None, "setMinimumHeight": lambda *args, **kwargs: None, "setHtml": lambda *args, **kwargs: None, "setMaximumHeight": lambda *args, **kwargs: None, "setMinimumWidth": lambda *args, **kwargs: None, "setObjectName": lambda *args, **kwargs: None})
fake_qtwidgets.QVBoxLayout = type("QVBoxLayout", (), {"__init__": lambda self, *args, **kwargs: None, "setContentsMargins": lambda *args, **kwargs: None, "setSpacing": lambda *args, **kwargs: None, "addWidget": lambda *args, **kwargs: None, "addLayout": lambda *args, **kwargs: None, "addStretch": lambda *args, **kwargs: None})
fake_qtwidgets.QWidget = type("QWidget", (), {"__init__": lambda self, *args, **kwargs: None, "setWindowTitle": lambda *args, **kwargs: None, "setWindowIcon": lambda *args, **kwargs: None, "resize": lambda *args, **kwargs: None, "setMinimumSize": lambda *args, **kwargs: None, "setMaximumSize": lambda *args, **kwargs: None, "setFixedWidth": lambda *args, **kwargs: None, "setFixedSize": lambda *args, **kwargs: None, "setStyleSheet": lambda *args, **kwargs: None, "setObjectName": lambda *args, **kwargs: None, "show": lambda *args, **kwargs: None, "setVisible": lambda *args, **kwargs: None, "hide": lambda *args, **kwargs: None, "setLayout": lambda *args, **kwargs: None})

sys.modules.setdefault("PyQt5", types.ModuleType("PyQt5"))
sys.modules["PyQt5.QtCore"] = fake_qtcore
sys.modules["PyQt5.QtGui"] = fake_qtgui
sys.modules["PyQt5.QtWidgets"] = fake_qtwidgets

from commands import AssistantEngine
from interface import BoogieInterface
from main import AssistantWorker, BoogieApp, extract_wake_command


class AssistantEngineTest(unittest.TestCase):
    def test_it_extracts_jojo_wake_word_aliases(self):
        self.assertEqual("mets la musique", extract_wake_command("jojo mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("djodjo mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("djo djo mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("jodjo mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("goat mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("g oat mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("j o j o mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("g o a t mets la musique"))
        self.assertEqual("mets la musique", extract_wake_command("jo jo mets la musique"))

    def test_it_forces_conversation_mode(self):
        interface = BoogieInterface.__new__(BoogieInterface)
        interface.mode_button = type(
            "ModeButton",
            (),
            {
                "setText": lambda self, value: setattr(self, "_text", value),
                "text": lambda self: getattr(self, "_text", ""),
                "setStyleSheet": lambda *args, **kwargs: None,
                "setEnabled": lambda *args, **kwargs: None,
                "setVisible": lambda self, value: setattr(self, "_visible", value),
                "isHidden": lambda self: not getattr(self, "_visible", True),
            },
        )()
        interface.mode_button.setVisible(False)

        interface.set_mode("assistant")

        self.assertEqual("conversation", interface.mode_button.text().casefold().replace("mode · ", "").strip())
        self.assertTrue(interface.mode_button.isHidden())

    def test_it_displays_user_message_before_assistant_reply(self):
        app = BoogieApp.__new__(BoogieApp)
        app.pending_requests = deque()
        app.assistant_busy = False
        app.window = Mock()
        app.engine = Mock()
        app.mode = "conversation"
        app.voice_enabled = True
        app.speech_available = False

        with patch.object(BoogieApp, "_start_next_request") as start_next:
            app.handle_prompt("bonjour", from_voice=False)

        app.window.add_message.assert_any_call("user", "bonjour")
        self.assertEqual([("bonjour", False)], list(app.pending_requests))
        start_next.assert_called_once_with()

    def test_it_uses_local_model_for_conversation_mode(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with (
            patch.object(engine, "_search_web", return_value=[{"title": "x", "url": "https://example.com", "snippet": "x"}]) as search,
            patch.object(engine, "_ask_local_model", return_value="Je vais bien") as local_model,
        ):
            response = engine.process("comment ça va", mode="conversation")

        self.assertEqual("Je vais bien", response)
        self.assertFalse(search.called)
        local_model.assert_called_once_with("comment ca va", [])

    def test_it_falls_back_to_plain_chat_when_local_model_is_unavailable(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with (
            patch.object(engine, "_search_web", return_value=[{"title": "x", "url": "https://example.com", "snippet": "x"}]) as search,
            patch.object(engine, "_ask_local_model", side_effect=OSError("offline")),
        ):
            response = engine.process("comment ça va", mode="conversation")

        self.assertIn("ça va", response.casefold())
        self.assertFalse(search.called)

    def test_it_uses_chat_like_fallback_for_general_conversation(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with (
            patch.object(engine, "_search_web", return_value=[{"title": "x", "url": "https://example.com", "snippet": "x"}]) as search,
            patch.object(engine, "_ask_local_model", side_effect=OSError("offline")),
        ):
            response = engine.process("tu peux parler normalement avec moi ?", mode="conversation")

        self.assertIn("parler", response.casefold())
        self.assertIn("normalement", response.casefold())
        self.assertNotIn("ordinateur", response.casefold())
        self.assertFalse(search.called)

    def test_it_emits_answer_before_speaking(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])
        worker = AssistantWorker(engine, "bonjour")
        worker.status_changed = Mock()
        worker.completed = Mock()
        worker.failed = Mock()
        engine.process = Mock(return_value="Bonjour, comment ça va ?")
        engine.speak = Mock(return_value="")

        worker.run()

        self.assertEqual(
            ("Bonjour, comment ça va ?", ""),
            worker.completed.emit.call_args_list[0].args,
        )

    def test_it_skips_speech_when_voice_is_disabled(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])
        worker = AssistantWorker(engine, "bonjour", voice_enabled=False)
        worker.status_changed = Mock()
        worker.completed = Mock()
        worker.failed = Mock()
        engine.process = Mock(return_value="Bonjour, comment ça va ?")
        engine.speak = Mock(return_value="")

        worker.run()

        engine.speak.assert_not_called()
        self.assertEqual(
            ("Bonjour, comment ça va ?", ""),
            worker.completed.emit.call_args_list[0].args,
        )

    def test_it_remembers_recent_conversation_context(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with patch.object(engine, "_ask_local_model", side_effect=["Salut !", "Tu as demandé : comment ça va."]) as local_model:
            first = engine.process("bonjour", mode="conversation")
            second = engine.process("qu est ce que je viens de te demander", mode="conversation")

        self.assertEqual("Salut !", first)
        self.assertEqual("Tu as demandé : comment ça va.", second)
        self.assertEqual(2, len(engine.conversation_history))
        self.assertEqual(2, local_model.call_count)

    def test_it_persists_selected_voice_profile(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            engine = AssistantEngine(Path(temporary_directory))

            engine.set_voice_profile("male_natural")

            saved_config = json.loads(
                (Path(temporary_directory) / "boogie_config.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual("male_natural", saved_config["voice_profile"])
        self.assertEqual("fr-FR-HenriNeural", saved_config["neural_voice"])
        self.assertEqual("male", saved_config["voice_gender"])
        self.assertEqual("", saved_config["voice_name"])

    def test_it_rejects_unknown_voice_profile_without_changing_config(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            engine = AssistantEngine(Path(temporary_directory))

            with self.assertRaises(ValueError):
                engine.set_voice_profile("unknown")

            self.assertFalse(
                (Path(temporary_directory) / "boogie_config.json").exists()
            )

    def test_it_corrects_spoken_spotify_and_artist_names(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with patch("commands.webbrowser.open", return_value=True) as mock_open:
            result = engine.process(
                "mets de la musique de tayleur swifte sur spotifai"
            )

        self.assertIn("Spotify", result)
        self.assertIn(
            "taylor%20swift",
            mock_open.call_args.args[0],
        )

    def test_it_waits_for_spotify_voice_playback_without_name_error(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])
        winmm = Mock()
        commands = []
        thread_ids = []
        status_calls = 0

        def send_command(command, result_buffer, *_args):
            nonlocal status_calls
            commands.append(command)
            thread_ids.append(threading.get_ident())
            if command.startswith("status "):
                status_calls += 1
                result_buffer.value = "playing" if status_calls == 1 else "stopped"
            return 0

        winmm.mciSendStringW.side_effect = send_command
        with (
            patch("commands.ctypes.WinDLL", return_value=winmm),
            patch("commands.time.sleep", side_effect=time_module.sleep) as sleep,
        ):
            engine._play_mp3(Path("response.mp3"))

        self.assertTrue(sleep.called)
        self.assertEqual(thread_ids[0], thread_ids[1])
        self.assertIn("play boogietts", commands[1])

    def test_it_reports_spoken_audio_playback_errors(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])
        winmm = Mock()
        winmm.mciSendStringW.side_effect = (
            lambda command, *_args: 277 if command.startswith("play ") else 0
        )
        winmm.mciGetErrorStringW.side_effect = (
            lambda _code, buffer, _length: setattr(buffer, "value", "lecture impossible")
        )

        with patch("commands.ctypes.WinDLL", return_value=winmm):
            with self.assertRaisesRegex(OSError, "lecture impossible"):
                engine._play_mp3(Path("response.mp3"))

    def test_it_accepts_spotify_before_the_play_command(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with patch("commands.webbrowser.open", return_value=True) as mock_open:
            result = engine.process("Spotify, joue Rihanna")

        self.assertIn("Spotify", result)
        self.assertIn("rihanna", mock_open.call_args.args[0])

    def test_it_corrects_game_and_celebrity_names_for_web_search(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        for prompt, expected_term in (
            ("Qu'est-ce que robloque ?", "roblox"),
            ("Qui est bee yonce ?", "beyonce"),
        ):
            with self.subTest(prompt=prompt):
                with (
                    patch.object(engine, "_search_web", return_value=[]) as search,
                    patch.object(
                        engine, "_ask_local_model", return_value="Réponse"
                    ),
                ):
                    engine.process(prompt)

                self.assertIn(expected_term, search.call_args.args[0])

    def test_it_removes_question_words_from_web_search(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        self.assertEqual(
            "brad pitt",
            engine._clean_search_query("parle moi de brad pitt"),
        )

    def test_it_ranks_results_by_actual_topic_relevance(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])
        search_results = [
            {
                "title": "Accueil ou acceuil",
                "url": "https://example.com/accueil",
                "snippet": "Conseils sur les pages d'accueil.",
            },
            {
                "title": "Brad Pitt - Biographie",
                "url": "https://example.com/brad-pitt",
                "snippet": "Brad Pitt est un acteur américain.",
            },
        ]

        with (
            patch(
                "commands.urllib.request.urlopen",
                side_effect=urllib.error.URLError("offline"),
            ),
            patch.object(engine, "_search_wikipedia", return_value=search_results),
        ):
            results = engine._search_web("parle moi de brad pitt")

        self.assertEqual("Brad Pitt - Biographie", results[0]["title"])
        self.assertEqual(1, len(results))

    def test_it_opens_youtube_search_for_video_requests(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with patch("commands.webbrowser.open_new_tab", return_value=True) as mock_open:
            result = engine.process("lance une vidéo de squeezie sur yt")

        self.assertIn("YouTube", result)
        self.assertTrue(mock_open.called)
        opened_url = mock_open.call_args[0][0]
        self.assertIn("youtube.com/results", opened_url)
        self.assertIn("squeezie", opened_url.lower())

    def test_it_cleans_noisy_vosk_transcripts(self):
        cleaned = AssistantEngine._clean_recognized_text("cuisine sur youtube")
        self.assertIn("squeezie", cleaned.lower())

        cleaned = AssistantEngine._clean_recognized_text("epstein en et putain")
        self.assertEqual("epstein", cleaned.lower())

    def test_it_closes_edge_with_close_command(self):
        engine = AssistantEngine(Path(__file__).resolve().parents[1])

        with patch("commands.subprocess.run", return_value=type("R", (), {"returncode": 0})()) as mock_run:
            result = engine.process("ferme edge")

        self.assertIn("fermé Edge", result)
        self.assertTrue(mock_run.called)

    def test_it_stops_current_response_when_user_says_stop(self):
        app = BoogieApp.__new__(BoogieApp)
        app.assistant_busy = True
        app.engine = Mock()
        app.window = Mock()
        app.stop_current_response = Mock()

        app.on_speech_recognized("stop")

        app.stop_current_response.assert_called_once()


if __name__ == "__main__":
    unittest.main()
