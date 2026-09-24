"""Zentrale Pfade und Konstanten."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "vpn-manager"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def ensure_config_dir(path: Path = CONFIG_DIR) -> None:
    """Legt das Config-Verzeichnis an (falls nötig) und erzwingt chmod 700."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
