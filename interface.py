from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt

class BoogieInterface(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Boogie Assistant")
        self.setFixedSize(350, 500)
        self.setStyleSheet("background-color: #0a1a2f; border-radius: 15px;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Logo Spider-Man stylisé
        self.logo = QLabel()
        self.logo.setPixmap(QPixmap("assets/logo.png").scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.logo)

        # Animation pulsante (écoute)
        self.pulse = QLabel()
        self.pulse.setPixmap(QPixmap("assets/pulse.png").scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.pulse)

        # Texte d'état
        self.status = QLabel("En attente...")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        self.setLayout(layout)

    def set_listening(self):
        self.status.setText("Écoute…")
        self.status.setStyleSheet("color: #00aaff; font-size: 22px; font-weight: bold;")

    def set_processing(self):
        self.status.setText("Analyse…")
        self.status.setStyleSheet("color: #ffaa00; font-size: 22px; font-weight: bold;")

    def set_speaking(self):
        self.status.setText("Réponse…")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")

    def set_idle(self):
        self.status.setText("En attente…")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")