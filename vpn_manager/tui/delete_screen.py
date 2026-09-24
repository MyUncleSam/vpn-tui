"""Screen: beliebige VPN-Verbindungen per Checkbox-Mehrfachauswahl löschen."""

from __future__ import annotations

from snack import ButtonBar, CheckboxTree, GridForm, Label

from vpn_manager import nmcli
from vpn_manager.tui import common


def run(screen, dry_run: bool) -> None:
    try:
        result = nmcli.run_nmcli(nmcli.build_list_command(), dry_run=False)
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", str(exc))
        return

    names = nmcli.filter_vpn_connections(nmcli.parse_connection_list(result.stdout))
    if not names:
        common.info(screen, "Löschen", "Keine VPN-Verbindungen gefunden.")
        return

    tree = CheckboxTree(height=min(len(names), 15), width=50)
    for name in names:
        tree.append(name, name)

    buttons = ButtonBar(screen, [("Löschen", "delete"), ("Zurück", "back")])
    form = GridForm(screen, "VPN-Verbindungen löschen", 1, 3)
    form.add(Label("Zu löschende Verbindungen markieren (Leertaste):"), 0, 0)
    form.add(tree, 0, 1)
    form.add(buttons, 0, 2, growx=1)

    result = form.runOnce()
    if buttons.buttonPressed(result) != "delete":
        return

    selected = tree.getSelection()
    if not selected:
        common.info(screen, "Löschen", "Keine Verbindung ausgewählt.")
        return

    if not common.confirm(screen, "Bestätigen", f"{len(selected)} Verbindung(en) wirklich löschen?"):
        return

    results = []
    for name in selected:
        try:
            nmcli.run_nmcli(nmcli.build_delete_command(name), dry_run=dry_run)
            results.append(f"{name}: OK")
        except nmcli.NmcliError as exc:
            results.append(f"{name}: FEHLER - {exc}")

    common.info(screen, "Fertig", "\n".join(results))
