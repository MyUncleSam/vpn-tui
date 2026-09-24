"""Gemeinsame snack-Dialog-Helfer, von mehreren Screens genutzt.

Nur dieses Modul (und die anderen unter vpn_manager/tui/) darf `snack`
importieren – so bleibt die übrige Logik ohne installiertes `newt` testbar.

Wichtig für alle Dialoge hier: snack leitet den Rückgabewert eines Buttons aus
dem Button-Text ab und schreibt ihn klein (`ButtonBar`: `value = blist.lower()`),
wenn der Button als einfacher String übergeben wird. Deshalb werden Buttons
durchgängig als (Text, Wert)-Tupel übergeben – damit ist der Rückgabewert
explizit und unabhängig von Groß-/Kleinschreibung und Umlauten.
"""

from __future__ import annotations

from snack import (
    ButtonBar,
    ButtonChoiceWindow,
    CheckboxTree,
    EntryWindow,
    GridForm,
    Label,
    ListboxChoiceWindow,
)

# Sichtbare Höhe von Auswahllisten; längere Listen bekommen einen Scrollbalken.
MAX_LIST_HEIGHT = 10
MAX_TREE_HEIGHT = 15


def info(screen, title: str, text: str) -> None:
    ButtonChoiceWindow(screen, title, text, buttons=[("Ok", "ok")], width=60)


def confirm(screen, title: str, text: str) -> bool:
    result = ButtonChoiceWindow(screen, title, text, buttons=[("Ja", "yes"), ("Nein", "no")], width=60)
    return result == "yes"


def prompt_text(screen, title: str, text: str, label: str, default: str = "") -> str | None:
    result, values = EntryWindow(
        screen,
        title,
        text,
        [(label, default)],
        buttons=[("Ok", "ok"), ("Abbrechen", "cancel")],
        width=60,
        entryWidth=40,
    )
    if result != "ok":
        return None
    return values[0]


def prompt_form(screen, title: str, text: str, fields: list[tuple[str, str]]):
    """fields: Liste von (Label, Default). Rückgabe: (button, values) oder (None, None) bei Abbruch."""
    result, values = EntryWindow(
        screen,
        title,
        text,
        fields,
        buttons=[("Ok", "ok"), ("Abbrechen", "cancel")],
        width=60,
        entryWidth=40,
    )
    if result != "ok":
        return None, None
    return result, values


def pick_connections(
    screen,
    names: list[str],
    title: str,
    text: str,
    action_label: str,
    action_value: str,
    *,
    labels: dict[str, str] | None = None,
    preselect: set[str] | None = None,
) -> list[str]:
    """Checkbox-Mehrfachauswahl über Verbindungsnamen. Leere Liste = Abbruch.

    `labels` erlaubt abweichende Anzeigetexte, `preselect` markiert Einträge vor.
    """
    height = min(len(names), MAX_TREE_HEIGHT)
    tree = CheckboxTree(height=height, width=50, scroll=1 if len(names) > height else 0)
    for name in names:
        tree.append(
            labels.get(name, name) if labels else name,
            name,
            selected=1 if preselect and name in preselect else 0,
        )

    buttons = ButtonBar(screen, [(action_label, action_value), ("Zurück", "back")])
    form = GridForm(screen, title, 1, 3)
    form.add(Label(text), 0, 0)
    form.add(tree, 0, 1)
    form.add(buttons, 0, 2, growx=1)

    if buttons.buttonPressed(form.runOnce()) != action_value:
        return []
    selected = tree.getSelection()
    if not selected:
        info(screen, title, "Keine Verbindung markiert.")
    return selected


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
        buttons=[("Auswählen", "select"), ("Keine", "none")],
        width=60,
        height=min(len(items), MAX_LIST_HEIGHT),
        scroll=1 if len(items) > MAX_LIST_HEIGHT else 0,
    )
    # result ist None, wenn der Eintrag direkt mit Enter bestätigt wurde
    # (ListboxChoiceWindow baut die Liste intern mit returnExit=1).
    if result == "none":
        return None
    return choice
