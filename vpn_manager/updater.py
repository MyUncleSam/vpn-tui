"""Selbst-Update beim Start: kurzer `git pull`, der den Start nie blockiert.

Schlägt das Update fehl (offline, keine Git-Installation, lokale Änderungen),
läuft einfach die vorhandene Version weiter – gemeldet wird das in einer Zeile.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

TIMEOUT_SECONDS = 5
REPO_DIR = Path(__file__).resolve().parent.parent


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    # Ohne diese Schalter kann git interaktiv nach Zugangsdaten fragen und
    # damit am Timeout vorbei den Start blockieren.
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -oBatchMode=yes"
    env["LC_ALL"] = "C"
    return env


def build_pull_command(repo_dir: Path) -> list[str]:
    return ["git", "-C", str(repo_dir), "pull", "--ff-only", "--quiet"]


def build_head_command(repo_dir: Path) -> list[str]:
    return ["git", "-C", str(repo_dir), "rev-parse", "HEAD"]


def _head(repo_dir: Path, runner) -> str | None:
    result = runner(
        build_head_command(repo_dir), capture_output=True, text=True, env=git_env()
    )
    return result.stdout.strip() if result.returncode == 0 else None


def update(
    repo_dir: Path | None = None,
    timeout: int = TIMEOUT_SECONDS,
    runner=subprocess.run,
) -> str | None:
    """Kurzer `git pull`. Rückgabe: Hinweis für den Nutzer oder None (nichts zu melden)."""
    repo_dir = Path(repo_dir) if repo_dir is not None else REPO_DIR
    if not (repo_dir / ".git").is_dir():
        # Keine Git-Installation (z. B. per pipx installiert) – nichts zu tun.
        return None

    try:
        before = _head(repo_dir, runner)
        result = runner(
            build_pull_command(repo_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=git_env(),
        )
        if result.returncode != 0:
            return "Update nicht möglich – die lokale Version wird verwendet."
        after = _head(repo_dir, runner)
    except subprocess.TimeoutExpired:
        return f"Update-Prüfung nach {timeout}s abgebrochen – die lokale Version wird verwendet."
    except FileNotFoundError:
        # git ist nicht installiert.
        return None

    if before and after and before != after:
        return "Neue Version eingespielt."
    return None
