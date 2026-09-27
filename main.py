import sounddevice as sd
import vosk
import json
import queue
import pyttsx3
import subprocess
import time
import threading

from interface import BoogieInterface

WAKE_WORD = "boogie"

engine = pyttsx3.init()
engine.setProperty('rate', 175)

def speak(text):
    engine.say(text)
    engine.runAndWait()

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

def listen_vosk(model):
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        rec = vosk.KaldiRecognizer(model, 16000)
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if "text" in result:
                    return result["text"].lower()

# ---------------------------
# INTERFACE SPIDER-MAN TASM2
# ---------------------------

ui = None

def start_ui():
    global ui
    ui = BoogieInterface()
    ui.show()

ui_thread = threading.Thread(target=start_ui)
ui_thread.start()

# ---------------------------
# ASSISTANT VOCAL
# ---------------------------

def main():
    model = vosk.Model("models/vosk_fr")
    speak("Boogie est en ligne bro.")

    while True:
        ui.set_listening()
        print("En écoute...")
        text = listen_vosk(model)
        print("Tu as dit :", text)

        if WAKE_WORD in text:
            ui.set_speaking()
            speak("Oui bro ?")
            time.sleep(0.3)

            ui.set_processing()
            command = listen_vosk(model)
            print("Commande :", command)

            if any(phrase in command for phrase in [
                "boogie stop", "stop", "arrête toi", "arrete toi",
                "boogie arrête toi", "boogie arrete toi",
                "boogie arrête", "boogie arrete",
                "arrête", "arrete"
            ]):
                ui.set_speaking()
                speak("Je me coupe bro.")
                break

            elif "ouvre chrome" in command:
                ui.set_speaking()
                speak("J'ouvre Chrome bro.")
                subprocess.Popen("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")

            else:
                ui.set_speaking()
                speak("J'ai pas compris bro.")

        ui.set_idle()

if __name__ == "__main__":
    main()
