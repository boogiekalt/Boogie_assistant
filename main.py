import sys
import re
import time
from collections import deque
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from commands import AssistantEngine
from interface import BoogieInterface


def extract_wake_command(phrase):
    match = re.search(r"\b(?:boogie|bougui|bougie)\b", phrase, re.IGNORECASE)
    if not match:
        return None
    return phrase[match.end():].strip(" ,.!?;:")


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

    def stop(self):
        self._stop_requested = True

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
            self.status_changed.emit("Wake word actif — dis « Boogie »")
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

                    if recognizer.AcceptWaveform(audio):
                        phrase = json.loads(recognizer.Result()).get("text", "").strip()
                        if not phrase:
                            continue

                        phrase = AssistantEngine._clean_recognized_text(phrase)
                        if not phrase:
                            recognizer.Reset()
                            continue

                        if awaiting_command:
                            command = extract_wake_command(phrase)
                            if command is None:
                                command = phrase
                            awaiting_command = False
                            self.recognized.emit(command)
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
                            command_deadline = time.monotonic() + self.command_timeout
                            self.wake_detected.emit()
                            self.status_changed.emit("Je t’écoute…")
                        recognizer.Reset()
                    if awaiting_command and time.monotonic() >= command_deadline:
                        awaiting_command = False
                        self.status_changed.emit("Wake word actif — dis « Boogie »")
                        recognizer.Reset()
        except Exception as exc:
            self.failed.emit(f"Écoute indisponible : {exc}")


class AssistantWorker(QThread):
    status_changed = pyqtSignal(str)
    completed = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, engine, prompt="", acknowledge=False):
        super().__init__()
        self.engine = engine
        self.prompt = prompt
        self.acknowledge = acknowledge

    def run(self):
        try:
            if self.acknowledge:
                warning = self.engine.speak("Oui, je t’écoute.")
                self.completed.emit("", warning)
                return
            answer = self.engine.process(self.prompt, self.status_changed.emit)
            self.status_changed.emit("Je te réponds…")
            speech_warning = self.engine.speak(answer)
            self.completed.emit(answer, speech_warning)
        except Exception as exc:
            self.failed.emit(f"Je n’ai pas pu traiter ta demande : {exc}")


class BoogieApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.aboutToQuit.connect(self.stop_workers)
        self.window = BoogieInterface()
        self.engine = AssistantEngine(Path(__file__).resolve().parent)
        self.speech_worker = None
        self.assistant_worker = None
        self.pending_requests = deque()
        self.assistant_busy = False
        self.speech_available = False

        self.window.send_requested.connect(self.handle_prompt)
        self.window.set_listening(True)
        self.window.set_status("Démarrage de l’écoute locale…")
        self.window.add_message(
            "assistant",
            "Salut, moi c’est Boogie (Bougui). Mon micro reste actif tant que "
            "l’application est ouverte. Dis « Boogie », puis ta demande. Tu peux "
            "aussi m’écrire ici.",
        )
        self.window.show()
        model_path = Path(__file__).resolve().parent / "models" / "vosk_fr"
        self.speech_worker = SpeechWorker(model_path)
        self.speech_worker.recognized.connect(self.on_speech_recognized)
        self.speech_worker.wake_detected.connect(self.on_wake_detected)
        self.speech_worker.status_changed.connect(self.on_speech_status)
        self.speech_worker.failed.connect(self.on_speech_failed)
        self.speech_worker.start()

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
        if from_voice:
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
            self.engine, prompt, acknowledge=acknowledge
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
                "Wake word actif — dis « Boogie »"
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
