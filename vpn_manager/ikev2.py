"""IKEv2/IPsec-Verbindungen über den strongswan-NetworkManager-Plugin (networkmanager-strongswan).

Anders als OpenVPN/WireGuard gibt es kein Standard-Dateiformat zum Import –
eine Verbindung wird direkt aus einer Gateway-Adresse (+ optionalen
Zugangsdaten) angelegt.
"""

from __future__ import annotations

from vpn_manager import nmcli

# TODO: Auf dem Zielsystem verifizieren (`man nm-settings-strongswan` bzw.
# `nmcli connection edit type vpn` -> `print vpn.data`). Nur zertifikatsbasierte
# Beispiele waren recherchierbar; für EAP-Username/Passwort ist dieser Key
# die plausibelste, aber unbestätigte Annahme. nmcli meldet unbekannte
# vpn.data-Properties mit einer selbsterklärenden Fehlermeldung.
STRONGSWAN_USERNAME_KEY = "eap_identity"


def build_strongswan_vpn_data(gateway: str) -> dict[str, str]:
    return {"address": gateway, "method": "eap", "ipcomp": "no", "encap": "no"}


def build_add_ikev2_command(name: str, gateway: str) -> list[str]:
    data = nmcli.build_vpn_data_string(build_strongswan_vpn_data(gateway))
    return [
        "connection",
        "add",
        "type",
        "vpn",
        "vpn-type",
        "strongswan",
        "con-name",
        name,
        "vpn.data",
        data,
    ]


def build_apply_credentials_commands(
    name: str, username: str, password: str
) -> tuple[list[str], list[str]]:
    """Liefert (vpn.data-Kommando, vpn.secrets-Kommando) für EAP-Login."""
    data_cmd = ["connection", "modify", name, "+vpn.data", f"{STRONGSWAN_USERNAME_KEY}={username}"]
    secret_cmd = ["connection", "modify", name, "+vpn.secrets", f"password={password}"]
    return data_cmd, secret_cmd
