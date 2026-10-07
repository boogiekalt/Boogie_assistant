import html

from PyQt5.QtCore import QPropertyAnimation, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
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

        self.setWindowTitle("Boogie | Jarvis HUD")
        self.resize(1400, 860)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(
            """
            QWidget {
                color: #ebf9ff;
                font-family: "Segoe UI";
                background: transparent;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff345f, stop:1 #a00032);
                border: 1px solid rgba(255,255,255,0.20);
                border-radius: 12px;
                color: #fff8fb;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 10px 14px;
                box-shadow: 0 0 14px rgba(255, 84, 125, 0.35);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff4d7b, stop:1 #c11442);
            }
            QPushButton:disabled {
                background: rgba(150, 170, 185, 0.15);
                border: 1px solid rgba(255,255,255,0.08);
                color: rgba(235, 249, 255, 0.62);
            }
            QLineEdit {
                background: rgba(5, 14, 22, 0.8);
                border: 1px solid rgba(98, 200, 255, 0.9);
                border-radius: 14px;
                color: #edfaff;
                padding: 12px 16px;
                selection-background-color: rgba(105, 198, 255, 0.7);
                box-shadow: inset 0 0 20px rgba(60, 145, 255, 0.18);
            }
            QTextBrowser {
                background: rgba(5, 12, 22, 0.7);
                border: 1px solid rgba(163, 210, 255, 0.12);
                border-radius: 18px;
                color: #ebf9ff;
            }
            """
        )

        self.background = QLabel(self)
        self.background.setStyleSheet(
            "background: qradialgradient(cx:0.5, cy:0.32, radius:1.5, "
            "stop:0 rgba(58, 145, 255, 0.28), stop:0.35 rgba(17, 35, 58, 0.10), "
            "stop:1 rgba(3, 8, 14, 0.96));"
        )
        self.background.lower()
        self.background.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.root = QWidget(self)
        self.root.setObjectName("hudRoot")
        self.root.setStyleSheet(
            """
            QWidget#hudRoot {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(8, 12, 18, 0.96),
                    stop:0.5 rgba(11, 20, 30, 0.96),
                    stop:1 rgba(7, 10, 17, 0.98));
                border: 1px solid rgba(134, 194, 255, 0.35);
                border-radius: 28px;
                box-shadow: 0 0 28px rgba(30, 120, 255, 0.18),
                    0 0 50px rgba(255, 46, 94, 0.08);
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
                background: rgba(10, 16, 25, 0.78);
                border: 1px solid rgba(128, 201, 255, 0.18);
                border-radius: 20px;
            }
            """
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        sidebar_title = QLabel("CONVERSATION")
        sidebar_title.setStyleSheet(
            "color: #9fe7ff; font-size: 11px; font-weight: 800; letter-spacing: 4px;"
        )
        sidebar_layout.addWidget(sidebar_title)

        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setStyleSheet(
            """
            QTextBrowser {
                background: rgba(7, 12, 22, 0.72);
                border: 1px solid rgba(90, 180, 255, 0.2);
                border-radius: 14px;
                padding: 10px;
                color: #ebf9ff;
            }
            """
        )
        self.history.setHtml(
            "<div style='color:#8fe1ff; font-size:10px; letter-spacing:2px;'>SYSTEM</div>"
            "<div style='color:#edfaff; margin-top:6px;'>Boogie prêt. Interface HUD active.</div>"
        )
        sidebar_layout.addWidget(self.history, 1)

        main_panel = QWidget(self.root)
        main_panel.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        header = QHBoxLayout()
        self.logo = QLabel("B")
        self.logo.setFixedSize(90, 90)
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 rgba(28, 150, 255, 0.30), stop:1 rgba(255, 52, 95, 0.18)); "
            "border: 1px solid rgba(140, 210, 255, 0.5); border-radius: 20px; "
            "color: #dff7ff; font-size: 36px; font-weight: 900; "
            "box-shadow: 0 0 22px rgba(67, 165, 255, 0.25);"
        )
        header.addWidget(self.logo)

        title_block = QVBoxLayout()
        title = QLabel("BOOGIE")
        title.setStyleSheet(
            "color: #f4fbff; font-size: 31px; font-weight: 900; letter-spacing: 7px;"
        )
        subtitle = QLabel("ASSISTANT PERSONNEL • IA LOCALE • SYNTHÈSE VOCAL")
        subtitle.setStyleSheet(
            "color: #a5d6f7; font-size: 10px; letter-spacing: 2px; text-transform: uppercase;"
        )
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()

        self.status = QLabel("En attente…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color: #8fe6ff; background: rgba(7, 18, 31, 0.9); "
            "border: 1px solid rgba(102, 200, 255, 0.85); border-radius: 12px; "
            "padding: 10px 18px; font-weight: 800; letter-spacing: 1px;"
        )
        header.addWidget(self.status)
        main_layout.addLayout(header)

        visor = QWidget()
        visor.setStyleSheet("background: rgba(8, 15, 22, 0.55); border: 1px solid rgba(120, 190, 255, 0.18); border-radius: 20px;")
        visor_layout = QVBoxLayout(visor)
        visor_layout.setContentsMargins(18, 18, 18, 18)
        visor_layout.setSpacing(10)

        self.core = QLabel()
        self.core.setAlignment(Qt.AlignCenter)
        self.core.setFixedSize(300, 300)
        self.core.setStyleSheet(
            "background: radial-gradient(circle, rgba(77, 211, 255, 0.4) 0%, "
            "rgba(77, 211, 255, 0.15) 28%, rgba(77, 211, 255, 0.06) 46%, "
            "rgba(0, 0, 0, 0) 72%); border: 1px solid rgba(110, 200, 255, 0.5); "
            "border-radius: 150px;"
        )
        self.core_effect = QGraphicsOpacityEffect(self.core)
        self.core.setGraphicsEffect(self.core_effect)
        self.core_animation = QPropertyAnimation(self.core_effect, b"opacity")
        self.core_animation.setLoopCount(-1)
        self.core.hide()

        self.core_text = QLabel("AUDIO / ANALYSE / RÉPONSE")
        self.core_text.setAlignment(Qt.AlignCenter)
        self.core_text.setStyleSheet(
            "color: #9ad7ff; font-size: 10px; letter-spacing: 3px; text-transform: uppercase;"
        )

        visor_layout.addWidget(self.core, 0, Qt.AlignCenter)
        visor_layout.addWidget(self.core_text)
        main_layout.addWidget(visor, 1)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setMinimumHeight(240)
        self.chat.setStyleSheet(
            """
            QTextBrowser {
                background: rgba(6, 12, 22, 0.78);
                border: 1px solid rgba(120, 188, 255, 0.18);
                border-radius: 18px;
                padding: 14px;
                color: #edfaff;
            }
            """
        )
        main_layout.addWidget(self.chat, 1)

        quick = QHBoxLayout()
        for prompt in (
            "Ouvre Chrome",
            "Cherche sur Google",
            "Mets Spotify",
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

        self.mic_button = QPushButton("🎙  MICRO ACTIF")
        self.mic_button.setMinimumWidth(220)
        self.mic_button.setDisabled(True)
        composer.addWidget(self.mic_button)

        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self._send_text)
        composer.addWidget(self.send_button)
        main_layout.addLayout(composer)

        footer = QLabel("SYSTÈME LOCAL • AUDIO • NAVIGATION • IA")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "color: #8eb4d8; font-size: 9px; letter-spacing: 2px; text-transform: uppercase;"
        )
        main_layout.addWidget(footer)

        self.root_layout = QHBoxLayout(self.root)
        self.root_layout.setContentsMargins(12, 12, 12, 12)
        self.root_layout.addWidget(self.sidebar, 1)
        self.root_layout.addWidget(main_panel, 4)

        outer_layout.addWidget(self.root)

    def _send_text(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.send_requested.emit(text)

    def add_message(self, speaker, text):
        safe_text = html.escape(text).replace("\n", "<br>")
        label = "TOI" if speaker == "user" else "BOOGIE"
        color = "#9fe7ff" if speaker == "user" else "#ff6a73"
        alignment = "right" if speaker == "user" else "left"

        line = (
            f'<p style="text-align:{alignment}; margin:10px 2px 6px;">'
            f'<span style="color:{color}; font-size:10px; letter-spacing:2px;">{label}</span>'
            f'<br><span style="color:#edfaff; font-size:14px; line-height:1.5;">{safe_text}</span></p>'
        )
        self.chat.append(line)
        self.chat.moveCursor(QTextCursor.End)

        history = (
            f'<div style="margin-top:8px; margin-bottom:8px;">'
            f'<span style="color:{color}; font-size:9px; letter-spacing:1px;">{label}</span>'
            f'<div style="color:#edfaff; font-size:12px; line-height:1.45;">{safe_text}</div>'
            f'</div>'
        )
        self.history.append(history)
        self.history.moveCursor(QTextCursor.End)

    def set_status(self, text):
        self.status.setText(text)
        lower = text.casefold()
        if "écout" in lower or "écoute" in lower:
            color = "#59e2a3"
            border = "#1c8d6a"
        elif "erreur" in lower or "indisponible" in lower:
            color = "#ff7f8b"
            border = "#9d3345"
        else:
            color = "#8fe6ff"
            border = "#3a96d2"
        self.status.setStyleSheet(
            f"color: {color}; background: rgba(5, 20, 34, 0.88); "
            f"border: 1px solid {border}; border-radius: 12px; "
            "padding: 10px 18px; font-weight: 800; letter-spacing: 1px;"
        )

    def trigger_pulse(self, duration=500):
        self.core.show()
        self.core_animation.stop()
        self.core_animation.setDuration(duration)
        self.core_animation.setStartValue(0.25)
        self.core_animation.setEndValue(1.0)
        self.core_animation.start()

    def set_listening(self, listening):
        self.mic_button.setText(
            "🎙  MICRO ACTIF" if listening else "🎙  MICRO INACTIF"
        )
        if listening:
            self.core.show()
            self.core_animation.start()
        else:
            self.core_animation.stop()
            self.core.hide()

    def set_busy(self, busy):
        self.send_button.setDisabled(busy)
        self.input.setDisabled(busy)

    def resizeEvent(self, event):
        self.background.resize(self.size())
        super().resizeEvent(event)


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
