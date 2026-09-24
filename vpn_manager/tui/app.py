"""Hauptmenü-Loop: dispatcht auf die einzelnen Screens."""

from __future__ import annotations

from snack import ListboxChoiceWindow, SnackScreen

from vpn_manager.tui import credentials_screen, delete_screen, ikev2_screen, import_screen, prep_screen

MENU_ITEMS = [
    ("Zugangsdaten verwalten", credentials_screen.run),
    ("Import (OpenVPN/WireGuard)", import_screen.run),
    ("IKEv2/IPsec-Verbindung anlegen", ikev2_screen.run),
    ("VPN-Verbindungen löschen", delete_screen.run),
    ("Vorbereitung (Pakete installieren)", prep_screen.run),
]


def run(dry_run: bool = False) -> None:
    screen = SnackScreen()
    try:
        while True:
            items = [(label, idx) for idx, (label, _) in enumerate(MENU_ITEMS)]
            title = "VPN Manager" + (" [DRY-RUN]" if dry_run else "")
            result, choice = ListboxChoiceWindow(
                screen,
                title,
                "Aktion wählen:",
                items,
                buttons=["Auswählen", "Beenden"],
                width=50,
                height=len(items),
            )
            if result != "Auswählen" or choice is None:
                break
            _, handler = MENU_ITEMS[choice]
            handler(screen, dry_run)
    finally:
        screen.finish()
