import html
import math
import time
from datetime import datetime
from pathlib import Path

import psutil
from PyQt5.QtCore import QTimer, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from commands import VOICE_PROFILES


class PulseCore(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMaximumSize(480, 480)
        self._phase = 0.0
        self._flash_until = 0.0
        self._busy = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(32)

    def _advance(self):
        self._phase = (self._phase + (0.027 if self._busy else 0.014)) % 1.0
        self.update()

    def flash(self, duration):
        self._flash_until = time.monotonic() + duration / 1000
        self.update()

    def set_busy(self, busy):
        self._busy = busy

    def paintEvent(self, _event):
        side = min(self.width(), self.height())
        radius = side * 0.47
        center_x = self.width() / 2
        center_y = self.height() / 2
        flash = time.monotonic() < self._flash_until
        glow_alpha = 112 if flash else 70

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(center_x, center_y)

        glow = QRadialGradient(0, 0, radius)
        glow.setColorAt(0.0, QColor(255, 36, 66, glow_alpha))
        glow.setColorAt(0.34, QColor(210, 20, 44, 34))
        glow.setColorAt(0.72, QColor(130, 12, 30, 10))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(-radius, -radius, radius * 2, radius * 2))

        for index in range(5):
            ring_radius = radius * (0.34 + index * 0.13)
            wobble = math.sin(self._phase * math.tau - index * 0.7) * 4
            ring_radius += wobble
            alpha = max(42, 176 - index * 24)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 53, 78, alpha), 1.2 if index else 2.0))
            painter.drawEllipse(
                QRectF(
                    -ring_radius,
                    -ring_radius,
                    ring_radius * 2,
                    ring_radius * 2,
                )
            )

        for index in range(4):
            ring_radius = radius * (0.48 + index * 0.115)
            angle = int((self._phase * 360 + index * 87) * 16)
            painter.setPen(QPen(QColor(255, 92, 108, 210 - index * 28), 3))
            painter.drawArc(
                int(-ring_radius),
                int(-ring_radius),
                int(ring_radius * 2),
                int(ring_radius * 2),
                angle,
                53 * 16,
            )

        tick_radius = radius * 0.91
        painter.save()
        painter.rotate(-self._phase * 360)
        painter.setPen(QPen(QColor(255, 103, 120, 155), 1))
        for index in range(72):
            painter.save()
            painter.rotate(index * 5)
            length = 12 if index % 6 == 0 else 5
            painter.drawLine(
                0,
                int(-tick_radius),
                0,
                int(-tick_radius + length),
            )
            painter.restore()
        painter.restore()

        core_radius = radius * (0.19 + math.sin(self._phase * math.tau) * 0.012)
        core_glow = QRadialGradient(0, 0, core_radius * 1.9)
        core_glow.setColorAt(0.0, QColor(255, 204, 207, 245))
        core_glow.setColorAt(0.22, QColor(255, 53, 78, 245))
        core_glow.setColorAt(0.72, QColor(170, 12, 37, 210))
        core_glow.setColorAt(1.0, QColor(100, 0, 22, 0))
        painter.setPen(QPen(QColor(255, 154, 164, 225), 1))
        painter.setBrush(core_glow)
        painter.drawEllipse(
            QRectF(
                -core_radius,
                -core_radius,
                core_radius * 2,
                core_radius * 2,
            )
        )
        painter.setPen(QColor(255, 239, 241))
        painter.drawText(
            int(-core_radius),
            int(-core_radius),
            int(core_radius * 2),
            int(core_radius * 2),
            Qt.AlignCenter,
            "B",
        )
        painter.end()


