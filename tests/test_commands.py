import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

fake_qtcore = types.ModuleType("PyQt5.QtCore")
fake_qtcore.Qt = type(
    "Qt",
    (),
    {"KeepAspectRatio": 0, "SmoothTransformation": 0, "AlignCenter": 0},
)
fake_qtcore.QThread = type("QThread", (), {})
fake_qtcore.QPropertyAnimation = type("QPropertyAnimation", (), {})
fake_qtcore.pyqtSignal = lambda *args, **kwargs: None

fake_qtgui = types.ModuleType("PyQt5.QtGui")
fake_qtgui.QPixmap = type("QPixmap", (), {"__init__": lambda self, *args, **kwargs: None, "isNull": lambda self: True})
fake_qtgui.QTextCursor = type("QTextCursor", (), {})

fake_qtwidgets = types.ModuleType("PyQt5.QtWidgets")
fake_qtwidgets.QApplication = type("QApplication", (), {})
fake_qtwidgets.QFrame = type("QFrame", (), {})
fake_qtwidgets.QGraphicsOpacityEffect = type("QGraphicsOpacityEffect", (), {"__init__": lambda self, *args, **kwargs: None, "setOpacity": lambda *args, **kwargs: None})
fake_qtwidgets.QHBoxLayout = type("QHBoxLayout", (), {"__init__": lambda self, *args, **kwargs: None, "setContentsMargins": lambda *args, **kwargs: None, "setSpacing": lambda *args, **kwargs: None, "addWidget": lambda *args, **kwargs: None, "addLayout": lambda *args, **kwargs: None, "addStretch": lambda *args, **kwargs: None})
fake_qtwidgets.QLabel = type("QLabel", (), {"__init__": lambda self, *args, **kwargs: None, "lower": lambda *args, **kwargs: None, "setGraphicsEffect": lambda *args, **kwargs: None, "setPixmap": lambda *args, **kwargs: None, "setFixedSize": lambda *args, **kwargs: None, "setAlignment": lambda *args, **kwargs: None, "setStyleSheet": lambda *args, **kwargs: None})
fake_qtwidgets.QLineEdit = type("QLineEdit", (), {})
fake_qtwidgets.QPushButton = type("QPushButton", (), {})
fake_qtwidgets.QTextBrowser = type("QTextBrowser", (), {"setOpenExternalLinks": lambda *args, **kwargs: None, "setMinimumHeight": lambda *args, **kwargs: None})
fake_qtwidgets.QVBoxLayout = type("QVBoxLayout", (), {"__init__": lambda self, *args, **kwargs: None, "setContentsMargins": lambda *args, **kwargs: None, "setSpacing": lambda *args, **kwargs: None, "addWidget": lambda *args, **kwargs: None, "addLayout": lambda *args, **kwargs: None})
fake_qtwidgets.QWidget = type("QWidget", (), {"__init__": lambda self, *args, **kwargs: None, "setWindowTitle": lambda *args, **kwargs: None, "resize": lambda *args, **kwargs: None, "setMinimumSize": lambda *args, **kwargs: None, "setStyleSheet": lambda *args, **kwargs: None, "show": lambda *args, **kwargs: None})

sys.modules.setdefault("PyQt5", types.ModuleType("PyQt5"))
sys.modules["PyQt5.QtCore"] = fake_qtcore
sys.modules["PyQt5.QtGui"] = fake_qtgui
sys.modules["PyQt5.QtWidgets"] = fake_qtwidgets

from commands import AssistantEngine
from main import BoogieApp


class AssistantEngineTest(unittest.TestCase):
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
