"""Screen: IKEv2/IPsec-Verbindung aus Name + Gateway-Adresse anlegen (kein Datei-Import)."""

from __future__ import annotations

from vpn_manager import credentials as creds
from vpn_manager import ikev2, nmcli
from vpn_manager.tui import common


def run(screen, dry_run: bool) -> None:
    result, values = common.prompt_form(
        screen,
        "IKEv2/IPsec-Verbindung anlegen",
        [("Verbindungsname", ""), ("Gateway-Adresse", "")],
    )
    if result is None:
        return
    name, gateway = values
    if not name or not gateway:
        common.info(screen, "Fehler", "Name und Gateway-Adresse sind erforderlich.")
        return

    profiles = creds.load_profiles()
    chosen = common.pick_profile(screen, profiles, title="Zugangsdaten (optional)")
    profile = profiles[chosen] if chosen else None

    try:
        nmcli.run_nmcli(ikev2.build_add_ikev2_command(name, gateway), dry_run=dry_run)
        nmcli.ensure_autoconnect_off(name, dry_run=dry_run)
        if profile is not None:
            data_cmd, secret_cmd = ikev2.build_apply_credentials_commands(
                name, profile.username, profile.password
            )
            nmcli.run_nmcli(data_cmd, dry_run=dry_run)
            nmcli.run_nmcli(secret_cmd, dry_run=dry_run)
    except nmcli.NmcliError as exc:
        common.info(screen, "Fehler", str(exc))
        return

    common.info(screen, "Fertig", f"IKEv2-Verbindung '{name}' angelegt (autoconnect: aus).")
