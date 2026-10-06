import html
from pathlib import Path

from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

class BoogieInterface(QWidget):
    send_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Boogie — Assistant personnel")
        self.resize(920, 820)
        self.setMinimumSize(680, 620)
        self.setStyleSheet(
            """
            QWidget { color: #eaf7ff; font-family: "Segoe UI"; }
            QPushButton {
                background: #102847; border: 1px solid #176b9b; border-radius: 10px;
                padding: 10px 14px; color: #eaf7ff; font-weight: 600;
            }
            QPushButton:hover { background: #173c60; border-color: #00c9ff; }
            QPushButton:disabled { color: #71859a; border-color: #304255; }
            QLineEdit {
                background: rgba(4, 15, 31, 225); border: 1px solid #237db0;
                border-radius: 12px; padding: 13px; selection-background-color: #00a8e8;
            }
            QTextBrowser {
                background: rgba(3, 12, 27, 205); border: 1px solid rgba(38, 120, 168, 150);
                border-radius: 14px; padding: 14px;
            }
            """
        )

        self.background = QLabel(self)
        self.background_pixmap = QPixmap(
            str(Path(__file__).resolve().parent / "assets" / "background.png")
        )
        self._scale_background()
        self.background.lower()
        self.background_effect = QGraphicsOpacityEffect(self.background)
        self.background_effect.setOpacity(0.3)
        self.background.setGraphicsEffect(self.background_effect)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.logo = QLabel()
        logo = QPixmap(str(Path(__file__).resolve().parent / "assets" / "logo.png"))
        if not logo.isNull():
            self.logo.setPixmap(logo.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setFixedSize(82, 82)
        self.logo.setAlignment(Qt.AlignCenter)
        header.addWidget(self.logo)

        title_block = QVBoxLayout()
        title = QLabel("BOOGIE")
        title.setStyleSheet(
            "color: #f4faff; font-size: 28px; font-weight: 800; letter-spacing: 5px;"
        )
        subtitle = QLabel("TON ASSISTANT PERSONNEL  ·  LOCAL & CONNECTÉ")
        subtitle.setStyleSheet("color: #84b8d6; font-size: 10px; letter-spacing: 1px;")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()

        self.status = QLabel("En attente…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color: #70e6ff; background: rgba(2, 19, 37, 210); "
            "border: 1px solid #176b9b; border-radius: 12px; padding: 8px 13px;"
        )
        header.addWidget(self.status)
        layout.addLayout(header)

        self.logo_effect = QGraphicsOpacityEffect()
        self.logo.setGraphicsEffect(self.logo_effect)
        self.logo_effect.setOpacity(1.0)

        self.pulse = QLabel(self)
        pulse = QPixmap(str(Path(__file__).resolve().parent / "assets" / "pulse.png"))
        self.pulse.setPixmap(
            pulse.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.pulse.setFixedSize(52, 52)
        self.pulse.setAlignment(Qt.AlignCenter)
        self.pulse.hide()
        header.addWidget(self.pulse)
        self.pulse_effect = QGraphicsOpacityEffect(self.pulse)
        self.pulse.setGraphicsEffect(self.pulse_effect)
        self.pulse_animation = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(0.35)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)

        tagline = QLabel("Une question, une recherche ou une action sur ton PC ?")
        tagline.setStyleSheet("color: #a8cce0; font-size: 14px; padding: 2px 4px;")
        layout.addWidget(tagline)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setMinimumHeight(300)
        layout.addWidget(self.chat, 1)

        examples = QHBoxLayout()
        for prompt in (
            "Ouvre un nouvel onglet Chrome",
            "Cherche sur Google les actualités tech",
            "Mets Daft Punk sur Spotify",
        ):
            button = QPushButton(prompt)
            button.clicked.connect(lambda _checked=False, text=prompt: self.send_requested.emit(text))
            examples.addWidget(button)
        layout.addLayout(examples)

        composer = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Écris à Boogie…")
        self.input.returnPressed.connect(self._send_text)
        composer.addWidget(self.input, 1)
        self.mic_button = QPushButton("🎙  Démarrage…")
        self.mic_button.setMinimumWidth(170)
        self.mic_button.setDisabled(True)
        composer.addWidget(self.mic_button)
        self.send_button = QPushButton("Envoyer")
        self.send_button.setMinimumWidth(96)
        self.send_button.clicked.connect(self._send_text)
        composer.addWidget(self.send_button)
        layout.addLayout(composer)

        footer = QLabel(
            "Voix et modèle IA locaux · Les recherches Web nécessitent Internet"
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #7494aa; font-size: 10px;")
        layout.addWidget(footer)

    def _send_text(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.send_requested.emit(text)

    def add_message(self, speaker, text):
        safe_text = html.escape(text).replace("\n", "<br>")
        if speaker == "user":
            label = "TOI"
            color = "#77dfff"
            alignment = "right"
        else:
            label = "BOOGIE"
            color = "#ff6a73"
            alignment = "left"
        self.chat.append(
            f'<p style="text-align:{alignment}; margin:10px 3px 3px;">'
            f'<span style="color:{color}; font-size:10px; letter-spacing:2px;">{label}</span>'
            f'<br><span style="color:#ecf7ff; font-size:14px; line-height:1.5;">'
            f"{safe_text}</span></p>"
        )
        self.chat.moveCursor(QTextCursor.End)

    def set_status(self, text):
        self.status.setText(text)
        color = "#70e6ff"
        if "écout" in text.casefold():
            color = "#55e3a4"
        elif "erreur" in text.casefold() or "indisponible" in text.casefold():
            color = "#ff7b82"
        self.status.setStyleSheet(
            f"color: {color}; background: rgba(2, 19, 37, 210); "
            f"border: 1px solid #176b9b; border-radius: 12px; padding: 8px 13px;"
        )

    def set_listening(self, listening):
        self.mic_button.setText(
            "🎙  Toujours à l’écoute" if listening else "🎙  Micro inactif"
        )
        self.mic_button.setDisabled(True)
        if listening:
            self.pulse.show()
            self.pulse_animation.start()
            self.logo_effect.setOpacity(0.7)
        else:
            self.pulse_animation.stop()
            self.pulse.hide()
            self.logo_effect.setOpacity(1.0)

    def set_busy(self, busy):
        self.send_button.setDisabled(busy)
        self.input.setDisabled(busy)

    def _scale_background(self):
        self.background.setGeometry(self.rect())
        if not self.background_pixmap.isNull():
            self.background.setPixmap(
                self.background_pixmap.scaled(
                    self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
            )

    def resizeEvent(self, event):
        self._scale_background()
        super().resizeEvent(event)
