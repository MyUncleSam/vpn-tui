"""Ordner-Scan für den Import-Screen: findet *.conf (WireGuard) und *.ovpn (OpenVPN)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EXTENSION_TO_TYPE = {
    ".conf": "wireguard",
    ".ovpn": "openvpn",
}


@dataclass
class ImportItem:
    path: Path
    conn_type: str  # "wireguard" | "openvpn"


def scan_folder(folder: Path) -> list[ImportItem]:
    """Scannt `folder` (nicht rekursiv) nach *.conf/*.ovpn-Dateien, alphabetisch sortiert."""
    items = []
    for entry in sorted(Path(folder).iterdir()):
        if not entry.is_file():
            continue
        conn_type = EXTENSION_TO_TYPE.get(entry.suffix)
        if conn_type is not None:
            items.append(ImportItem(entry, conn_type))
    return items
