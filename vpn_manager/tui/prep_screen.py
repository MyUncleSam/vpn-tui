"""Screen: benötigte Pakete (OpenVPN/WireGuard/IKEv2) prüfen und installieren."""

from __future__ import annotations

import subprocess

from vpn_manager import packages
from vpn_manager.tui import common


def _status_lines(status: dict[str, bool]) -> list[str]:
    return [f"[{'x' if installed else ' '}] {pkg}" for pkg, installed in status.items()]


def run(screen, dry_run: bool) -> None:
    status = packages.check_all(packages.REQUIRED_PACKAGES)
    missing = [pkg for pkg, installed in status.items() if not installed]

    if not missing:
        common.info(
            screen, "Vorbereitung", "Alle benötigten Pakete sind installiert:\n" + "\n".join(_status_lines(status))
        )
        return

    text = (
        "Status:\n"
        + "\n".join(_status_lines(status))
        + f"\n\nFehlende Pakete installieren ({packages.PRIVILEGE} pacman -S --needed ...)?"
    )
    if not common.confirm(screen, "Vorbereitung", text):
        return

    argv = packages.build_install_command(missing)
    if dry_run:
        common.info(screen, "Dry-Run", "Würde ausführen:\n" + " ".join(argv))
        return

    screen.suspend()
    try:
        print("Ausführen: " + " ".join(argv))
        result = subprocess.run(argv)
        ok = result.returncode == 0
    finally:
        screen.resume()

    new_status = packages.check_all(packages.REQUIRED_PACKAGES)
    title = "Installation abgeschlossen" if ok else "Installation fehlgeschlagen"
    common.info(screen, title, "\n".join(_status_lines(new_status)))
