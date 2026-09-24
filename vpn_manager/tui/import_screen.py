"""Screen: Ordner mit *.ovpn/*.conf-Dateien in einem Rutsch importieren."""

from __future__ import annotations

from pathlib import Path

from vpn_manager import credentials as creds
from vpn_manager import importer, nmcli
from vpn_manager.tui import common


def run(screen, dry_run: bool) -> None:
    folder_str = common.prompt_text(screen, "Import", "Ordner mit *.ovpn/*.conf-Dateien:")
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
        profiles = creds.load_profiles()
        chosen = common.pick_profile(screen, profiles, title="Zugangsdaten für OpenVPN (optional)")
        if chosen:
            profile = profiles[chosen]

    results = []
    for item in items:
        try:
            res = nmcli.run_nmcli(
                nmcli.build_import_command(item.conn_type, str(item.path)), dry_run=dry_run
            )
            name = item.path.stem if dry_run else nmcli.parse_import_output(res.stdout)
            if name is None:
                results.append(f"{item.path.name}: Import ok, Verbindungsname nicht erkannt")
                continue

            nmcli.ensure_autoconnect_off(name, dry_run=dry_run)

            if item.conn_type == "openvpn" and profile is not None:
                data_cmd, secret_cmd = nmcli.build_openvpn_credentials_commands(
                    name, profile.username, profile.password
                )
                nmcli.run_nmcli(data_cmd, dry_run=dry_run)
                nmcli.run_nmcli(secret_cmd, dry_run=dry_run)

            results.append(f"{item.path.name}: OK ({name})")
        except nmcli.NmcliError as exc:
            results.append(f"{item.path.name}: FEHLER - {exc}")

    common.info(screen, "Import abgeschlossen", "\n".join(results))
