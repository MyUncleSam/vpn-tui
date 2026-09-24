"""Zentraler nmcli-Kommando-Wrapper.

Strikt getrennt in reine argv-Builder/Parser (unit-testbar, keine I/O) und
eine einzige Ausführungsfunktion (`run_nmcli`). Nichts in diesem Modul
importiert `snack` – es wird sowohl von der TUI als auch von den Tests in
Umgebungen ohne `nmcli`/`snack` genutzt (via injizierbarem `runner`).
"""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass

# TYPE-Werte, die `nmcli -t -f NAME,TYPE connection show` für VPN-Verbindungen
# liefert. WireGuard-Verbindungen sind ein nativer NM-Verbindungstyp
# ("wireguard"), OpenVPN und IKEv2/strongswan laufen beide unter dem
# generischen VPN-Framework ("vpn"). "openvpn" wird zusätzlich akzeptiert,
# falls eine NM-Version das je unterscheidet.
VPN_TYPES = {"vpn", "wireguard", "openvpn"}

_IMPORT_OK_RE = re.compile(r"Connection '(.+)' \(.+\) successfully added")


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
        proc = runner(argv, capture_output=True, text=True)
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
# ---------------------------------------------------------------------------


def build_import_command(conn_type: str, file_path: str) -> list[str]:
    return ["connection", "import", "type", conn_type, "file", file_path]


def build_autoconnect_off_command(name: str) -> list[str]:
    return ["connection", "modify", name, "connection.autoconnect", "no"]


def build_delete_command(name: str) -> list[str]:
    return ["connection", "delete", name]


def build_list_command() -> list[str]:
    return ["-t", "-f", "NAME,TYPE", "connection", "show"]


def build_vpn_data_string(pairs: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in pairs.items())


def build_openvpn_credentials_commands(
    name: str, username: str, password: str
) -> tuple[list[str], list[str]]:
    """Liefert (vpn.data-Kommando, vpn.secrets-Kommando) für OpenVPN-Login."""
    data_cmd = [
        "connection",
        "modify",
        name,
        "+vpn.data",
        f"connection-type=password,username={username}",
    ]
    secret_cmd = ["connection", "modify", name, "+vpn.secrets", f"password={password}"]
    return data_cmd, secret_cmd


# ---------------------------------------------------------------------------
# Reine Ausgabe-Parser
# ---------------------------------------------------------------------------


def parse_import_output(stdout: str) -> str | None:
    """Extrahiert den Verbindungsnamen aus der Erfolgsmeldung von `connection import`."""
    match = _IMPORT_OK_RE.search(stdout)
    return match.group(1) if match else None


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


def filter_vpn_connections(parsed: list[tuple[str, str]]) -> list[str]:
    return [name for name, ctype in parsed if ctype in VPN_TYPES]


# ---------------------------------------------------------------------------
# Zentraler Helfer (Anforderung: jede Verbindung bekommt autoconnect=no)
# ---------------------------------------------------------------------------


def ensure_autoconnect_off(name: str, dry_run: bool, runner=subprocess.run) -> CommandResult:
    return run_nmcli(build_autoconnect_off_command(name), dry_run=dry_run, runner=runner)
