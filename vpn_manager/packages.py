"""Paket-Vorbereitung (pacman) + Bootstrap der TUI-Abhängigkeit `newt`.

`bootstrap_install_newt` darf – im Gegensatz zum Rest des Moduls – nicht von
`snack` abhängen, da sie genau dann läuft, wenn `snack` noch fehlt.
"""

from __future__ import annotations

import subprocess

REQUIRED_PACKAGES = ["networkmanager-openvpn", "wireguard-tools", "networkmanager-strongswan"]
NEWT_PACKAGE = "newt"

PRIVILEGE = "sudo"  # Alternative: "pkexec" (siehe README)


def check_installed(pkg: str, runner=subprocess.run) -> bool:
    """True, falls `pkg` laut `pacman -Qi` installiert ist. False bei fehlendem pacman."""
    try:
        result = runner(["pacman", "-Qi", pkg], capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return result.returncode == 0


def check_all(packages: list[str], runner=subprocess.run) -> dict[str, bool]:
    return {pkg: check_installed(pkg, runner) for pkg in packages}


def build_install_command(pkgs: list[str], privilege: str = PRIVILEGE) -> list[str]:
    base = ["pacman", "-S", "--needed", *pkgs]
    return [privilege, *base] if privilege else base


def bootstrap_install_newt(dry_run: bool = False) -> bool:
    """Reiner print/input/subprocess-Bootstrap, läuft ohne `snack`.

    Gibt True zurück, wenn `newt` danach (voraussichtlich) verfügbar ist.
    """
    print("Das TUI-Toolkit 'newt' (Python-Modul 'snack') ist nicht installiert.")
    if dry_run:
        argv = build_install_command([NEWT_PACKAGE])
        print("[dry-run] " + " ".join(argv))
        return False

    answer = input(f"Jetzt mit pacman installieren? [J/n] ").strip().lower()
    if answer not in ("", "j", "y", "ja", "yes"):
        print("Abgebrochen. Ohne 'newt' kann die TUI nicht gestartet werden.")
        return False

    argv = build_install_command([NEWT_PACKAGE])
    try:
        subprocess.run(argv, check=True)
    except FileNotFoundError:
        print("pacman nicht gefunden – bitte 'newt' manuell installieren.")
        return False
    except subprocess.CalledProcessError as exc:
        print(f"Installation fehlgeschlagen (Exit {exc.returncode}).")
        return False

    import importlib.util

    if importlib.util.find_spec("snack") is None:
        print(
            "'newt' wurde installiert, das Python-Modul 'snack' ist aber weiterhin nicht "
            "auffindbar. Bitte 'pacman -Ss newt' prüfen (evtl. abweichender Paketname für "
            "die Python-Bindings)."
        )
        return False
    return True
