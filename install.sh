#!/usr/bin/env bash
#
# One-Line-Installer für vpn-tui:
#
#   curl -fsSL https://raw.githubusercontent.com/MyUncleSam/vpn-tui/master/install.sh | bash
#
# Installiert ins Benutzerverzeichnis – kein sudo nötig, und das Selbst-Update
# beim Start kann ohne Sonderrechte pullen:
#
#   Code:    ~/.local/share/vpn-tui
#   Befehl:  ~/.local/bin/vpn-tui
#
# Ist die Installation schon vorhanden, wird sie stattdessen aktualisiert.
# Es wird keinerlei zusätzliche Software installiert – fehlende Abhängigkeiten
# werden am Ende nur benannt.
#
# Anpassbar über Umgebungsvariablen:
#   VPN_TUI_DIR   Zielverzeichnis      (Standard: ~/.local/share/vpn-tui)
#   VPN_TUI_BIN   Pfad des Befehls     (Standard: ~/.local/bin/vpn-tui)
#   VPN_TUI_REPO  Quell-Repository     (Standard: GitHub über HTTPS)

set -euo pipefail

REPO_URL="${VPN_TUI_REPO:-https://github.com/MyUncleSam/vpn-tui.git}"
INSTALL_DIR="${VPN_TUI_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/vpn-tui}"
BIN_PATH="${VPN_TUI_BIN:-$HOME/.local/bin/vpn-tui}"

die() {
    echo "Fehler: $*" >&2
    exit 1
}

if [[ $EUID -eq 0 && -z "${VPN_TUI_DIR:-}" ]]; then
    die "Bitte ohne sudo ausführen – installiert wird ins Benutzerverzeichnis.
       (Für einen anderen Ort VPN_TUI_DIR und VPN_TUI_BIN setzen.)"
fi

command -v git >/dev/null || die "git ist nicht installiert."
command -v python3 >/dev/null || die "python3 ist nicht installiert."

if [[ -e "$INSTALL_DIR" ]]; then
    # Vorhandenes Verzeichnis nur anfassen, wenn es wirklich diese Installation ist.
    [[ -d "$INSTALL_DIR/.git" ]] ||
        die "$INSTALL_DIR existiert, ist aber kein Git-Repository. Bitte manuell prüfen."
    existing_remote="$(git -C "$INSTALL_DIR" remote get-url origin 2>/dev/null || true)"
    [[ "$existing_remote" == *vpn-tui* ]] ||
        die "$INSTALL_DIR gehört zu einem anderen Projekt (${existing_remote:-kein origin}). Abbruch."

    echo "Aktualisiere vorhandene Installation in $INSTALL_DIR ..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    mkdir -p "$(dirname "$INSTALL_DIR")"
    echo "Klone $REPO_URL nach $INSTALL_DIR ..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

[[ -f "$INSTALL_DIR/main.py" ]] || die "$INSTALL_DIR/main.py fehlt – unerwarteter Repository-Inhalt."

bin_dir="$(dirname "$BIN_PATH")"
mkdir -p "$bin_dir"

echo "Richte Befehl $BIN_PATH ein ..."
cat >"$BIN_PATH" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod 755 "$BIN_PATH"

command_name="$(basename "$BIN_PATH")"

echo
echo "Fertig. Start mit:  $command_name"
echo "Vorschau ohne Änderungen:  $command_name --dry-run"

# Laufzeit-Abhängigkeiten nur prüfen, nicht installieren.
missing=()
python3 -c "import snack" 2>/dev/null ||
    missing+=("newt (Python-Modul 'snack')   ->  sudo pacman -S newt")
command -v nmcli >/dev/null ||
    missing+=("NetworkManager (nmcli)        ->  sudo pacman -S networkmanager")

if [[ ${#missing[@]} -gt 0 ]]; then
    echo
    echo "Dafür fehlt noch:"
    printf '  - %s\n' "${missing[@]}"
fi

case ":${PATH}:" in
    *":$bin_dir:"*) ;;
    *)
        echo
        echo "Hinweis: $bin_dir liegt nicht in deinem PATH."
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && exec bash"
        ;;
esac

# Ältere systemweite Installation würde den neuen Befehl im PATH überdecken.
old_bin="/usr/local/bin/vpn-tui"
if [[ "$BIN_PATH" != "$old_bin" && -e "$old_bin" ]]; then
    echo
    echo "Hinweis: Es existiert noch eine ältere systemweite Installation, die"
    echo "im PATH vermutlich Vorrang hat. Entfernen mit:"
    echo "  sudo rm -rf /opt/vpn-tui $old_bin"
fi
