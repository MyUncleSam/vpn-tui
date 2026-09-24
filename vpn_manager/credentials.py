"""JSON-Credential-Store: mehrere benannte Zugangsdaten-Profile (Anbieter/Username/Passwort).

Lade-/Speicherfunktionen sind die einzige I/O-Schicht; CRUD-Operationen sind
reine dict-in/dict-out-Funktionen und damit ohne Dateisystem testbar.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from vpn_manager import config


@dataclass
class CredentialProfile:
    provider: str
    username: str
    password: str


def load_profiles(path: Path = config.CREDENTIALS_FILE) -> dict[str, CredentialProfile]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {name: CredentialProfile(**fields) for name, fields in raw.items()}


def save_profiles(profiles: dict[str, CredentialProfile], path: Path = config.CREDENTIALS_FILE) -> None:
    config.ensure_config_dir(path.parent)
    raw = {name: asdict(profile) for name, profile in profiles.items()}
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    os.chmod(path, 0o600)


def add_profile(
    profiles: dict[str, CredentialProfile], name: str, provider: str, username: str, password: str
) -> dict[str, CredentialProfile]:
    if name in profiles:
        raise ValueError(f"Profil '{name}' existiert bereits")
    return {**profiles, name: CredentialProfile(provider, username, password)}


def update_profile(
    profiles: dict[str, CredentialProfile],
    name: str,
    provider: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> dict[str, CredentialProfile]:
    if name not in profiles:
        raise ValueError(f"Profil '{name}' existiert nicht")
    current = profiles[name]
    updated = CredentialProfile(
        provider=provider if provider is not None else current.provider,
        username=username if username is not None else current.username,
        password=password if password is not None else current.password,
    )
    return {**profiles, name: updated}


def delete_profile(profiles: dict[str, CredentialProfile], name: str) -> dict[str, CredentialProfile]:
    if name not in profiles:
        raise ValueError(f"Profil '{name}' existiert nicht")
    return {n: p for n, p in profiles.items() if n != name}