class BoogieInterface(QWidget):
    send_requested = pyqtSignal(str)
    voice_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    voice_toggled = pyqtSignal(bool)

    def __init__(self, voice_profile="female_natural"):
        super().__init__()
        self.voice_enabled = True
        self.setWindowTitle("BOOGIE  //  INTERFACE DE CONTRÔLE")
        self.resize(1500, 900)
        self.setMinimumSize(1120, 720)
        self.setStyleSheet(
            """
            QWidget {
                color: #f5e9eb;
                font-family: "Segoe UI";
                background: transparent;
            }
            QWidget#hudRoot {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #10080b, stop:0.52 #130b0f, stop:1 #080709);
                border: 1px solid rgba(255, 65, 88, 0.42);
                border-radius: 22px;
            }
            QFrame#panel {
                background: rgba(18, 12, 15, 0.94);
                border: 1px solid rgba(255, 73, 94, 0.22);
                border-radius: 16px;
            }
            QLabel#eyebrow {
                color: #ff687a;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 3px;
            }
            QLabel#muted {
                color: #9e858a;
                font-size: 10px;
                letter-spacing: 1px;
            }
            QPushButton {
                background: rgba(100, 16, 32, 0.72);
                border: 1px solid rgba(255, 78, 100, 0.45);
                border-radius: 9px;
                color: #ffeef0;
                font-weight: 700;
                padding: 9px 12px;
            }
            QPushButton:hover {
                background: rgba(173, 24, 48, 0.9);
                border-color: #ff6b7d;
            }
            QPushButton:disabled {
                background: rgba(75, 56, 60, 0.6);
                color: #9e858a;
            }
            QLineEdit, QComboBox {
                background: rgba(9, 7, 9, 0.94);
                border: 1px solid rgba(255, 75, 98, 0.48);
                border-radius: 10px;
                color: #fff2f3;
                padding: 10px 12px;
                selection-background-color: #9e1e35;
            }
            QComboBox QAbstractItemView {
                background: #160c10;
                color: #fff2f3;
                selection-background-color: #75152a;
            }
            QTextBrowser {
                background: rgba(8, 7, 9, 0.82);
                border: 1px solid rgba(255, 73, 94, 0.19);
                border-radius: 12px;
                padding: 10px;
                color: #f5e9eb;
            }
            QProgressBar {
                background: #29151a;
                border: 0;
                border-radius: 3px;
                max-height: 5px;
            }
            QProgressBar::chunk {
                background: #ff405c;
                border-radius: 3px;
            }
            """
        )

        self.root = QWidget(self)
        self.root.setObjectName("hudRoot")
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.addWidget(self.root)
        layout = QHBoxLayout(self.root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        icon_path = Path(__file__).resolve().parent / "assets" / "logo.png"
        if icon_path.is_file():
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
            logo_pixmap = QPixmap(str(icon_path))
        else:
            logo_pixmap = QPixmap()

        self.sidebar = self._make_panel()
        self.sidebar.setFixedWidth(235)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(14, 16, 14, 14)
        side_layout.setSpacing(10)

        side_heading = QLabel("HISTORIQUE")
        side_heading.setObjectName("eyebrow")
        side_layout.addWidget(side_heading)
        side_subtitle = QLabel("JOURNAL DE SESSION")
        side_subtitle.setObjectName("muted")
        side_layout.addWidget(side_subtitle)

        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(True)
        self.history.setHtml(
            "<span style='color:#ff687a;letter-spacing:2px;'>SYSTÈME</span>"
            "<p style='color:#d7c3c7;'>Boogie prêt. Le journal apparaîtra ici.</p>"
        )
        side_layout.addWidget(self.history, 1)
        session_label = QLabel("SESSION ACTIVE  /  01")
        session_label.setObjectName("muted")
        side_layout.addWidget(session_label)
        layout.addWidget(self.sidebar)

        center = QWidget()
        center.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        header = QHBoxLayout()
        self.logo = QLabel()
        self.logo.setFixedSize(58, 58)
        self.logo.setAlignment(Qt.AlignCenter)
        if not logo_pixmap.isNull():
            self.logo.setPixmap(
                logo_pixmap.scaled(
                    52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            self.logo.setText("B")
            self.logo.setStyleSheet("color: #ff4c67; font-size: 34px; font-weight: 900;")
        header.addWidget(self.logo)

        title_block = QVBoxLayout()
        title = QLabel("BOOGIE")
        title.setStyleSheet(
            "color:#fff3f4;font-size:26px;font-weight:900;letter-spacing:7px;"
        )
        subtitle = QLabel("SYSTÈME D’ASSISTANCE  //  EN LIGNE")
        subtitle.setObjectName("muted")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch()
        self.status = QLabel("INITIALISATION")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(
            "color:#ff8997;background:rgba(84,12,27,0.38);"
            "border:1px solid rgba(255,75,98,0.42);border-radius:10px;"
            "padding:9px 13px;font-size:10px;font-weight:800;letter-spacing:1px;"
        )
        header.addWidget(self.status)
        center_layout.addLayout(header)

        core_panel = self._make_panel()
        core_layout = QVBoxLayout(core_panel)
        core_layout.setContentsMargins(10, 8, 10, 8)
        core_layout.setSpacing(4)
        self.core = PulseCore()
        core_layout.addWidget(self.core, 1, Qt.AlignCenter)
        core_caption = QLabel("CŒUR SYSTÈME  ·  AUDIO / ANALYSE / RÉPONSE")
        core_caption.setObjectName("eyebrow")
        core_caption.setAlignment(Qt.AlignCenter)
        core_layout.addWidget(core_caption)
        center_layout.addWidget(core_panel, 1)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setMinimumHeight(155)
        self.chat.setMaximumHeight(205)
        center_layout.addWidget(self.chat)

        quick_row = QHBoxLayout()
        for prompt in ("Ouvre Chrome", "Cherche sur Google", "Mets Spotify"):
            button = QPushButton(prompt)
            button.setMinimumHeight(36)
            button.clicked.connect(
                lambda _checked=False, text=prompt: self.send_requested.emit(text)
            )
            quick_row.addWidget(button)
        center_layout.addLayout(quick_row)

        composer = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Écris à Boogie…")
        self.input.returnPressed.connect(self._send_text)
        composer.addWidget(self.input, 1)
        self.mic_button = QPushButton("MICRO · INITIALISATION")
        self.mic_button.setMinimumWidth(175)
        self.mic_button.setDisabled(True)
        composer.addWidget(self.mic_button)
        self.mode_button = QPushButton("MODE · CONVERSATION")
        self.mode_button.setMinimumWidth(150)
        self.mode_button.setEnabled(False)
        self.mode_button.setVisible(False)
        composer.addWidget(self.mode_button)
        self.voice_button = QPushButton("VOIX · ACTIVÉE")
        self.voice_button.setMinimumWidth(165)
        self.voice_button.clicked.connect(self._toggle_voice)
        composer.addWidget(self.voice_button)
        self.send_button = QPushButton("ENVOYER")
        self.send_button.clicked.connect(self._send_text)
        composer.addWidget(self.send_button)
        center_layout.addLayout(composer)
        layout.addWidget(center, 1)

        self.metrics_panel = self._make_panel()
        self.metrics_panel.setFixedWidth(235)
        metrics_layout = QVBoxLayout(self.metrics_panel)
        metrics_layout.setContentsMargins(14, 16, 14, 14)
        metrics_layout.setSpacing(10)
        metrics_heading = QLabel("TÉLÉMÉTRIE")
        metrics_heading.setObjectName("eyebrow")
        metrics_layout.addWidget(metrics_heading)
        metrics_subtitle = QLabel("ÉTAT DE LA MACHINE")
        metrics_subtitle.setObjectName("muted")
        metrics_layout.addWidget(metrics_subtitle)

        self.metric_values = {}
        self.metric_bars = {}
        self._add_metric(metrics_layout, "cpu", "PROCESSEUR")
        self._add_metric(metrics_layout, "memory", "MÉMOIRE RAM")
        self._add_metric(metrics_layout, "battery", "BATTERIE")
        self._add_metric(metrics_layout, "network", "RÉSEAU LOCAL", with_bar=False)
        self._add_metric(metrics_layout, "uptime", "TEMPS DE FONCTIONNEMENT", with_bar=False)
        metrics_layout.addStretch()
        self.clock = QLabel()
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setObjectName("eyebrow")
        metrics_layout.addWidget(self.clock)

        voice_heading = QLabel("PROFIL VOCAL")
        voice_heading.setObjectName("muted")
        metrics_layout.addWidget(voice_heading)
        self.voice_combo = QComboBox()
        for key, profile in VOICE_PROFILES.items():
            self.voice_combo.addItem(profile["label"], key)
        selected_index = self.voice_combo.findData(voice_profile)
        self.voice_combo.setCurrentIndex(max(0, selected_index))
        self.voice_combo.currentIndexChanged.connect(self._voice_selection_changed)
        metrics_layout.addWidget(self.voice_combo)
        voice_note = QLabel("Voix en ligne · effets comiques stylisés")
        voice_note.setObjectName("muted")
        voice_note.setWordWrap(True)
        metrics_layout.addWidget(voice_note)
        layout.addWidget(self.metrics_panel)

        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self.refresh_system_metrics)
        self._metrics_timer.start(1500)
        self.refresh_system_metrics()

    @staticmethod
    def _make_panel():
        panel = QFrame()
        panel.setObjectName("panel")
        return panel

    def _add_metric(self, layout, key, title, with_bar=True):
        card = QVBoxLayout()
        card.setSpacing(5)
        heading = QLabel(title)
        heading.setObjectName("muted")
        value = QLabel("—")
        value.setStyleSheet("color:#fff1f2;font-size:19px;font-weight:700;")
        card.addWidget(heading)
        card.addWidget(value)
        self.metric_values[key] = value
        if with_bar:
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setRange(0, 100)
            card.addWidget(bar)
            self.metric_bars[key] = bar
        layout.addLayout(card)

    def refresh_system_metrics(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            interfaces = psutil.net_if_stats()
            network_up = any(
                stats.isup and not name.casefold().startswith("loopback")
                for name, stats in interfaces.items()
            )
            uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
        except (OSError, psutil.Error, NotImplementedError) as exc:
            for value in self.metric_values.values():
                value.setText("INDISPONIBLE")
            self.set_status(f"TÉLÉMÉTRIE INDISPONIBLE · {exc}")
            return

        memory_percent = int(memory.percent)
        self.metric_values["cpu"].setText(f"{cpu_percent:.0f} %")
        self.metric_bars["cpu"].setValue(round(cpu_percent))
        self.metric_values["memory"].setText(
            f"{memory_percent} %  ·  {memory.used / (1024 ** 3):.1f} / "
            f"{memory.total / (1024 ** 3):.1f} Go"
        )
        self.metric_bars["memory"].setValue(memory_percent)
        self.metric_values["network"].setText(
            "CONNECTÉ" if network_up else "HORS LIGNE"
        )
        self.metric_values["network"].setStyleSheet(
            "color:#71e0a1;font-size:15px;font-weight:700;"
            if network_up
            else "color:#ff7180;font-size:15px;font-weight:700;"
        )
        hours, remainder = divmod(uptime_seconds, 3600)
        self.metric_values["uptime"].setText(
            f"{hours} h {remainder // 60:02d} min"
        )

        try:
            battery = psutil.sensors_battery()
        except (OSError, psutil.Error, NotImplementedError) as exc:
            self.metric_values["battery"].setText("ERREUR DE LECTURE")
            self.metric_bars["battery"].setValue(0)
            self.set_status(f"BATTERIE INDISPONIBLE · {exc}")
        else:
            if battery is None:
                self.metric_values["battery"].setText("AUCUNE BATTERIE")
                self.metric_bars["battery"].setValue(0)
            else:
                battery_percent = round(battery.percent)
                charging = " · CHARGE" if battery.power_plugged else ""
                self.metric_values["battery"].setText(
                    f"{battery_percent} %{charging}"
                )
                self.metric_bars["battery"].setValue(battery_percent)
        self.clock.setText(datetime.now().strftime("%H:%M:%S"))

    def _toggle_mode(self):
        next_mode = "conversation"
        self.set_mode(next_mode)
        self.mode_changed.emit(next_mode)

    def set_mode(self, mode):
        normalized_mode = "conversation"
        label = "MODE · CONVERSATION"
        self.mode_button.setText(label)
        self.mode_button.setStyleSheet("color:#7fe7ff;")
        self.mode_button.setEnabled(False)
        self.mode_button.setVisible(False)

    def _toggle_voice(self):
        self.set_voice_enabled(not self.voice_enabled)
        self.voice_toggled.emit(self.voice_enabled)

    def set_voice_enabled(self, enabled):
        self.voice_enabled = bool(enabled)
        label = "VOIX · ACTIVÉE" if self.voice_enabled else "VOIX · DÉSACTIVÉE"
        self.voice_button.setText(label)
        self.voice_button.setStyleSheet(
            "color:#9fe7ff;" if self.voice_enabled else "color:#f5c1c8;"
        )

    def _voice_selection_changed(self, _index):
        profile = self.voice_combo.currentData()
        if profile:
            self.voice_changed.emit(profile)

    def _send_text(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.send_requested.emit(text)

    def add_message(self, speaker, text):
        safe_text = html.escape(text).replace("\n", "<br>")
        label = "TOI" if speaker == "user" else "BOOGIE"
        color = "#ff9ba7" if speaker == "user" else "#ff536b"
        alignment = "right" if speaker == "user" else "left"
        message = (
            f'<p style="text-align:{alignment};margin:8px 2px;">'
            f'<span style="color:{color};font-size:10px;letter-spacing:2px;">'
            f"{label}</span><br>"
            f'<span style="color:#f6e9eb;font-size:13px;line-height:1.45;">'
            f"{safe_text}</span></p>"
        )
        self.chat.append(message)
        self.chat.moveCursor(QTextCursor.End)
        self.history.append(
            f'<p style="margin:7px 1px;"><span style="color:{color};'
            f'font-size:9px;letter-spacing:1px;">{label}</span><br>'
            f'<span style="color:#e7d4d8;font-size:11px;">{safe_text}</span></p>'
        )
        self.history.moveCursor(QTextCursor.End)

    def set_status(self, text):
        self.status.setText(text.upper())
        lower = text.casefold()
        if "erreur" in lower or "indisponible" in lower or "hors ligne" in lower:
            color, border = "#ff7d89", "#9f2d40"
        elif "écout" in lower or "écoute" in lower:
            color, border = "#72e3a3", "#258553"
        else:
            color, border = "#ff8997", "#a53a4c"
        self.status.setStyleSheet(
            f"color:{color};background:rgba(84,12,27,0.38);"
            f"border:1px solid {border};border-radius:10px;"
            "padding:9px 13px;font-size:10px;font-weight:800;letter-spacing:1px;"
        )

    def trigger_pulse(self, duration=500):
        self.core.flash(duration)

    def set_listening(self, listening):
        self.mic_button.setText(
            "MICRO · ACTIF" if listening else "MICRO · INACTIF"
        )
        self.mic_button.setStyleSheet(
            "color:#71e0a1;" if listening else "color:#ff7180;"
        )
        self.core.flash(600)

    def set_busy(self, busy):
        self.send_button.setDisabled(busy)
        self.input.setDisabled(busy)
        self.core.set_busy(busy)
