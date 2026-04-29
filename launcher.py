import importlib
import logging
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path


class _BrowserWebviewFallback:
    """Fallback when pywebview is unavailable in this environment."""

    def __init__(self):
        self._url = None

    def create_window(self, _title, url, **_kwargs):
        self._url = url

    def start(self, **_kwargs):
        if self._url:
            webbrowser.open(self._url)


def _load_webview():
    try:
        return importlib.import_module("webview")
    except ModuleNotFoundError:
        return _BrowserWebviewFallback()


webview = _load_webview()
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOGS_DIR / "launcher.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def start_django():
    try:
        logging.info("Starting Django development server")
        subprocess.run(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
            cwd=str(BASE_DIR),
            check=True,
        )
    except Exception as exc:
        logging.exception("Failed to start Django server: %s", exc)

if __name__ == "__main__":
    logging.info("Launcher bootstrap")
    t = threading.Thread(target=start_django)
    t.daemon = True
    t.start()

    webview.create_window(
        "TDR Payroll System",
        "http://127.0.0.1:8000",
        width=1200,
        height=800
    )

    webview.start(gui="edgechromium")