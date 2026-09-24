"""Screen: Zugangsdaten-Profile verwalten (Anbieter, Username, Passwort)."""

from __future__ import annotations

from snack import ButtonBar, Entry, GridForm, Label, Listbox

from vpn_manager import credentials as creds
from vpn_manager.tui import common


def _edit_form(screen, title: str, provider: str = "", username: str = "", password: str = ""):
    provider_entry = Entry(30, provider)
    username_entry = Entry(30, username)
    password_entry = Entry(30, password, password=1)

    buttons = ButtonBar(screen, [("Speichern", "save"), ("Abbrechen", "cancel")])
    form = GridForm(screen, title, 2, 4)
    form.add(Label("Anbieter:"), 0, 0)
    form.add(provider_entry, 1, 0)
    form.add(Label("Username:"), 0, 1)
    form.add(username_entry, 1, 1)
    form.add(Label("Passwort:"), 0, 2)
    form.add(password_entry, 1, 2)
    form.add(buttons, 0, 3, growx=1)

    result = form.runOnce()
    if buttons.buttonPressed(result) != "save":
        return None
    return provider_entry.value(), username_entry.value(), password_entry.value()


def run(screen, dry_run: bool) -> None:
    while True:
        profiles = creds.load_profiles()
        items = [
            (f"{name} ({profile.provider}, {profile.username})", name)
            for name, profile in profiles.items()
        ]

        listbox = Listbox(height=min(max(len(items), 1), 10), width=50, returnExit=0)
        for text, value in items:
            listbox.append(text, value)
        if not items:
            listbox.append("(keine Profile gespeichert)", None)

        buttons = ButtonBar(
            screen, [("Neu", "new"), ("Bearbeiten", "edit"), ("Löschen", "delete"), ("Zurück", "back")]
        )
        form = GridForm(screen, "Zugangsdaten verwalten", 1, 2)
        form.add(listbox, 0, 0)
        form.add(buttons, 0, 1, growx=1)
        result = form.runOnce()
        action = buttons.buttonPressed(result)

        if action in (None, "back"):
            return

        selected = listbox.current()

        if action == "new":
            name = common.prompt_text(screen, "Neues Profil", "Profilname:")
            if not name:
                continue
            if name in profiles:
                common.info(screen, "Fehler", f"Profil '{name}' existiert bereits.")
                continue
            values = _edit_form(screen, "Neues Profil")
            if values is None:
                continue
            provider, username, password = values
            profiles = creds.add_profile(profiles, name, provider, username, password)
            creds.save_profiles(profiles)

        elif action == "edit":
            if not selected:
                continue
            profile = profiles[selected]
            values = _edit_form(
                screen, f"Profil bearbeiten: {selected}", profile.provider, profile.username, profile.password
            )
            if values is None:
                continue
            provider, username, password = values
            profiles = creds.update_profile(profiles, selected, provider, username, password)
            creds.save_profiles(profiles)

        elif action == "delete":
            if not selected:
                continue
            if common.confirm(screen, "Bestätigen", f"Profil '{selected}' wirklich löschen?"):
                profiles = creds.delete_profile(profiles, selected)
                creds.save_profiles(profiles)
