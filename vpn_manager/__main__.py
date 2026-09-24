"""Einstiegspunkt: parst Argumente, prüft `snack`, startet die TUI."""

from __future__ import annotations

import argparse
import importlib.util
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vpn-manager",
        description="Mass-Import und Verwaltung von OpenVPN- und WireGuard-Verbindungen über nmcli.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt alle nmcli-Kommandos nur an, statt sie auszuführen.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if importlib.util.find_spec("snack") is None:
        print(
            "Das TUI-Toolkit 'newt' (Python-Modul 'snack') ist nicht installiert.\n"
            "Bitte einmalig nachinstallieren:  sudo pacman -S newt"
        )
        return 1

    from vpn_manager.tui.app import run

    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
