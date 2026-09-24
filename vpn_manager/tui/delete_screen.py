"""Screen: beliebige VPN-Verbindungen per Checkbox-Mehrfachauswahl löschen."""

from __future__ import annotations

from vpn_manager import nmcli
from vpn_manager.tui import common


def run(screen, dry_run: bool) -> None:
    try:
        listing = nmcli.run_nmcli(nmcli.build_list_command(), dry_run=False)
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", str(exc))
        return

    names = nmcli.filter_vpn_connections(nmcli.parse_connection_list(listing.stdout))
    if not names:
        common.info(screen, "Löschen", "Keine VPN-Verbindungen gefunden.")
        return

    selected = common.pick_connections(
        screen,
        names,
        "VPN-Verbindungen löschen",
        "Zu löschende Verbindungen markieren (Leertaste):",
        "Löschen",
        "delete",
    )
    if not selected:
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
