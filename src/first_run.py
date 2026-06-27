"""First-run setup wizard — PyQt5 GUI shown on initial launch.

No terminal, no pip, no config editing. The customer sees a clean
wizard that auto-detects their hardware and configures everything.
"""

import os
import subprocess
import sys
from typing import Optional

import yaml
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QRadioButton, QButtonGroup,
    QStackedWidget, QProgressBar, QFrame, QSpacerItem, QSizePolicy,
)

def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(__file__))

CONFIG_PATH = os.path.join(_app_dir(), "config.yaml")

# ── Dark theme ────────────────────────────────────────────
STYLE = """
QWidget {
    background: #0e1015;
    color: #e7e9ee;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QLabel#title {
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
}
QLabel#subtitle {
    font-size: 13px;
    color: #9aa0ab;
}
QLabel#step {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    color: #9aa0ab;
    text-transform: uppercase;
}
QRadioButton {
    font-size: 13px;
    color: #e7e9ee;
    spacing: 10px;
    padding: 12px 16px;
    border: 1px solid #2e333b;
    border-radius: 10px;
    background: #1c1f24;
}
QRadioButton:hover {
    border-color: #3a4150;
    background: #23272e;
}
QRadioButton:checked {
    border-color: #2f81f7;
    background: #161e2b;
}
QRadioButton::indicator { width: 0; height: 0; }
QLineEdit {
    padding: 10px 14px;
    border: 1px solid #2e333b;
    border-radius: 8px;
    background: #1c1f24;
    color: #e7e9ee;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #2f81f7;
}
QPushButton#primary {
    padding: 10px 28px;
    border: none;
    border-radius: 8px;
    background: #2f81f7;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#primary:hover { background: #4090ff; }
QPushButton#primary:pressed { background: #2570d4; }
QPushButton#secondary {
    padding: 10px 28px;
    border: 1px solid #2e333b;
    border-radius: 8px;
    background: transparent;
    color: #9aa0ab;
    font-size: 13px;
}
QPushButton#secondary:hover { color: #e7e9ee; border-color: #3a4150; }
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #1c1f24;
    height: 8px;
}
QProgressBar::chunk {
    background: #2f81f7;
    border-radius: 4px;
}
QLabel#status-ok { color: #2ecc71; }
QLabel#status-warn { color: #f5a623; }
QLabel#status-err { color: #eb5757; }
"""


