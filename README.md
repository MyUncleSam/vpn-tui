# VPN Manager

Kleine TUI (newt/snack, optisch angelehnt an `nmtui`) für CachyOS/KDE Plasma
(NetworkManager), um viele OpenVPN-/WireGuard-Konfigurationsdateien in einem
Rutsch per `nmcli` zu importieren, IKEv2/IPsec-Verbindungen anzulegen und
VPN-Verbindungen zentral zu verwalten – statt für jede Datei einzeln durch
die grafische Import-Dialoge zu klicken.

Jede vom Tool angelegte/importierte Verbindung bekommt automatisch
`connection.autoconnect no` – nichts wählt sich beim Systemstart von selbst ein.

## Voraussetzungen

- Python 3.10+
- `newt` (Arch/CachyOS-Paket, liefert die Python-Bindings `snack`). Fehlt es
  beim Start, bietet das Programm einmalig an, es per `pacman` zu installieren.
- `nmcli` (NetworkManager) – auf CachyOS mit KDE Plasma in der Regel bereits
  vorhanden.
- Für den Import/Verwaltung: `networkmanager-openvpn`, `wireguard-tools`,
  `networkmanager-strongswan` (inkl. `strongswan`) – Menüpunkt „Vorbereitung“
  prüft und installiert diese bei Bedarf.

## Start

```bash
python3 main.py
```

Mit `--dry-run` werden alle `nmcli`-/`pacman`-Kommandos nur ausgegeben statt
ausgeführt – empfehlenswert für den allerersten Testlauf, um die generierten
Kommandos zu prüfen, bevor irgendetwas real verändert wird:

```bash
python3 main.py --dry-run
```

Optional per `pipx install .` bzw. `pip install --user .` installierbar,
danach als `vpn-manager` aufrufbar.

## Bekannte Unsicherheit: IKEv2/EAP-Username

Der `vpn.data`-Key für EAP-Username beim strongswan-NetworkManager-Plugin
(`STRONGSWAN_USERNAME_KEY` in `vpn_manager/ikev2.py`, aktuell `eap_identity`)
ist nicht mit letzter Sicherheit belegt. Schlägt `nmcli` beim Anwenden von
Zugangsdaten mit „unknown property“ o. ä. fehl, den korrekten Key über
`man nm-settings-strongswan` bzw. `nmcli connection edit type vpn` →
`print vpn.data` ermitteln und die Konstante entsprechend anpassen.

## Privilegien für die Paketinstallation

Standardmäßig wird `sudo pacman -S --needed ...` verwendet (Terminal-Prompt,
kein Polkit-Agent nötig). Für einen grafischen Prompt stattdessen `pkexec`
verwenden: `PRIVILEGE = "pkexec"` in `vpn_manager/packages.py` setzen.

## Zugangsdaten-Speicherung

Zugangsdaten-Profile (Anbieter/Username/Passwort) liegen als Klartext-JSON in
`~/.config/vpn-manager/credentials.json` (Datei `chmod 600`, Verzeichnis
`chmod 700`) – bewusst einfach gehalten, kein System-Keyring.

## Tests

```bash
python3 -m unittest discover -s tests
```

Deckt die komplette Logik (nmcli-Kommandoaufbau, Credential-CRUD,
Ordner-Scan, Paket-Checks) ohne `nmcli`/`snack`/`pacman` ab. Die TUI-Screens
selbst (`vpn_manager/tui/`) benötigen `snack` und müssen auf dem Zielsystem
manuell durchgespielt werden (siehe Verifikationsschritte im Plan).
