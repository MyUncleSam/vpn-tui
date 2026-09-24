#!/usr/bin/env bash
#
# One-Line-Installer für vpn-tui:
#
#   curl -fsSL https://raw.githubusercontent.com/MyUncleSam/vpn-tui/master/install.sh | sudo bash
#
# Klont das Repository nach /opt/vpn-tui und legt den Befehl `vpn-tui` an.
# Ist die Installation schon vorhanden, wird sie stattdessen aktualisiert.
# Es wird keinerlei zusätzliche Software installiert – fehlende Abhängigkeiten
# werden am Ende nur benannt.
#
# Anpassbar über Umgebungsvariablen:
#   VPN_TUI_DIR   Zielverzeichnis      (Standard: /opt/vpn-tui)
#   VPN_TUI_BIN   Pfad des Befehls     (Standard: /usr/local/bin/vpn-tui)
#   VPN_TUI_REPO  Quell-Repository     (Standard: GitHub über HTTPS)

set -euo pipefail

REPO_URL="${VPN_TUI_REPO:-https://github.com/MyUncleSam/vpn-tui.git}"
INSTALL_DIR="${VPN_TUI_DIR:-/opt/vpn-tui}"
BIN_PATH="${VPN_TUI_BIN:-/usr/local/bin/vpn-tui}"

die() {
    echo "Fehler: $*" >&2
    exit 1
}

command -v git >/dev/null || die "git ist nicht installiert."
command -v python3 >/dev/null || die "python3 ist nicht installiert."

if [[ -e "$INSTALL_DIR" ]]; then
    # Vorhandenes Verzeichnis nur anfassen, wenn es wirklich diese Installation ist.
    [[ -d "$INSTALL_DIR/.git" ]] ||
        die "$INSTALL_DIR existiert, ist aber kein Git-Repository. Bitte manuell prüfen."
    existing_remote="$(git -C "$INSTALL_DIR" remote get-url origin 2>/dev/null || true)"
    [[ "$existing_remote" == *vpn-tui* ]] ||
        die "$INSTALL_DIR gehört zu einem anderen Projekt (${existing_remote:-kein origin}). Abbruch."
    [[ -w "$INSTALL_DIR" ]] || die "Keine Schreibrechte in $INSTALL_DIR – bitte mit sudo ausführen."

    echo "Aktualisiere vorhandene Installation in $INSTALL_DIR ..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    parent_dir="$(dirname "$INSTALL_DIR")"
    [[ -d "$parent_dir" ]] || die "$parent_dir existiert nicht."
    [[ -w "$parent_dir" ]] || die "Keine Schreibrechte in $parent_dir – bitte mit sudo ausführen."

    echo "Klone $REPO_URL nach $INSTALL_DIR ..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

[[ -f "$INSTALL_DIR/main.py" ]] || die "$INSTALL_DIR/main.py fehlt – unerwarteter Repository-Inhalt."

bin_dir="$(dirname "$BIN_PATH")"
[[ -d "$bin_dir" ]] || die "$bin_dir existiert nicht."
[[ -w "$bin_dir" ]] || die "Keine Schreibrechte in $bin_dir – bitte mit sudo ausführen."

echo "Richte Befehl $BIN_PATH ein ..."
cat >"$BIN_PATH" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod 755 "$BIN_PATH"

# Laufzeit-Abhängigkeiten nur prüfen, nicht installieren.
missing=()
python3 -c "import snack" 2>/dev/null ||
    missing+=("newt (Python-Modul 'snack')   ->  sudo pacman -S newt")
command -v nmcli >/dev/null ||
    missing+=("NetworkManager (nmcli)        ->  sudo pacman -S networkmanager")

echo
echo "Fertig. Start mit:  $(basename "$BIN_PATH")"
echo "Vorschau ohne Änderungen:  $(basename "$BIN_PATH") --dry-run"

if [[ ${#missing[@]} -gt 0 ]]; then
    echo
    echo "Dafür fehlt noch:"
    printf '  - %s\n' "${missing[@]}"
fi