class DetectThread(QThread):
    """Background thread to detect GPU and test server connectivity."""
    result = pyqtSignal(dict)

    def __init__(self, url=None):
        super().__init__()
        self.url = url

    def run(self):
        info = {"gpu": None, "server_ok": False, "server_model": False}

        # Detect local GPU
        try:
            r = subprocess.run(
                "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
                shell=True, capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                info["gpu"] = r.stdout.strip().split("\n")[0]
        except Exception:
            pass

        # Test server if URL given
        if self.url:
            try:
                import requests
                resp = requests.get(f"{self.url}/health", timeout=5)
                if resp.ok:
                    data = resp.json()
                    info["server_ok"] = True
                    info["server_model"] = data.get("model_loaded", False)
            except Exception:
                pass

        self.result.emit(info)


class SetupWizard(QWidget):
    """First-run setup wizard."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wisper Setup")
        self.setFixedSize(520, 480)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self._config = self._load_config()
        self._gpu_info = None
        self._chosen_mode = None

        # Pages
        self._pages = QStackedWidget()
        self._build_welcome_page()
        self._build_mode_page()
        self._build_server_page()
        self._build_done_page()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._pages)

        # Start GPU detection
        self._detect = DetectThread()
        self._detect.result.connect(self._on_detect)
        self._detect.start()

    # ── Pages ─────────────────────────────────────────────

    def _build_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 50, 40, 40)

        title = QLabel("Welcome to Wisper")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(
            "Speech-to-text dictation for Windows.\n"
            "Press a hotkey, speak, and text appears.\n\n"
            "Let's set up your transcription engine."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        self._detect_label = QLabel("Detecting hardware...")
        self._detect_label.setObjectName("subtitle")
        self._detect_label.setAlignment(Qt.AlignCenter)

        self._detect_bar = QProgressBar()
        self._detect_bar.setRange(0, 0)  # indeterminate
        self._detect_bar.setFixedWidth(200)

        detect_row = QHBoxLayout()
        detect_row.addStretch()
        detect_row.addWidget(self._detect_bar)
        detect_row.addStretch()

        btn = QPushButton("Get Started")
        btn.setObjectName("primary")
        btn.clicked.connect(lambda: self._pages.setCurrentIndex(1))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()

        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(16)
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        layout.addWidget(self._detect_label)
        layout.addSpacing(8)
        layout.addLayout(detect_row)
        layout.addStretch()
        layout.addLayout(btn_row)

        self._pages.addWidget(page)

    def _build_mode_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        step = QLabel("STEP 1 OF 2")
        step.setObjectName("step")

        title = QLabel("Transcription Engine")
        title.setObjectName("title")

        subtitle = QLabel("How should Wisper transcribe your speech?")
        subtitle.setObjectName("subtitle")

        self._gpu_label = QLabel("")
        self._gpu_label.setObjectName("subtitle")

        # Radio buttons
        self._mode_group = QButtonGroup(self)

        self._rb_remote = QRadioButton(
            "  Connect to a GPU server\n"
            "  Fast (~0.5s). Needs a machine with NVIDIA GPU on your network."
        )
        self._rb_local = QRadioButton(
            "  Use this machine's GPU\n"
            "  Fast (~0.5s). Requires NVIDIA GPU with CUDA on this PC."
        )
        self._rb_cpu = QRadioButton(
            "  CPU only (no GPU needed)\n"
            "  Slower (~5-15s) but works on any Windows machine."
        )

        self._rb_remote.setChecked(True)
        self._mode_group.addButton(self._rb_remote, 0)
        self._mode_group.addButton(self._rb_local, 1)
        self._mode_group.addButton(self._rb_cpu, 2)

        # Nav buttons
        next_btn = QPushButton("Next")
        next_btn.setObjectName("primary")
        next_btn.clicked.connect(self._on_mode_next)

        nav = QHBoxLayout()
        nav.addStretch()
        nav.addWidget(next_btn)

        layout.addWidget(step)
        layout.addSpacing(8)
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(self._gpu_label)
        layout.addSpacing(16)
        layout.addWidget(self._rb_remote)
        layout.addSpacing(6)
        layout.addWidget(self._rb_local)
        layout.addSpacing(6)
        layout.addWidget(self._rb_cpu)
        layout.addStretch()
        layout.addLayout(nav)

        self._pages.addWidget(page)

    def _build_server_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        step = QLabel("STEP 2 OF 2")
        step.setObjectName("step")

        self._server_title = QLabel("GPU Server Address")
        self._server_title.setObjectName("title")

        self._server_subtitle = QLabel(
            "Enter the IP address of the machine running the Wisper GPU server."
        )
        self._server_subtitle.setObjectName("subtitle")
        self._server_subtitle.setWordWrap(True)

        # IP input
        ip_label = QLabel("Server address:")
        self._ip_input = QLineEdit("192.168.0.5")
        self._ip_input.setPlaceholderText("e.g. 192.168.0.5")

        port_label = QLabel("Port:")
        self._port_input = QLineEdit("8765")
        self._port_input.setFixedWidth(80)

        ip_row = QHBoxLayout()
        ip_row.addWidget(self._ip_input, 1)
        ip_row.addSpacing(8)
        ip_row.addWidget(port_label)
        ip_row.addWidget(self._port_input)

        # Status
        self._server_status = QLabel("")
        self._server_status.setWordWrap(True)

        test_btn = QPushButton("Test Connection")
        test_btn.setObjectName("secondary")
        test_btn.clicked.connect(self._test_server)

        test_row = QHBoxLayout()
        test_row.addWidget(test_btn)
        test_row.addStretch()

        # Nav
        back_btn = QPushButton("Back")
        back_btn.setObjectName("secondary")
        back_btn.clicked.connect(lambda: self._pages.setCurrentIndex(1))

        finish_btn = QPushButton("Finish Setup")
        finish_btn.setObjectName("primary")
        finish_btn.clicked.connect(self._finish)

        nav = QHBoxLayout()
        nav.addWidget(back_btn)
        nav.addStretch()
        nav.addWidget(finish_btn)

        layout.addWidget(step)
        layout.addSpacing(8)
        layout.addWidget(self._server_title)
        layout.addSpacing(4)
        layout.addWidget(self._server_subtitle)
        layout.addSpacing(20)
        layout.addWidget(ip_label)
        layout.addSpacing(4)
        layout.addLayout(ip_row)
        layout.addSpacing(12)
        layout.addLayout(test_row)
        layout.addSpacing(8)
        layout.addWidget(self._server_status)
        layout.addStretch()
        layout.addLayout(nav)

        self._pages.addWidget(page)

    def _build_done_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 50, 40, 40)

        title = QLabel("You're All Set!")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        self._done_summary = QLabel("")
        self._done_summary.setObjectName("subtitle")
        self._done_summary.setAlignment(Qt.AlignCenter)
        self._done_summary.setWordWrap(True)

        hint = QLabel(
            "Press Ctrl+Win or click the floating island to dictate.\n"
            "Right-click the island for options."
        )
        hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)

        btn = QPushButton("Start Wisper")
        btn.setObjectName("primary")
        btn.clicked.connect(self._start_app)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()

        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(self._done_summary)
        layout.addSpacing(20)
        layout.addWidget(hint)
        layout.addStretch()
        layout.addLayout(btn_row)

        self._pages.addWidget(page)

    # ── Detection callback ───────────────────────────────

    def _on_detect(self, info):
        self._gpu_info = info.get("gpu")
        self._detect_bar.setRange(0, 1)
        self._detect_bar.setValue(1)

        if self._gpu_info:
            self._detect_label.setText(f"GPU found: {self._gpu_info}")
            self._detect_label.setObjectName("status-ok")
            self._gpu_label.setText(f"Detected: {self._gpu_info}")
            self._gpu_label.setObjectName("status-ok")
        else:
            self._detect_label.setText("No NVIDIA GPU detected")
            self._detect_label.setObjectName("status-warn")
            self._gpu_label.setText("No GPU detected on this machine")
            self._gpu_label.setObjectName("status-warn")
            self._rb_local.setEnabled(False)
            self._rb_local.setText(
                "  Use this machine's GPU\n"
                "  Not available — no NVIDIA GPU detected."
            )

        # Restyle after objectName change
        self._detect_label.setStyleSheet(self._detect_label.styleSheet())
        self._gpu_label.setStyleSheet(self._gpu_label.styleSheet())

    # ── Mode selection ───────────────────────────────────

    def _on_mode_next(self):
        mode_id = self._mode_group.checkedId()

        if mode_id == 0:  # Remote GPU server
            self._chosen_mode = "remote"
            self._server_title.setText("GPU Server Address")
            self._server_subtitle.setText(
                "Enter the IP of the machine running the Wisper GPU server.\n"
                "You can set up the server later — the app will fall back to CPU."
            )
            self._pages.setCurrentIndex(2)

        elif mode_id == 1:  # Local GPU
            self._chosen_mode = "local_gpu"
            self._server_title.setText("Local GPU Server")
            self._server_subtitle.setText(
                "Wisper will run the GPU server on this machine (localhost).\n"
                "The model loads into GPU memory on startup."
            )
            self._ip_input.setText("localhost")
            self._ip_input.setEnabled(False)
            self._pages.setCurrentIndex(2)

        elif mode_id == 2:  # CPU only
            self._chosen_mode = "cpu"
            self._apply_config()
            self._show_done()

    # ── Server test ──────────────────────────────────────

    def _test_server(self):
        ip = self._ip_input.text().strip()
        port = self._port_input.text().strip()
        url = f"http://{ip}:{port}"

        self._server_status.setText("Testing...")
        self._server_status.setObjectName("subtitle")
        self._server_status.setStyleSheet(self._server_status.styleSheet())
        QApplication.processEvents()

        self._test_thread = DetectThread(url)
        self._test_thread.result.connect(self._on_test_result)
        self._test_thread.start()

    def _on_test_result(self, info):
        if info["server_ok"]:
            if info["server_model"]:
                self._server_status.setText("Connected! Server is running and model is loaded.")
                self._server_status.setObjectName("status-ok")
            else:
                self._server_status.setText("Server reachable but model is still loading...")
                self._server_status.setObjectName("status-warn")
        else:
            self._server_status.setText(
                "Could not reach server. Check the IP and make sure the server is running.\n"
                "You can still finish setup — the app will fall back to CPU."
            )
            self._server_status.setObjectName("status-err")
        self._server_status.setStyleSheet(self._server_status.styleSheet())

    # ── Finish ───────────────────────────────────────────

    def _finish(self):
        self._apply_config()
        self._show_done()

    def _apply_config(self):
        config = self._config

        if self._chosen_mode == "remote":
            ip = self._ip_input.text().strip()
            port = self._port_input.text().strip()
            config["whisper"]["remote_url"] = f"http://{ip}:{port}"
            config["whisper"]["model_name"] = "tiny"
            config["whisper"]["device"] = "cpu"

        elif self._chosen_mode == "local_gpu":
            port = self._port_input.text().strip()
            config["whisper"]["remote_url"] = f"http://localhost:{port}"
            config["whisper"]["model_name"] = "tiny"
            config["whisper"]["device"] = "cpu"

        elif self._chosen_mode == "cpu":
            config["whisper"]["remote_url"] = ""
            config["whisper"]["model_name"] = "tiny"
            config["whisper"]["device"] = "cpu"

        config["_setup_complete"] = True
        self._save_config(config)

    def _show_done(self):
        config = self._config
        url = config["whisper"].get("remote_url", "")

        if self._chosen_mode == "remote":
            summary = f"Mode: Remote GPU server at {url}\nFallback: Local CPU (tiny model)"
        elif self._chosen_mode == "local_gpu":
            summary = f"Mode: Local GPU server at {url}\nModel loaded into your GPU on startup"
        else:
            summary = "Mode: CPU only (tiny model)\nSlower but works without a GPU"

        self._done_summary.setText(summary)
        self._pages.setCurrentIndex(3)

    def _start_app(self):
        self.close()

    # ── Config helpers ───────────────────────────────────

    @staticmethod
    def _load_config():
        # Copy bundled default if no config exists yet
        if not os.path.exists(CONFIG_PATH) and getattr(sys, "frozen", False):
            bundled = os.path.join(sys._MEIPASS, "config.yaml")
            if os.path.exists(bundled):
                import shutil
                shutil.copy2(bundled, CONFIG_PATH)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                return yaml.safe_load(f)
        return {}

    @staticmethod
    def _save_config(config):
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def needs_setup() -> bool:
    """Check if first-run setup is needed."""
    if not os.path.exists(CONFIG_PATH):
        return True
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return not config.get("_setup_complete", False)


def run_setup_wizard(app: QApplication) -> bool:
    """Show the setup wizard. Returns True if completed."""
    wizard = SetupWizard()
    wizard.setStyleSheet(STYLE)
    wizard.show()
    app.exec_()
    return not needs_setup()
