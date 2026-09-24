"""Hauptmenü-Loop: dispatcht auf die einzelnen Screens."""

from __future__ import annotations

from snack import ListboxChoiceWindow, SnackScreen

from vpn_manager.tui import (
    apply_credentials_screen,
    autoconnect_screen,
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
            text = f"{notice}\n\nAktion wählen:" if notice else "Aktion wählen:"
            result, choice = ListboxChoiceWindow(
                screen,
                title,
                text,
                items,
                buttons=[("Auswählen", "select"), ("Beenden", "quit")],
                width=50,
                height=len(items),
            )
            # result ist None, wenn ein Eintrag direkt mit Enter bestätigt wurde
            # (ListboxChoiceWindow baut die Liste intern mit returnExit=1) – das
            # ist ebenfalls eine Auswahl, kein Abbruch.
            if result == "quit":
                break
            _, handler = MENU_ITEMS[choice]
            handler(screen, dry_run)
    finally:
        screen.finish()
