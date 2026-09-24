"""Gemeinsame snack-Dialog-Helfer, von mehreren Screens genutzt.

Nur dieses Modul (und die anderen unter vpn_manager/tui/) darf `snack`
importieren – siehe Bootstrapping-Hinweis in vpn_manager/__main__.py.
"""

from __future__ import annotations

from snack import EntryWindow, ListboxChoiceWindow


def info(screen, title: str, text: str) -> None:
    from snack import ButtonChoiceWindow

    ButtonChoiceWindow(screen, title, text, buttons=["Ok"], width=60)


def confirm(screen, title: str, text: str) -> bool:
    from snack import ButtonChoiceWindow

    result = ButtonChoiceWindow(screen, title, text, buttons=["Ja", "Nein"], width=60)
    return result == "Ja"


def prompt_text(screen, title: str, prompt: str, default: str = "") -> str | None:
    result, values = EntryWindow(screen, title, "", [(prompt, default)])
    if result != "Ok":
        return None
    return values[0]


def prompt_form(screen, title: str, fields: list[tuple[str, str]]):
    """fields: Liste von (Label, Default). Rückgabe: (button, values) oder (None, None) bei Abbruch."""
    result, values = EntryWindow(screen, title, "", fields)
    if result != "Ok":
        return None, None
    return result, values


def pick_profile(screen, profiles: dict, title: str = "Zugangsdaten wählen"):
    """Zeigt eine Auswahl gespeicherter Zugangsdaten-Profile. Rückgabe: Profilname oder None."""
    if not profiles:
        return None
    items = [(f"{name} ({profile.provider}, {profile.username})", name) for name, profile in profiles.items()]
    result, choice = ListboxChoiceWindow(
        screen,
        title,
        "Zugangsdatenprofil anwenden (optional):",
        items,
        buttons=["Auswählen", "Keine"],
        width=60,
    )
    if result != "Auswählen":
        return None
    return choice
