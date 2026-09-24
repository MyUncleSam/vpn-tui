"""Screen: bei mehreren bestehenden VPN-Verbindungen `connection.autoconnect` abschalten.

Nützlich für Verbindungen, die nicht über dieses Tool angelegt wurden (oder vor
dem Locale-Fix importiert wurden) und sich deshalb noch automatisch einwählen.
"""

from __future__ import annotations

from vpn_manager import nmcli
from vpn_manager.tui import common


def run(screen, dry_run: bool) -> None:
    try:
        listing = nmcli.run_nmcli(nmcli.build_autoconnect_list_command(), dry_run=False)
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", str(exc))
        return

    entries = [
        (name, autoconnect)
        for name, conn_type, autoconnect in nmcli.parse_autoconnect_list(listing.stdout)
        if conn_type in nmcli.VPN_TYPES
    ]
    if not entries:
        common.info(screen, "Autoconnect", "Keine VPN-Verbindungen gefunden.")
        return

    enabled = {name for name, autoconnect in entries if autoconnect}
    if not enabled:
        common.info(
            screen,
            "Autoconnect",
            "Bei allen VPN-Verbindungen ist autoconnect bereits deaktiviert.",
        )
        return

    names = [name for name, _ in entries]
    labels = {
        name: f"{name}  (autoconnect: {'AN' if autoconnect else 'aus'})"
        for name, autoconnect in entries
    }

    selected = common.pick_connections(
        screen,
        names,
        "Autoconnect deaktivieren",
        "Vorausgewählt sind alle Verbindungen mit aktivem Autoconnect (Leertaste ändert):",
        "Deaktivieren",
        "disable",
        labels=labels,
        preselect=enabled,
    )
    if not selected:
        return

    results = []
    for name in selected:
        try:
            nmcli.ensure_autoconnect_off(name, dry_run=dry_run)
            results.append(f"{name}: OK")
        except nmcli.NmcliError as exc:
            results.append(f"{name}: FEHLER - {exc}")

    common.info(screen, "Fertig", "\n".join(results))
