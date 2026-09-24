"""Zentraler nmcli-Kommando-Wrapper.

Strikt getrennt in reine argv-Builder/Parser (unit-testbar, keine I/O) und
eine einzige Ausführungsfunktion (`run_nmcli`). Nichts in diesem Modul
importiert `snack` – es wird sowohl von der TUI als auch von den Tests in
Umgebungen ohne `nmcli`/`snack` genutzt (via injizierbarem `runner`).
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass

# TYPE-Werte, die `nmcli -t -f NAME,TYPE connection show` für VPN-Verbindungen
# liefert. WireGuard ist ein nativer NM-Verbindungstyp ("wireguard"), OpenVPN
# läuft unter dem generischen VPN-Framework ("vpn"). "openvpn" wird zusätzlich
# akzeptiert, falls eine NM-Version das je unterscheidet.
VPN_TYPES = {"vpn", "wireguard", "openvpn"}

# Verbindungstypen, die Username/Passwort kennen – WireGuard ist schlüsselbasiert
# und taucht deshalb beim Anwenden von Zugangsdaten nicht auf.
PASSWORD_VPN_TYPES = {"vpn", "openvpn"}

# Plugin-Name, wie er am Ende von vpn.service-type steht
# (org.freedesktop.NetworkManager.openvpn).
SERVICE_TYPE_OPENVPN = "openvpn"


class NmcliError(RuntimeError):
    def __init__(self, argv: list[str], returncode: int, stderr: str):
        self.argv = argv
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Kommando fehlgeschlagen ({returncode}): {shlex.join(argv)}\n{stderr}".strip()
        )


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    dry_run: bool = False


def stable_output_env() -> dict[str, str]:
    """Umgebung mit fester Locale, damit nmcli-Ausgaben maschinell lesbar bleiben.

    nmcli übersetzt seine Meldungen (deutsch z. B. „Verbindung »X« (uuid)
    erfolgreich hinzugefügt."), wodurch jedes Parsen ohne feste Locale
    sprachabhängig und damit unzuverlässig wäre.
    """
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    # gettext würde LANGUAGE sonst bevorzugt auswerten.
    env.pop("LANGUAGE", None)
    return env


def run_nmcli(
    args: list[str],
    dry_run: bool = False,
    check: bool = True,
    runner=subprocess.run,
) -> CommandResult:
    """Führt `nmcli <args>` aus (oder druckt es im Dry-Run statt es auszuführen)."""
    argv = ["nmcli", *args]
    if dry_run:
        print("[dry-run] " + shlex.join(argv))
        return CommandResult(argv, 0, "", "", dry_run=True)
    try:
        proc = runner(argv, capture_output=True, text=True, env=stable_output_env())
    except FileNotFoundError as exc:
        raise NmcliError(
            argv, -1, "nmcli nicht gefunden – ist NetworkManager installiert?"
        ) from exc
    result = CommandResult(argv, proc.returncode, proc.stdout, proc.stderr, dry_run=False)
    if check and proc.returncode != 0:
        raise NmcliError(argv, proc.returncode, proc.stderr)
    return result


# ---------------------------------------------------------------------------
# Reine argv-Builder
#
# `identifier` ist überall Name ODER UUID einer Verbindung – laut nmcli(1) wird
# eine Verbindung "by its name, UUID or D-Bus path" identifiziert. Beim Import
# wird bewusst die UUID verwendet, weil sie auch bei doppelten Namen eindeutig
# ist und nicht aus übersetzten Meldungen gelesen werden muss.
# ---------------------------------------------------------------------------


def build_import_command(conn_type: str, file_path: str) -> list[str]:
    return ["connection", "import", "type", conn_type, "file", file_path]


def build_autoconnect_off_command(identifier: str) -> list[str]:
    return ["connection", "modify", identifier, "connection.autoconnect", "no"]


def build_delete_command(identifier: str) -> list[str]:
    return ["connection", "delete", identifier]


def build_list_command() -> list[str]:
    return ["-t", "-f", "NAME,TYPE", "connection", "show"]


def build_uuid_list_command() -> list[str]:
    return ["-t", "-f", "UUID,NAME", "connection", "show"]


def build_autoconnect_list_command() -> list[str]:
    return ["-t", "-f", "NAME,TYPE,AUTOCONNECT", "connection", "show"]


def build_service_type_command(identifier: str) -> list[str]:
    """Fragt das VPN-Plugin einer Verbindung ab (z. B. org.freedesktop.NetworkManager.openvpn)."""
    return ["-t", "-f", "vpn.service-type", "connection", "show", identifier]


def build_vpn_data_string(pairs: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in pairs.items())


def build_openvpn_credentials_commands(
    identifier: str, username: str, password: str
) -> tuple[list[str], list[str]]:
    """Liefert (vpn.data-Kommando, vpn.secrets-Kommando) für OpenVPN-Login."""
    data_cmd = [
        "connection",
        "modify",
        identifier,
        "+vpn.data",
        f"connection-type=password,username={username}",
    ]
    secret_cmd = ["connection", "modify", identifier, "+vpn.secrets", f"password={password}"]
    return data_cmd, secret_cmd


# ---------------------------------------------------------------------------
# Reine Ausgabe-Parser
# ---------------------------------------------------------------------------


def _split_terse_line(line: str) -> list[str]:
    """Splittet eine `nmcli -t`-Zeile an unescapten Doppelpunkten."""
    fields: list[str] = []
    current: list[str] = []
    escape = False
    for ch in line:
        if escape:
            current.append(ch)
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(ch)
    fields.append("".join(current))
    return fields


def parse_connection_list(output: str) -> list[tuple[str, str]]:
    """Parst die Ausgabe von `nmcli -t -f NAME,TYPE connection show` zu (name, type)."""
    connections = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = _split_terse_line(line)
        if len(fields) >= 2:
            connections.append((fields[0], fields[1]))
    return connections


def parse_uuid_list(output: str) -> dict[str, str]:
    """Parst `nmcli -t -f UUID,NAME connection show` zu {uuid: name}."""
    connections = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = _split_terse_line(line)
        if len(fields) >= 2:
            connections[fields[0]] = fields[1]
    return connections


def new_connections(before: dict[str, str], after: dict[str, str]) -> list[tuple[str, str]]:
    """Verbindungen, die in `after`, aber nicht in `before` stehen, als (uuid, name)."""
    return [(uuid, name) for uuid, name in after.items() if uuid not in before]


def parse_autoconnect_list(output: str) -> list[tuple[str, str, bool]]:
    """Parst `nmcli -t -f NAME,TYPE,AUTOCONNECT connection show` zu (name, type, autoconnect).

    Verlässt sich auf die feste Locale aus `stable_output_env()` – ohne sie wäre
    der Wert übersetzt ("ja"/"nein") statt "yes"/"no".
    """
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = _split_terse_line(line)
        if len(fields) >= 3:
            entries.append((fields[0], fields[1], fields[2].strip().lower() == "yes"))
    return entries


def filter_vpn_connections(parsed: list[tuple[str, str]], types: set[str] = VPN_TYPES) -> list[str]:
    return [name for name, ctype in parsed if ctype in types]


def parse_service_type(output: str) -> str:
    """Normalisiert die vpn.service-type-Ausgabe auf den reinen Plugin-Namen.

    Verarbeitet sowohl die Terse-Form (nur der Wert) als auch die normale Form
    ("vpn.service-type:   org.freedesktop.NetworkManager.openvpn").
    """
    value = output.strip()
    if not value:
        return ""
    if ":" in value:
        value = value.split(":")[-1].strip()
    return value.rsplit(".", 1)[-1].lower()


# ---------------------------------------------------------------------------
# Zentraler Helfer (Anforderung: jede Verbindung bekommt autoconnect=no)
# ---------------------------------------------------------------------------


def ensure_autoconnect_off(identifier: str, dry_run: bool, runner=subprocess.run) -> CommandResult:
    return run_nmcli(build_autoconnect_off_command(identifier), dry_run=dry_run, runner=runner)
