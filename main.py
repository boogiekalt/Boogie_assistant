import threading
from window import launch_ui
from interface import BoogieInterface

# --- Lancer l'interface dans un thread séparé ---
ui = None

def start_ui():
    global ui
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    ui = BoogieInterface()
    ui.show()
    app.exec_()

threading.Thread(target=start_ui, daemon=True).start()

# --- Ton assistant vocal ---
import time

def listen():
    time.sleep(2)
    return "boogie"

def speak(text):
    print("Boogie:", text)

# --- Boucle principale ---
while True:
    if ui:
        ui.set_idle()

    text = listen()

    if text == "boogie":
        ui.set_listening()
        time.sleep(1)

        ui.set_processing()
        time.sleep(1)

        ui.set_speaking()
        speak("Oui bro ?")

        time.sleep(1)
        ui.set_idle()
