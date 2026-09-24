# VPN Manager

Kleine TUI (newt/snack, optisch angelehnt an `nmtui`) für CachyOS/KDE Plasma
(NetworkManager), um viele OpenVPN-/WireGuard-Konfigurationsdateien in einem
Rutsch per `nmcli` zu importieren und zentral zu verwalten – statt für jede
Datei einzeln durch die grafischen Import-Dialoge zu klicken.

Menüpunkte:

- **Zugangsdaten verwalten** – benannte Profile (Anbieter, Username, Passwort)
- **Import** – alle `*.ovpn`/`*.conf` eines Ordners importieren, optional mit Zugangsdaten
- **Zugangsdaten auf Verbindungen anwenden** – mehrere bestehende Verbindungen
  markieren und ein Zugangsdaten-Profil auf alle gleichzeitig anwenden
- **Autoconnect deaktivieren** – zeigt den Autoconnect-Status aller
  VPN-Verbindungen, wählt die aktiven vor und schaltet sie gesammelt ab
- **VPN-Verbindungen löschen** – Mehrfachauswahl per Checkbox

Jede vom Tool importierte Verbindung bekommt automatisch
`connection.autoconnect no` – nichts wählt sich beim Systemstart von selbst ein.

Das Tool installiert selbst keine Software.

## Voraussetzungen

- Python 3.10+
- `nmcli` (NetworkManager) – auf CachyOS mit KDE Plasma bereits vorhanden.
- `newt` (liefert die Python-Bindings `snack`). Fehlt es, nennt das Programm
  beim Start den nötigen Befehl: `sudo pacman -S newt`

OpenVPN und WireGuard funktionieren unter CachyOS out-of-the-box und brauchen
keine Zusatzpakete.

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/MyUncleSam/vpn-tui/master/install.sh | bash
```

Kein `sudo` nötig – installiert wird ins Benutzerverzeichnis:

- Code: `~/.local/share/vpn-tui`
- Befehl: `~/.local/bin/vpn-tui`

Derselbe Befehl aktualisiert eine vorhandene Installation (`git pull`). Weil
alles dem Benutzer gehört, kann auch das Selbst-Update beim Start ohne
Sonderrechte arbeiten.

Der Installer installiert **keine** Software – fehlt `newt` oder
NetworkManager, nennt er am Ende nur den passenden `pacman`-Befehl. Liegt im
Zielverzeichnis etwas, das nicht zu diesem Projekt gehört, bricht er ab, statt
es anzufassen. Liegt `~/.local/bin` nicht im `PATH`, weist er darauf hin.

Zielpfade lassen sich überschreiben:

```bash
curl -fsSL .../install.sh | VPN_TUI_DIR=~/git/vpn-tui VPN_TUI_BIN=~/bin/vpn-tui bash
```

Deinstallieren:

```bash
rm -rf ~/.local/share/vpn-tui ~/.local/bin/vpn-tui
```

## Start

```bash
vpn-tui
```

Mit `--dry-run` werden alle `nmcli`-Kommandos nur ausgegeben statt ausgeführt –
empfehlenswert für den ersten Testlauf, um die generierten Kommandos zu prüfen,
bevor etwas real verändert wird:

```bash
vpn-tui --dry-run
```

Ohne Installation geht es auch direkt aus dem Repository-Verzeichnis:

```bash
python3 main.py
```

### Selbst-Update beim Start

Beim Start wird kurz `git pull --ff-only` im eigenen Verzeichnis ausgeführt,
damit immer die aktuelle Version läuft. Das blockiert den Start nie:

- Timeout von 5 Sekunden – ohne Internet startet das Tool einfach weiter
- git darf dabei nicht nach Zugangsdaten fragen (`GIT_TERMINAL_PROMPT=0`),
  sonst würde ein Prompt am Timeout vorbei hängen bleiben
- lokale Änderungen werden durch `--ff-only` nie überschrieben
- das Ergebnis erscheint als Hinweiszeile im Hauptmenü

Abschalten mit `--no-update`; bei `--dry-run` unterbleibt es ohnehin, weil
dabei nichts verändert wird:

```bash
vpn-tui --no-update
```

## Umgang mit lokalisierten nmcli-Ausgaben

nmcli übersetzt seine Ausgaben – und zwar nicht nur Meldungen, sondern auch
Werte wie `yes`/`no` (→ `ja`/`nein`), selbst in der Terse-Ausgabe `-t`. Nicht
übersetzt werden Exit-Codes und Bezeichner (`NAME`, `UUID`, `TYPE`).

Das Tool geht deshalb zweigleisig vor:

- alle nmcli-Aufrufe laufen mit `LC_ALL=C` (siehe `nmcli.stable_output_env`)
- beim Import wird die neu angelegte Verbindung nicht aus der Erfolgsmeldung
  gelesen, sondern über die Differenz der UUID-Liste vor/nach dem Import
  ermittelt (`nmcli.new_connections`). Adressiert wird anschließend über die
  UUID – eindeutig auch bei doppelten Verbindungsnamen.

## Offener Punkt: gespeicherte Passwörter

Fragt NetworkManager trotz hinterlegtem Passwort beim Verbinden weiterhin
danach, fehlt vermutlich `password-flags=0` in `vpn.data` (Passwort systemweit
speichern statt vom Agent abfragen). Ergänzt würde das zentral in
`nmcli.build_openvpn_credentials_commands` – die Funktion wird von „Import“ und
„Zugangsdaten anwenden“ gemeinsam genutzt.

## Zugangsdaten-Speicherung

Zugangsdaten-Profile (Anbieter/Username/Passwort) liegen als Klartext-JSON in
`~/.config/vpn-manager/credentials.json` (Datei `chmod 600`, Verzeichnis
`chmod 700`) – bewusst einfach gehalten, kein System-Keyring.

## Tests

```bash
python3 -m unittest discover -s tests
```

Deckt die komplette Logik (nmcli-Kommandoaufbau, Credential-CRUD, Ordner-Scan)
sowie den Ablauf aller TUI-Screens ab – ohne dass `nmcli` oder `snack`
installiert sein müssen. Die Screens selbst müssen auf dem Zielsystem manuell
durchgespielt werden.
