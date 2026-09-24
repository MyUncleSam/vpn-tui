"""Gemeinsame snack-Dialoge – jeder davon lässt sich mit ESC abbrechen.

Zwei Eigenheiten von snack bestimmen den Aufbau hier:

1. Die Komfortfunktionen (`ButtonChoiceWindow`, `ListboxChoiceWindow`,
   `EntryWindow`) reagieren nicht auf ESC. newt liefert die Taste nur, wenn sie
   per `addHotKey` am Formular registriert ist, und dafür bieten diese
   Funktionen keinen Parameter. Die Dialoge sind deshalb selbst aus `GridForm`
   aufgebaut.
2. `ButtonBar` leitet den Rückgabewert eines Buttons aus dessen Text ab und
   schreibt ihn klein (`value = blist.lower()`), wenn der Button als einfacher
   String übergeben wird. Buttons werden daher immer als (Text, Wert)-Tupel
   übergeben.

Nur Module unter vpn_manager/tui/ dürfen `snack` importieren – so bleibt die
übrige Logik ohne installiertes `newt` testbar.
"""

from __future__ import annotations

from snack import ButtonBar, CheckboxTree, Entry, Grid, GridForm, Label, Listbox, TextboxReflowed

# Sichtbare Höhe von Auswahllisten; längere Listen bekommen einen Scrollbalken.
MAX_LIST_HEIGHT = 10
MAX_TREE_HEIGHT = 15
DIALOG_WIDTH = 60
LIST_WIDTH = 50

ESC = "ESC"
QUIT_KEYS = ("q", "Q")
CANCEL_KEYS = (ESC, *QUIT_KEYS)


def run_form(form, quit_key: bool = True):
    """Führt ein GridForm aus. Rückgabe: Widget, "ESC" oder "q"/"Q".

    `quit_key=False` für Formulare mit Texteingabe: dort würde "q" als Hotkey
    das Tippen abfangen, statt zu helfen.
    """
    form.addHotKey(ESC)
    if quit_key:
        for key in QUIT_KEYS:
            form.addHotKey(key)
    return form.runOnce()


def is_cancel(result) -> bool:
    """True, wenn der Dialog per ESC oder Q abgebrochen wurde."""
    return result in CANCEL_KEYS


def _text(screen, text: str) -> TextboxReflowed:
    return TextboxReflowed(DIALOG_WIDTH, text, maxHeight=max(screen.height - 12, 4))


def info(screen, title: str, text: str) -> None:
    buttons = ButtonBar(screen, [("Ok", "ok")])
    form = GridForm(screen, title, 1, 2)
    form.add(_text(screen, text), 0, 0, padding=(0, 0, 0, 1))
    form.add(buttons, 0, 1, growx=1)
    # ESC/Q schließen den Hinweis wie "Ok" – er hat keine Gegenoption.
    run_form(form)


def confirm(screen, title: str, text: str) -> bool:
    buttons = ButtonBar(screen, [("Ja", "yes"), ("Nein", "no")])
    form = GridForm(screen, title, 1, 2)
    form.add(_text(screen, text), 0, 0, padding=(0, 0, 0, 1))
    form.add(buttons, 0, 1, growx=1)

    result = run_form(form)
    if is_cancel(result):
        return False
    return buttons.buttonPressed(result) == "yes"


def prompt_form(screen, title: str, text: str, fields: list[tuple[str, str]]):
    """fields: Liste von (Label, Default). Rückgabe: ("ok", values) oder (None, None)."""
    entries = [Entry(40, default) for _, default in fields]

    grid = Grid(2, len(fields))
    for row, ((label, _), entry) in enumerate(zip(fields, entries)):
        grid.setField(Label(label), 0, row, padding=(0, 0, 1, 0), anchorLeft=1)
        grid.setField(entry, 1, row, anchorLeft=1)

    buttons = ButtonBar(screen, [("Ok", "ok"), ("Abbrechen", "cancel")])
    form = GridForm(screen, title, 1, 3)
    form.add(_text(screen, text), 0, 0, padding=(0, 0, 0, 1))
    form.add(grid, 0, 1, padding=(0, 0, 0, 1))
    form.add(buttons, 0, 2, growx=1)

    # Kein q-Hotkey: hier wird Text getippt.
    result = run_form(form, quit_key=False)
    if is_cancel(result) or buttons.buttonPressed(result) != "ok":
        return None, None
    return "ok", tuple(entry.value() for entry in entries)


def prompt_text(screen, title: str, text: str, label: str, default: str = "") -> str | None:
    result, values = prompt_form(screen, title, text, [(label, default)])
    return values[0] if result else None


def choose(
    screen,
    title: str,
    text: str,
    items: list[tuple[str, object]],
    action: tuple[str, str] = ("Auswählen", "select"),
    cancel: tuple[str, str] = ("Abbrechen", "cancel"),
):
    """Einfachauswahl aus (Anzeigetext, Wert). Rückgabe: Wert, oder None bei Abbruch/ESC."""
    height = min(len(items), MAX_LIST_HEIGHT)
    listbox = Listbox(
        height=height, width=LIST_WIDTH, returnExit=1, scroll=1 if len(items) > height else 0
    )
    for label, value in items:
        listbox.append(label, value)

    buttons = ButtonBar(screen, [action, cancel])
    form = GridForm(screen, title, 1, 3)
    form.add(_text(screen, text), 0, 0)
    form.add(listbox, 0, 1, padding=(0, 1, 0, 1))
    form.add(buttons, 0, 2, growx=1)

    result = run_form(form)
    if is_cancel(result) or buttons.buttonPressed(result) == cancel[1]:
        return None
    # Bei Enter auf einem Eintrag ist result die Listbox (returnExit=1), nicht
    # der Button – das zählt ebenfalls als Auswahl.
    return listbox.current()


def pick_profile(screen, profiles: dict, title: str = "Zugangsdaten wählen"):
    """Zeigt eine Auswahl gespeicherter Zugangsdaten-Profile. Rückgabe: Profilname oder None."""
    if not profiles:
        return None
    items = [
        (f"{name} ({profile.provider}, {profile.username})", name)
        for name, profile in profiles.items()
    ]
    return choose(
        screen,
        title,
        "Zugangsdatenprofil anwenden (optional):",
        items,
        cancel=("Keine", "none"),
    )


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
    tree = CheckboxTree(height=height, width=LIST_WIDTH, scroll=1 if len(names) > height else 0)
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

    result = run_form(form)
    if is_cancel(result) or buttons.buttonPressed(result) != action_value:
        return []
    selected = tree.getSelection()
    if not selected:
        info(screen, title, "Keine Verbindung markiert.")
    return selected
