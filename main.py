import sys
import re
import time
from collections import deque
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from commands import AssistantEngine
from interface import BoogieInterface


def extract_wake_command(phrase):
    normalized = (phrase or "").strip()
    if not normalized:
        return None

    wake_patterns = [
        r"boogie",
        r"bougui",
        r"bougie",
        r"j\s*o\s*j\s*o",
        r"d\s*j\s*o\s*d\s*j\s*o",
        r"d\s*j\s*o\s*\s*d\s*j\s*o",
        r"j\s*o\s*d\s*j\s*o",
        r"g\s*o\s*a\s*t",
    ]
    for pattern in wake_patterns:
        match = re.search(rf"^(?:{pattern})(?:\s+(.*)|\s*$)", normalized, re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip(" ,.!?;:")

    for pattern in wake_patterns:
        match = re.search(rf"(?:^|\s)(?:{pattern})(?:\s+(.*)|\s*$)", normalized, re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip(" ,.!?;:")

    return None


class SpeechWorker(QThread):
    recognized = pyqtSignal(str)
    wake_detected = pyqtSignal()
    status_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model_path, command_timeout=10):
        super().__init__()
        self.model_path = model_path
        self.command_timeout = command_timeout
        self._stop_requested = False
        self._whisper_model = None
        self._command_buffer = bytearray()

    def stop(self):
        self._stop_requested = True

    def _load_whisper(self):
        if self._whisper_model is not None:
            return self._whisper_model

        try:
            import whisper

            self._whisper_model = whisper.load_model("small", device="cpu")
            self.status_changed.emit("Transcription Whisper prête — meilleure compréhension")
            return self._whisper_model
        except Exception as exc:
            self._whisper_model = False
            self.status_changed.emit(f"Whisper indisponible : {exc}")
            return None

    def _transcribe_command_with_whisper(self):
        if not self._command_buffer:
            return None

        model = self._load_whisper()
        if model is None:
            return None

        try:
            import numpy as np

            audio = np.frombuffer(bytes(self._command_buffer), dtype=np.int16).astype(np.float32)
            audio = audio / 32768.0
            result = model.transcribe(audio, fp16=False, language="fr")
            text = result.get("text", "").strip() if isinstance(result, dict) else ""
            if not text:
                segments = result.get("segments", []) if isinstance(result, dict) else []
                text = " ".join(
                    segment.get("text", "")
                    for segment in segments
                    if isinstance(segment, dict)
                ).strip()
            cleaned = AssistantEngine._clean_recognized_text(text)
            return cleaned or None
        except Exception as exc:
            self.status_changed.emit(f"Whisper a échoué : {exc}")
            return None

    def run(self):
        import json
        import queue

        if not self.model_path.is_dir():
            self.failed.emit(
                "Le modèle vocal français est introuvable dans models/vosk_fr."
            )
            return

        audio_queue = queue.Queue()

        def collect_audio(indata, _frames, _time_info, status):
            if status:
                self.status_changed.emit(f"Audio : {status}")
            audio_queue.put(bytes(indata))

        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model

            self.status_changed.emit("Chargement du modèle vocal local…")
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, 16000)
            self.status_changed.emit("Wake word actif — dis « Jojo » ou « Goat »")
            awaiting_command = False
            command_deadline = 0.0

            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=collect_audio,
            ):
                while not self._stop_requested:
                    try:
                        audio = audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        continue

                    if awaiting_command:
                        self._command_buffer.extend(audio)

                    if recognizer.AcceptWaveform(audio):
                        phrase = json.loads(recognizer.Result()).get("text", "").strip()
                        if not phrase:
                            continue

                        phrase = AssistantEngine._clean_recognized_text(phrase)
                        if not phrase:
                            recognizer.Reset()
                            continue

                        if awaiting_command:
                            whisper_text = self._transcribe_command_with_whisper()
                            final_command = whisper_text or phrase
                            self._command_buffer.clear()
                            awaiting_command = False
                            self.recognized.emit(final_command)
                            recognizer.Reset()
                            continue

                        command = extract_wake_command(phrase)
                        if command is None:
                            recognizer.Reset()
                            continue

                        if command:
                            self.recognized.emit(command)
                        else:
                            awaiting_command = True
                            self._command_buffer.clear()
                            command_deadline = time.monotonic() + self.command_timeout
                            self.wake_detected.emit()
                            self.status_changed.emit("Je t’écoute…")
                        recognizer.Reset()
                    if awaiting_command and time.monotonic() >= command_deadline:
                        whisper_text = self._transcribe_command_with_whisper()
                        final_command = whisper_text or ""
                        self._command_buffer.clear()
                        awaiting_command = False
                        self.status_changed.emit("Wake word actif — dis « Jojo » ou « Goat »")
                        recognizer.Reset()
                        if final_command:
                            self.recognized.emit(final_command)
        except Exception as exc:
            self.failed.emit(f"Écoute indisponible : {exc}")


