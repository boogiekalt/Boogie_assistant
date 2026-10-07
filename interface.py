import html
from pathlib import Path

from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtSignal
from PyQt5.QtGui import QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QFrame,
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
        self.resize(1440, 860)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(
            """
            QWidget {
                color: #edfaff;
                font-family: "Segoe UI";
                background: transparent;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff2e57, stop:1 #d60035);
                border: 1px solid rgba(255,255,255,0.25);
                border-radius: 12px;
                padding: 10px 14px;
                color: #fff9ff;
                font-weight: 800;
                letter-spacing: 0.5px;
                box-shadow: 0 0 12px rgba(255, 60, 96, 0.45);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff4a73, stop:1 #eb133d);
            }
            QPushButton:disabled {
                color: #c9d6ea;
                background: rgba(115, 122, 135, 0.3);
                border: 1px solid rgba(255,255,255,0.08);
            }
            QLineEdit {
                background: rgba(6, 14, 25, 0.8);
                border: 1px solid rgba(90, 180, 255, 0.85);
                border-radius: 14px;
                padding: 13px 16px;
                color: #eefaff;
                selection-background-color: #61d8ff;
                box-shadow: inset 0 0 18px rgba(67, 140, 255, 0.2);
            }
            QTextBrowser {
                background: rgba(5, 12, 22, 0.7);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 18px;
                padding: 16px;
                color: #edfaff;
            }
            QLabel { color: #edfaff; }
            """
        )

        self.background = QLabel(self)
        self.background_pixmap = QPixmap(
            str(Path(__file__).resolve().parent / "assets" / "background.png")
        )
        self._scale_background()
        self.background.lower()
        self.background_effect = QGraphicsOpacityEffect(self.background)
        self.background_effect.setOpacity(0.12)
        self.background.setGraphicsEffect(self.background_effect)

        self.root = QWidget(self)
        self.root.setObjectName("rootPane")
        self.root.setStyleSheet(
            """
            QWidget#rootPane {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(8, 12, 18, 0.96),
                    stop:0.38 rgba(14, 22, 32, 0.95),
                    stop:0.75 rgba(10, 18, 29, 0.96),
                    stop:1 rgba(7, 12, 18, 0.97));
                border: 1px solid rgba(104, 174, 255, 0.4);
                border-radius: 28px;
                box-shadow: 0 0 30px rgba(42, 123, 255, 0.18), 0 0 60px rgba(255, 44, 89, 0.12);
            }
            """
        )

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(18, 18, 18, 18)
        outer_layout.setSpacing(18)

        self.sidebar = QWidget(self.root)
        self.sidebar.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(6, 12, 19, 0.9),
                    stop:1 rgba(10, 16, 26, 0.9));
                border: 1px solid rgba(120, 196, 255, 0.25);
                border-radius: 20px;
            }
            """
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        sidebar_title = QLabel("CONVERSATION")
        sidebar_title.setStyleSheet(
            "color: #9fe6ff; font-size: 11px; font-weight: 800; letter-spacing: 3px;"
        )
        sidebar_layout.addWidget(sidebar_title)

        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setStyleSheet(
            """
            QTextBrowser {
                background: rgba(7, 12, 22, 0.75);
                border: 1px solid rgba(98, 189, 255, 0.16);
                border-radius: 14px;
                padding: 10px;
                color: #eaf8ff;
            }
            """
        )
        sidebar_layout.addWidget(self.history, 1)

        main_panel = QWidget(self.root)
        main_panel.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        header = QHBoxLayout()
        self.logo = QLabel()
        logo = QPixmap(str(Path(__file__).resolve().parent / "assets" / "logo.png"))
        if not logo.isNull():
            self.logo.setPixmap(
                logo.scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self.logo.setFixedSize(90, 90)
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.18); border-radius: 20px; background: rgba(255,255,255,0.02);"
            "box-shadow: 0 0 16px rgba(90, 180, 255, 0.22);"
        )
        header.addWidget(self.logo)

        title_block = QVBoxLayout()
        title = QLabel("BOOGIE")
        title.setStyleSheet(
            "color: #f4fbff; font-size: 31px; font-weight: 900; letter-spacing: 7px;"
        )
        subtitle = QLabel("ASSISTANT PERSONNEL • SYNTHÈSE VOCAL • IA / LOCAL")
        subtitle.setStyleSheet(
            "color: #a6d4f5; font-size: 10px; letter-spacing: 2px; text-transform: uppercase;"
        )
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()

        self.status = QLabel("En attente…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color: #8ce8ff; background: rgba(7, 22, 40, 0.9); "
            "border: 1px solid rgba(90, 180, 255, 0.9); border-radius: 12px; "
            "padding: 10px 18px; font-weight: 800; letter-spacing: 1px;"
            "box-shadow: inset 0 0 14px rgba(90,180,255,0.25), 0 0 16px rgba(90,180,255,0.2);"
        )
        header.addWidget(self.status)
        self.logo_effect = QGraphicsOpacityEffect()
        self.logo.setGraphicsEffect(self.logo_effect)
        self.logo_effect.setOpacity(1.0)

        self.pulse = QLabel(self.root)
        self.pulse.setFixedSize(74, 74)
        self.pulse.setAlignment(Qt.AlignCenter)
        self.pulse.hide()
        self.pulse.setStyleSheet(
            "background: radial-gradient(circle, rgba(77,210,255,0.7) 0%, rgba(77,210,255,0.2) 40%, rgba(77,210,255,0.05) 65%, transparent 100%);"
            "border: 1px solid rgba(123,214,255,0.7); border-radius: 37px;"
        )
        header.addWidget(self.pulse)
        self.pulse_effect = QGraphicsOpacityEffect(self.pulse)
        self.pulse.setGraphicsEffect(self.pulse_effect)
        self.pulse_animation = QPropertyAnimation(self.pulse_effect, b"opacity")
        self.pulse_animation.setDuration(800)
        self.pulse_animation.setStartValue(0.2)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)
        main_layout.addLayout(header)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setMinimumHeight(360)
        self.chat.setStyleSheet(
            """
            QTextBrowser {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(8, 16, 27, 0.9),
                    stop:1 rgba(8, 14, 22, 0.86));
                border: 1px solid rgba(118, 170, 255, 0.2);
                border-radius: 18px;
                padding: 16px;
                color: #edfaff;
            }
            """
        )
        main_layout.addWidget(self.chat, 1)

        quick = QHBoxLayout()
        for prompt in (
            "Ouvre un nouvel onglet Chrome",
            "Cherche sur Google les actualités tech",
            "Mets Daft Punk sur Spotify",
        ):
            button = QPushButton(prompt)
            button.clicked.connect(
                lambda _checked=False, text=prompt: self.send_requested.emit(text)
            )
            button.setMinimumHeight(42)
            quick.addWidget(button)
        main_layout.addLayout(quick)

        composer = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Écris à Boogie…")
        self.input.returnPressed.connect(self._send_text)
        composer.addWidget(self.input, 1)

        self.mic_button = QPushButton("🎙  Toujours à l’écoute")
        self.mic_button.setMinimumWidth(220)
        self.mic_button.setDisabled(True)
        composer.addWidget(self.mic_button)

        self.send_button = QPushButton("Envoyer")
        self.send_button.setMinimumWidth(110)
        self.send_button.clicked.connect(self._send_text)
        composer.addWidget(self.send_button)
        main_layout.addLayout(composer)

        footer = QLabel("Voix locale • IA locale • Contrôle Windows • Requêtes web")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "color: #84b3d1; font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;"
        )
        main_layout.addWidget(footer)

        self.root_layout = QHBoxLayout(self.root)
        self.root_layout.addWidget(self.sidebar, 1)
        self.root_layout.addWidget(main_panel, 5)

        outer_layout.addWidget(self.root)

        self.history.append(
            "<span style='color:#8ce8ff; font-size:10px; letter-spacing:2px;'>SYSTEM</span><br>"
            "<span style='color:#edfaff;'>Boogie prêt. Accueil vivant.</span>"
        )

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

        rendered = (
            f'<p style="text-align:{alignment}; margin:10px 3px 3px;">'
            f'<span style="color:{color}; font-size:10px; letter-spacing:2px;">{label}</span>'
            f'<br><span style="color:#ecf7ff; font-size:14px; line-height:1.5;">{safe_text}</span></p>'
        )
        self.chat.append(rendered)
        self.chat.moveCursor(QTextCursor.End)

        history_entry = (
            f'<div style="margin-top:6px; margin-bottom:6px;">'
            f'<span style="color:{color}; font-size:9px; letter-spacing:1px;">{label}</span>'
            f'<div style="color:#edfaff; font-size:12px; line-height:1.45;">{safe_text}</div>'
            f'</div>'
        )
        self.history.append(history_entry)
        self.history.moveCursor(QTextCursor.End)

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
            "font-weight: 800; letter-spacing: 1px;"
        )

    def trigger_pulse(self, duration=500):
        self.pulse.show()
        self.pulse_animation.stop()
        self.pulse_animation.setDuration(duration)
        self.pulse_animation.setStartValue(0.15)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.start()

    def set_listening(self, listening):
        self.mic_button.setText(
            "🎙  Toujours à l’écoute" if listening else "🎙  Micro inactif"
        )
        self.mic_button.setDisabled(True)
        if listening:
            self.pulse.show()
            self.pulse_animation.start()
            self.logo_effect.setOpacity(0.8)
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

    def trigger_pulse(self, duration=500):
        self.pulse.show()
        self.pulse_animation.stop()
        self.pulse_animation.setDuration(duration)
        self.pulse_animation.setStartValue(0.2)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.start()

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
