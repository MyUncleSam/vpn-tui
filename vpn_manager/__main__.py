"""Einstiegspunkt: parst Argumente, prüft/bootstrapped `snack`, startet die TUI."""

from __future__ import annotations

import argparse
import importlib.util
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="vpn-manager",
        description="Mass-Import/Verwaltung von OpenVPN-, WireGuard- und IKEv2/IPsec-Verbindungen über nmcli.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt alle nmcli-/pacman-Kommandos nur an, statt sie auszuführen.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if importlib.util.find_spec("snack") is None:
        from vpn_manager import packages

        ok = packages.bootstrap_install_newt(dry_run=args.dry_run)
        if not ok:
            return 1
        if args.dry_run:
            # Im Dry-Run wurde nichts wirklich installiert – die TUI kann
            # daher nicht gestartet werden.
            return 0

    from vpn_manager.tui.app import run

    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
