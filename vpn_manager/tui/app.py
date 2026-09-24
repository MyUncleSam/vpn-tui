"""Hauptmenü-Loop: dispatcht auf die einzelnen Screens."""

from __future__ import annotations

from snack import SnackScreen

from vpn_manager.tui import (
    apply_credentials_screen,
    autoconnect_screen,
    common,
    credentials_screen,
    delete_screen,
    import_screen,
)

MENU_ITEMS = [
    ("Zugangsdaten verwalten", credentials_screen.run),
    ("Import (OpenVPN/WireGuard)", import_screen.run),
    ("Zugangsdaten auf Verbindungen anwenden", apply_credentials_screen.run),
    ("Autoconnect deaktivieren", autoconnect_screen.run),
    ("VPN-Verbindungen löschen", delete_screen.run),
]


def run(dry_run: bool = False, notice: str | None = None) -> None:
    """`notice`: einzeilige Startmeldung (z. B. vom Selbst-Update), sonst None.

    Sie wird im Menü angezeigt statt per print ausgegeben – die TUI übernimmt
    den Bildschirm sofort und würde eine gedruckte Zeile überschreiben.
    """
    screen = SnackScreen()
    try:
        while True:
            items = [(label, idx) for idx, (label, _) in enumerate(MENU_ITEMS)]
            title = "VPN Manager" + (" [DRY-RUN]" if dry_run else "")
            hint = "Aktion wählen (ESC oder Q beendet):"
            text = f"{notice}\n\n{hint}" if notice else hint

            choice = common.choose(screen, title, text, items, cancel=("Beenden", "quit"))
            if choice is None:
                break
            _, handler = MENU_ITEMS[choice]
            handler(screen, dry_run)
    except KeyboardInterrupt:
        # Falls Ctrl+C doch als SIGINT durchkommt: sauber beenden statt Traceback.
        pass
    finally:
        # Stellt das Terminal in jedem Fall wieder her.
        screen.finish()
