import sys
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from commands import AssistantEngine
from interface import BoogieInterface


class SpeechWorker(QThread):
    recognized = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path
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

        def collect_audio(indata, frames, time_info, status):
            if status:
                self.status_changed.emit(f"Audio : {status}")
            audio_queue.put(bytes(indata))

        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model

            self.status_changed.emit("Chargement du modèle vocal local…")
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, 16000)
            self.status_changed.emit("Je t’écoute…")

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
                        if phrase:
                            self.recognized.emit(phrase)
                            return
        except Exception as exc:
            self.failed.emit(f"Écoute indisponible : {exc}")


class AssistantWorker(QThread):
    status_changed = pyqtSignal(str)
    completed = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, engine, prompt):
        super().__init__()
        self.engine = engine
        self.prompt = prompt

    def run(self):
        try:
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

        self.window.send_requested.connect(self.handle_prompt)
        self.window.listen_requested.connect(self.toggle_listening)
        self.window.set_status("Prêt — assistant local")
        self.window.add_message(
            "assistant",
            "Salut, moi c’est Boogie (Bougui). Écris-moi une demande ou active "
            "le micro pour me parler. Je peux chercher sur le Web et lancer "
            "quelques actions autorisées sur ton PC.",
        )
        self.window.show()

    def toggle_listening(self):
        if self.speech_worker and self.speech_worker.isRunning():
            self.speech_worker.stop()
            self.window.set_listening(False)
            self.window.set_status("Micro désactivé")
            return

        model_path = Path(__file__).resolve().parent / "models" / "vosk_fr"
        self.speech_worker = SpeechWorker(model_path)
        self.speech_worker.recognized.connect(self.on_speech_recognized)
        self.speech_worker.status_changed.connect(self.window.set_status)
        self.speech_worker.failed.connect(self.on_speech_failed)
        self.speech_worker.start()
        self.window.set_listening(True)

    def on_speech_recognized(self, phrase):
        if self.speech_worker and self.speech_worker.isRunning():
            self.speech_worker.stop()
        self.window.set_listening(False)
        self.handle_prompt(phrase)

    def on_speech_failed(self, message):
        self.window.set_listening(False)
        self.window.set_status("Micro indisponible")
        self.window.add_message("assistant", message)

    def handle_prompt(self, prompt):
        prompt = prompt.strip()
        if not prompt:
            return
        if self.speech_worker and self.speech_worker.isRunning():
            self.speech_worker.stop()
            self.window.set_listening(False)
        self.window.add_message("user", prompt)
        self.window.set_busy(True)
        self.window.set_status("Je réfléchis…")
        self.assistant_worker = AssistantWorker(self.engine, prompt)
        self.assistant_worker.status_changed.connect(self.window.set_status)
        self.assistant_worker.completed.connect(self.on_answer)
        self.assistant_worker.failed.connect(self.on_answer_failed)
        self.assistant_worker.start()

    def on_answer(self, answer, speech_warning):
        self.window.add_message("assistant", answer)
        if speech_warning:
            self.window.add_message("assistant", speech_warning)
        self.window.set_status("Prêt")
        self.window.set_busy(False)

    def on_answer_failed(self, message):
        self.window.add_message("assistant", message)
        self.window.set_status("Une erreur est survenue")
        self.window.set_busy(False)

    def stop_workers(self):
        for worker in (self.speech_worker, self.assistant_worker):
            if worker and worker.isRunning():
                if isinstance(worker, SpeechWorker):
                    worker.stop()
                worker.wait()

    def run(self):
        return self.app.exec_()


if __name__ == "__main__":
    sys.exit(BoogieApp().run())