class AssistantWorker(QThread):
    status_changed = pyqtSignal(str)
    completed = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, engine, prompt="", acknowledge=False, mode="assistant", voice_enabled=True):
        super().__init__()
        self.engine = engine
        self.prompt = prompt
        self.acknowledge = acknowledge
        self.mode = mode
        self.voice_enabled = voice_enabled

    def run(self):
        try:
            if self.acknowledge:
                if self.voice_enabled:
                    warning = self.engine.speak("Oui, je t’écoute.")
                    self.completed.emit("", warning)
                else:
                    self.completed.emit("", "")
                return
            answer = self.engine.process(
                self.prompt,
                self.status_changed.emit,
                mode=self.mode,
            )
            self.status_changed.emit("Je te réponds…")
            self.completed.emit(answer, "")
            if self.voice_enabled:
                speech_warning = self.engine.speak(answer)
                if speech_warning:
                    self.completed.emit("", speech_warning)
        except Exception as exc:
            self.failed.emit(f"Je n’ai pas pu traiter ta demande : {exc}")


class BoogieApp:
    def __init__(self):
        self.mode = "conversation"
        self.voice_enabled = True
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.stop_workers)
        self.engine = AssistantEngine(Path(__file__).resolve().parent)
        self.window = BoogieInterface(self.engine.voice_profile)
        icon_path = Path(__file__).resolve().parent / "assets" / "logo.png"
        if icon_path.is_file():
            self.app.setWindowIcon(QIcon(str(icon_path)))
        self.speech_worker = None
        self.assistant_worker = None
        self.pending_requests = deque()
        self.assistant_busy = False
        self.speech_available = False

        self.window.send_requested.connect(self.handle_prompt)
        self.window.voice_changed.connect(self.on_voice_changed)
        self.window.mode_changed.connect(self.set_mode)
        self.window.voice_toggled.connect(self.set_voice_enabled)
        self.window.set_listening(True)
        self.window.set_mode(self.mode)
        self.window.set_voice_enabled(self.voice_enabled)
        self.window.set_status("Démarrage de l’écoute locale…")
        self.window.add_message(
            "assistant",
            "Salut, moi c’est Boogie (Bougui). Mon micro reste actif tant que "
            "l’application est ouverte. Dis « Jojo », « Djodjo » ou « Goat », "
            "puis ta demande. Tu peux aussi m’écrire ici.",
        )
        self.window.show()
        model_path = Path(__file__).resolve().parent / "models" / "vosk_fr"
        self.speech_worker = SpeechWorker(model_path)
        self.speech_worker.recognized.connect(self.on_speech_recognized)
        self.speech_worker.wake_detected.connect(self.on_wake_detected)
        self.speech_worker.status_changed.connect(self.on_speech_status)
        self.speech_worker.failed.connect(self.on_speech_failed)
        self.speech_worker.start()

    def set_mode(self, mode):
        normalized_mode = "conversation"
        self.mode = normalized_mode
        self.window.set_mode(normalized_mode)

    def set_voice_enabled(self, enabled):
        self.voice_enabled = bool(enabled)
        self.window.set_voice_enabled(self.voice_enabled)
        if self.voice_enabled:
            self.window.set_status("Retour vocal activé")
        else:
            self.window.set_status("Retour vocal désactivé")

    def on_voice_changed(self, profile):
        try:
            self.engine.set_voice_profile(profile)
        except (OSError, ValueError) as exc:
            self.window.add_message(
                "assistant",
                f"Le profil vocal n’a pas pu être enregistré : {exc}",
            )
            self.window.voice_combo.blockSignals(True)
            self.window.voice_combo.setCurrentIndex(
                self.window.voice_combo.findData(self.engine.voice_profile)
            )
            self.window.voice_combo.blockSignals(False)
            return
        self.window.set_status("Profil vocal enregistré")

    def on_speech_recognized(self, phrase):
        cleaned = phrase.strip()
        if self.assistant_busy and cleaned.casefold() in {"stop", "boogie stop"}:
            self.window.trigger_pulse(220)
            self.stop_current_response()
            return
        self.window.trigger_pulse(350)
        self.handle_prompt(phrase, from_voice=True)

    def on_wake_detected(self):
        self.window.trigger_pulse(420)
        self.enqueue_request("", acknowledge=True)

    def on_speech_failed(self, message):
        self.speech_available = False
        self.window.set_listening(False)
        self.window.set_status("Micro indisponible")
        self.window.add_message("assistant", message)

    def on_speech_status(self, status):
        if status.startswith("Wake word actif"):
            self.speech_available = True
        self.window.set_status(status)

    def handle_prompt(self, prompt, from_voice=False):
        prompt = prompt.strip()
        if not prompt:
            return
        self.window.add_message("user", prompt)
        self.enqueue_request(prompt)

    def enqueue_request(self, prompt, acknowledge=False):
        self.pending_requests.append((prompt, acknowledge))
        self._start_next_request()

    def _start_next_request(self):
        if self.assistant_busy or not self.pending_requests:
            return
        prompt, acknowledge = self.pending_requests.popleft()
        self.assistant_busy = True
        if acknowledge:
            self.window.set_status("Je t’écoute…")
        else:
            self.window.set_busy(True)
            self.window.set_status("Je réfléchis…")
        self.assistant_worker = AssistantWorker(
            self.engine,
            prompt,
            acknowledge=acknowledge,
            mode=self.mode,
            voice_enabled=self.voice_enabled,
        )
        self.assistant_worker.status_changed.connect(self.window.set_status)
        self.assistant_worker.completed.connect(self.on_answer)
        self.assistant_worker.failed.connect(self.on_answer_failed)
        self.assistant_worker.start()

    def on_answer(self, answer, speech_warning):
        if answer:
            self.window.add_message("assistant", answer)
        if speech_warning:
            self.window.add_message("assistant", speech_warning)
        self.assistant_busy = False
        self.window.set_busy(False)
        if not self.pending_requests:
            status = (
                "Wake word actif — dis « Jojo » ou « Goat »"
                if self.speech_available
                else "Micro indisponible"
            )
            self.window.set_status(status)
        self._start_next_request()

    def on_answer_failed(self, message):
        self.window.add_message("assistant", message)
        self.window.set_status("Une erreur est survenue")
        self.assistant_busy = False
        self.window.set_busy(False)
        self._start_next_request()

    def stop_current_response(self):
        if self.engine is not None:
            self.engine.request_stop()
        self.window.set_status("Arrêt de la réponse…")

    def stop_workers(self):
        if self.speech_worker and self.speech_worker.isRunning():
            self.speech_worker.stop()
            self.speech_worker.wait()
        if self.assistant_worker and self.assistant_worker.isRunning():
            self.assistant_worker.wait()

    def run(self):
        return self.app.exec_()


if __name__ == "__main__":
    sys.exit(BoogieApp().run())
