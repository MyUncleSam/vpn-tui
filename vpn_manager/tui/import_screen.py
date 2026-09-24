"""Screen: Ordner mit *.ovpn/*.conf-Dateien in einem Rutsch importieren."""

from __future__ import annotations

from pathlib import Path

from vpn_manager import credentials as creds
from vpn_manager import importer, nmcli
from vpn_manager.tui import common


def _connection_snapshot() -> dict[str, str]:
    """{uuid: name} aller Verbindungen – lesend, läuft auch im Dry-Run echt."""
    result = nmcli.run_nmcli(nmcli.build_uuid_list_command(), dry_run=False)
    return nmcli.parse_uuid_list(result.stdout)


def run(screen, dry_run: bool) -> None:
    folder_str = common.prompt_text(
        screen,
        "Import",
        "Aus welchem Ordner sollen die Konfigurationsdateien importiert werden?\n"
        "(*.ovpn für OpenVPN, *.conf für WireGuard)",
        "Ordner:",
    )
    if not folder_str:
        return
    folder = Path(folder_str).expanduser()
    if not folder.is_dir():
        common.info(screen, "Fehler", f"'{folder}' ist kein Ordner.")
        return

    items = importer.scan_folder(folder)
    if not items:
        common.info(screen, "Import", "Keine *.ovpn/*.conf-Dateien in diesem Ordner gefunden.")
        return

    ovpn_count = sum(1 for i in items if i.conn_type == "openvpn")
    wg_count = sum(1 for i in items if i.conn_type == "wireguard")

    summary = f"{wg_count} WireGuard- und {ovpn_count} OpenVPN-Datei(en) gefunden."
    if ovpn_count == 0:
        summary += " (WireGuard verwendet keine Zugangsdaten.)"
    if not common.confirm(screen, "Import bestätigen", summary + "\n\nJetzt importieren?"):
        return

    profile = None
    if ovpn_count > 0:
        try:
            profiles = creds.load_profiles()
        except creds.CredentialsFileError as exc:
            common.info(screen, "Warnung", f"{exc}\n\nImport läuft ohne Zugangsdaten weiter.")
            profiles = {}
        chosen = common.pick_profile(screen, profiles, title="Zugangsdaten für OpenVPN (optional)")
        if chosen:
            profile = profiles[chosen]

    try:
        known = _connection_snapshot()
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", f"Verbindungsliste nicht lesbar:\n{exc}")
        return

    results = []
    for item in items:
        try:
            nmcli.run_nmcli(
                nmcli.build_import_command(item.conn_type, str(item.path)), dry_run=dry_run
            )
        except nmcli.NmcliError as exc:
            results.append(f"{item.path.name}: FEHLER beim Import - {exc}")
            continue

        if dry_run:
            identifier = name = item.path.stem
        else:
            try:
                current = _connection_snapshot()
            except nmcli.NmcliError as exc:
                results.append(f"{item.path.name}: Import OK, Verbindungsliste nicht lesbar - {exc}")
                continue
            created = nmcli.new_connections(known, current)
            known = current
            if not created:
                results.append(f"{item.path.name}: Import lief durch, neue Verbindung nicht gefunden")
                continue
            # Adressierung über die UUID: eindeutig auch bei doppelten Namen.
            identifier, name = created[0]

        try:
            nmcli.ensure_autoconnect_off(identifier, dry_run=dry_run)
        except nmcli.NmcliError as exc:
            results.append(
                f"{item.path.name}: Import OK ({name}), aber autoconnect konnte NICHT "
                f"deaktiviert werden - {exc}"
            )
            continue

        try:
            if item.conn_type == "openvpn" and profile is not None:
                data_cmd, secret_cmd = nmcli.build_openvpn_credentials_commands(
                    identifier, profile.username, profile.password
                )
                nmcli.run_nmcli(data_cmd, dry_run=dry_run)
                nmcli.run_nmcli(secret_cmd, dry_run=dry_run)
            results.append(f"{item.path.name}: OK ({name})")
        except nmcli.NmcliError as exc:
            results.append(f"{item.path.name}: Import OK ({name}), Zugangsdaten FEHLER - {exc}")

    common.info(screen, "Import abgeschlossen", "\n".join(results))
