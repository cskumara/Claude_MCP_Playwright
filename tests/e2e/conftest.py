import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="session", autouse=True)
def server():
    proc = subprocess.Popen([sys.executable, str(ROOT / "app" / "server.py")])
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE_URL}/login")
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("Flask server did not start")
    yield
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL
