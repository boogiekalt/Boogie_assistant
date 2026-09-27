from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation

class BoogieInterface(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Boogie Assistant")
        self.setFixedSize(350, 500)
        self.setStyleSheet("background-color: #0a1a2f; border-radius: 15px;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # --- BACKGROUND ---
        self.background = QLabel(self)
        self.background.setPixmap(QPixmap("assets/background.png").scaled(
            350, 500, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        ))
        self.background.setGeometry(0, 0, 350, 500)
        self.background.lower()

        # --- LOGO ---
        self.logo = QLabel(self)
        self.logo.setPixmap(QPixmap("assets/logo.png").scaled(
            180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)

        # Glow du logo
        self.logo_effect = QGraphicsOpacityEffect()
        self.logo.setGraphicsEffect(self.logo_effect)
        self.logo_effect.setOpacity(1.0)

        # --- PULSE ---
        self.pulse = QLabel(self)
        self.pulse.setPixmap(QPixmap("assets/pulse.png").scaled(
            220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.pulse.setAlignment(Qt.AlignCenter)
        self.pulse.hide()
        layout.addWidget(self.pulse)

        # Animation du pulse
        self.pulse_effect = QGraphicsOpacityEffect()
        self.pulse.setGraphicsEffect(self.pulse_effect)

        self.pulse_animation = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_animation.setDuration(1200)
        self.pulse_animation.setStartValue(0.3)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)

        # --- TEXTE D'ÉTAT ---
        self.status = QLabel("En attente…")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

        self.setLayout(layout)

    # --- ÉTATS ---
    def set_listening(self):
        self.status.setText("Écoute…")
        self.status.setStyleSheet("color: #00aaff; font-size: 22px; font-weight: bold;")

        self.pulse.show()
        self.pulse_animation.start()

        self.logo_effect.setOpacity(0.7)

    def set_processing(self):
        self.status.setText("Analyse…")
        self.status.setStyleSheet("color: #ffaa00; font-size: 22px; font-weight: bold;")

        self.pulse_animation.stop()
        self.pulse.hide()

        self.logo_effect.setOpacity(0.5)

    def set_speaking(self):
        self.status.setText("Réponse…")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")

        self.pulse_animation.stop()
        self.pulse.hide()

        self.logo_effect.setOpacity(1.0)

    def set_idle(self):
        self.status.setText("En attente…")
        self.status.setStyleSheet("color: #e60000; font-size: 22px; font-weight: bold;")

        self.pulse_animation.stop()
        self.pulse.hide()

        self.logo_effect.setOpacity(1.0)

