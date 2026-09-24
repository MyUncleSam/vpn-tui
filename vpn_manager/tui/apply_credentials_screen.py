"""Screen: gespeicherte Zugangsdaten auf mehrere bestehende VPN-Verbindungen anwenden."""

from __future__ import annotations

from vpn_manager import credentials as creds
from vpn_manager import nmcli
from vpn_manager.tui import common


def _service_type_of(name: str) -> str:
    # Lesender Aufruf – läuft auch im Dry-Run echt, sonst wäre der VPN-Typ unbekannt.
    result = nmcli.run_nmcli(nmcli.build_service_type_command(name), dry_run=False)
    return nmcli.parse_service_type(result.stdout)


def run(screen, dry_run: bool) -> None:
    try:
        listing = nmcli.run_nmcli(nmcli.build_list_command(), dry_run=False)
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", str(exc))
        return

    names = nmcli.filter_vpn_connections(
        nmcli.parse_connection_list(listing.stdout), types=nmcli.PASSWORD_VPN_TYPES
    )
    if not names:
        common.info(
            screen,
            "Zugangsdaten anwenden",
            "Keine passenden VPN-Verbindungen gefunden.\n\n"
            "WireGuard-Verbindungen sind schlüsselbasiert und werden hier nicht aufgeführt.",
        )
        return

    selected = common.pick_connections(
        screen,
        names,
        "Zugangsdaten anwenden",
        "Verbindungen markieren (Leertaste), die die Zugangsdaten erhalten sollen:",
        "Weiter",
        "apply",
    )
    if not selected:
        return

    try:
        profiles = creds.load_profiles()
    except creds.CredentialsFileError as exc:
        common.info(screen, "Fehler", str(exc))
        return
    if not profiles:
        common.info(
            screen, "Zugangsdaten anwenden", "Es sind noch keine Zugangsdaten-Profile gespeichert."
        )
        return

    chosen = common.pick_profile(screen, profiles, title="Zugangsdaten auswählen")
    if not chosen:
        return
    profile = profiles[chosen]

    if not common.confirm(
        screen,
        "Bestätigen",
        f"Zugangsdaten '{chosen}' (Username: {profile.username}) auf "
        f"{len(selected)} Verbindung(en) anwenden?",
    ):
        return

    results = []
    for name in selected:
        try:
            service_type = _service_type_of(name)
        except nmcli.NmcliError as exc:
            results.append(f"{name}: FEHLER - {exc}")
            continue

        # Nur OpenVPN kennt die hier gesetzten Username/Passwort-Keys; andere
        # Plugins bekämen sonst unbrauchbare Einträge.
        if service_type != nmcli.SERVICE_TYPE_OPENVPN:
            results.append(
                f"{name}: übersprungen - VPN-Typ '{service_type or 'unbekannt'}' "
                "nutzt keine Zugangsdaten"
            )
            continue

        try:
            data_cmd, secret_cmd = nmcli.build_openvpn_credentials_commands(
                name, profile.username, profile.password
            )
            nmcli.run_nmcli(data_cmd, dry_run=dry_run)
            nmcli.run_nmcli(secret_cmd, dry_run=dry_run)
            results.append(f"{name}: OK")
        except nmcli.NmcliError as exc:
            results.append(f"{name}: FEHLER - {exc}")

    common.info(screen, "Fertig", "\n".join(results))
