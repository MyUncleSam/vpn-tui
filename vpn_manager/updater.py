"""Selbst-Update beim Start: kurzer `git pull`, der den Start nie blockiert.

Der Ablauf wird im Terminal mitgeschrieben – in dem Moment läuft die TUI noch
nicht, der Nutzer sieht also, dass etwas passiert (und bei langsamer Leitung
auch, worauf gewartet wird). Die Rückgabe wird zusätzlich im Hauptmenü
angezeigt, weil die TUI den Bildschirm gleich darauf übernimmt.

Schlägt das Update fehl (offline, keine Git-Installation, lokale Änderungen),
läuft einfach die vorhandene Version weiter.
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
    # Kein --quiet: die Ausgabe von git ist genau das, was der Nutzer sehen soll.
    return ["git", "-C", str(repo_dir), "pull", "--ff-only"]


def build_head_command(repo_dir: Path) -> list[str]:
    return ["git", "-C", str(repo_dir), "rev-parse", "HEAD"]


def _say(line: str) -> None:
    # flush, damit die Zeile vor der Ausgabe des Subprozesses erscheint.
    print(line, flush=True)


def _head(repo_dir: Path, runner) -> str | None:
    result = runner(build_head_command(repo_dir), capture_output=True, text=True, env=git_env())
    return result.stdout.strip() if result.returncode == 0 else None


def update(
    repo_dir: Path | None = None,
    timeout: int = TIMEOUT_SECONDS,
    runner=subprocess.run,
) -> str | None:
    """Kurzer `git pull`. Rückgabe: Hinweis fürs Menü oder None (nichts zu melden)."""
    repo_dir = Path(repo_dir) if repo_dir is not None else REPO_DIR
    _say("Suche nach Updates ...")

    if not (repo_dir / ".git").is_dir():
        # Kein Git-Checkout (z. B. per pipx installiert) – nichts zu tun.
        _say(f"  Kein Git-Checkout in {repo_dir} – übersprungen.")
        return None

    argv = build_pull_command(repo_dir)
    _say("  " + " ".join(argv))

    try:
        before = _head(repo_dir, runner)
        # Bewusst ohne capture_output: git schreibt direkt ins Terminal, damit
        # auch der Fortschritt eines längeren Downloads sichtbar ist.
        result = runner(argv, timeout=timeout, env=git_env())
        if result.returncode != 0:
            return _report("Update nicht möglich – die lokale Version wird verwendet.")
        after = _head(repo_dir, runner)
    except subprocess.TimeoutExpired:
        return _report(
            f"Update-Prüfung nach {timeout}s abgebrochen – die lokale Version wird verwendet."
        )
    except FileNotFoundError:
        _say("  git ist nicht installiert – übersprungen.")
        return None

    if before and after and before != after:
        return _report(f"Neue Version eingespielt ({before[:7]} -> {after[:7]}).")

    _report("Bereits aktuell.")
    return None


def _report(message: str) -> str:
    _say(f"  {message}")
    return message
