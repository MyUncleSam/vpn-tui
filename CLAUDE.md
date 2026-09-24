# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TUI zum Massen-Import und Verwalten von OpenVPN-/WireGuard-Verbindungen über
`nmcli` (CachyOS/Arch, KDE Plasma). Code, Kommentare und UI-Texte sind deutsch.

## Befehle

```bash
python3 -m unittest discover -s tests          # gesamte Suite
python3 -m unittest tests.test_nmcli           # eine Datei
python3 -m unittest tests.test_screens.EscapeTests.test_q_cancels_like_esc   # ein Test
python3 -m py_compile main.py vpn_manager/*.py vpn_manager/tui/*.py tests/*.py

python3 main.py --dry-run                      # Lauf ohne Änderungen am System
bash -n install.sh                             # Installer-Syntax
```

Kein Linter, kein Build-Schritt. Tests sind stdlib-`unittest` und laufen ohne
`nmcli`, `newt`/`snack` oder `pacman` – die Entwicklungsumgebung hat diese
in der Regel nicht.

## Architektur

Zwei Schichten, streng getrennt:

- `vpn_manager/*.py` – Logik. **Darf `snack` niemals importieren.**
- `vpn_manager/tui/*.py` – Oberfläche. Nur hier ist `snack` erlaubt, und auch
  dort nur in `app.py`, `common.py`, `credentials_screen.py`; die übrigen
  Screens gehen über die Dialoge in `common.py`.

Diese Regel ist der Grund, warum die gesamte Logik ohne installiertes `newt`
testbar ist. Beim Hinzufügen eines Moduls prüfen:
`grep -rn "^from snack\|^import snack" vpn_manager/`

`nmcli.py` ist zweigeteilt: reine `build_*`/`parse_*`-Funktionen ohne I/O plus
`run_nmcli()` als einzige ausführende Stelle. Letztere nimmt einen
injizierbaren `runner` (Default `subprocess.run`) – Tests übergeben einen Stub
statt echtem nmcli. Ebenso `updater.update()`.

Screens haben einheitlich `run(screen, dry_run) -> None` und werden über
`app.MENU_ITEMS` eingehängt.

## Verbindliche Invarianten

**Autoconnect.** Jede importierte Verbindung bekommt
`connection.autoconnect no` über `nmcli.ensure_autoconnect_off()`. Schlägt das
fehl, muss der Screen das *explizit* melden – eine stillschweigend
autoconnect-fähige Verbindung ist der schlimmste Fehlerfall des Tools.

**Dry-Run.** `dry_run=True` gilt nur für *verändernde* Aufrufe (import, add,
modify, delete). Lesende Aufrufe (`connection show`) laufen immer echt, sonst
hätten die Screens nichts anzuzeigen. Die Unterscheidung trifft der aufrufende
Screen, nicht `run_nmcli`. Auch das Selbst-Update unterbleibt im Dry-Run.

**Startausgabe.** `updater.update()` schreibt Ankündigung, git-Kommando und
Ergebnis nach stdout, und der Pull läuft bewusst *ohne* `capture_output`, damit
git direkt ins Terminal schreibt. Das ist der einzige Moment, in dem der Nutzer
etwas sieht – danach übernimmt die TUI den Bildschirm; das Ergebnis wandert
deshalb zusätzlich als `notice` ins Hauptmenü.

**Keine Softwareinstallation.** Das Tool installiert nichts – weder Pakete noch
sich selbst fehlende Abhängigkeiten. Fehlendes `newt` führt nur zu einem
Hinweis mit dem passenden `pacman`-Befehl.

## nmcli-Ausgaben: nie Fließtext auswerten

nmcli übersetzt seine Ausgaben. Nicht übersetzt sind Exit-Codes und Bezeichner
(`NAME`, `UUID`, `TYPE`) – **übersetzt sind auch `yes`/`no`**, selbst in der
Terse-Ausgabe `-t` (deutsch `ja`/`nein`).

- Alle Aufrufe laufen über `nmcli.stable_output_env()` mit `LC_ALL=C`.
- Erfolgsmeldungen werden nicht geparst. Die neu importierte Verbindung wird
  über die Differenz der UUID-Liste vor/nach dem Import bestimmt
  (`nmcli.new_connections`) und danach **über die UUID** adressiert – eindeutig
  auch bei doppelten Verbindungsnamen.

Ein früherer Bug kam genau daher: Der Regex auf `Connection '...' successfully
added` traf auf deutschem System nie, wodurch Zugangsdaten *und* das
Abschalten von Autoconnect stillschweigend übersprungen wurden.

## snack-Fallstricke

Die Bibliothek verhält sich an drei Stellen unerwartet. Alle drei sind durch
Tests abgesichert, die bei Verstoß fehlschlagen:

1. **Buttons immer als `(Text, Wert)`-Tupel.** Bei einfachen Strings leitet
   `ButtonBar` den Rückgabewert aus dem Text ab und schreibt ihn klein – ein
   Vergleich gegen `"Auswählen"` trifft dann nie.
2. **Dialoge selbst bauen.** `ButtonChoiceWindow`/`ListboxChoiceWindow`/
   `EntryWindow` reagieren nicht auf ESC; newt liefert eine Taste nur, wenn sie
   per `addHotKey` registriert ist, und dafür bieten sie keinen Parameter.
   Deshalb alle Dialoge über `common.run_form()` + `common.is_cancel()`.
3. **`q` nur ohne Texteingabe.** `run_form(form, quit_key=False)` in jedem
   Formular mit `Entry`, sonst bricht die Eingabe eines „q" den Dialog ab.
   Betrifft `common.prompt_form` und `credentials_screen._edit_form`.

Listen mit `returnExit=1` beenden das Formular direkt; `buttonPressed()` gibt
dann `None` zurück – das ist eine Auswahl, kein Abbruch (siehe `common.choose`).

## Tests

`tests/test_screens.py` und `tests/test_app_flow.py` injizieren ein
Fake-`snack`-Modul in `sys.modules` und leeren `vpn_manager.tui*` aus dem
Modul-Cache, damit die Screens ohne `newt` importierbar sind. Neue
snack-Widgets müssen in `SNACK_NAMES` ergänzt werden.

Beim Ändern von Verhalten, das auf einer dieser Invarianten beruht: die
zugehörige Stelle gezielt kaputtmachen und prüfen, dass ein Test fehlschlägt.
Mehrere dieser Regeln stammen aus realen Fehlern, die vorher unbemerkt blieben.

## Hinweise zur Umgebung

Installiert wird ins Benutzerverzeichnis (`~/.local/share/vpn-tui`, Befehl
`~/.local/bin/vpn-tui`) – bewusst ohne root, damit das Selbst-Update beim Start
(`updater.py`, `git pull --ff-only` mit 5s-Timeout) ohne Sonderrechte pullen
kann. Zugangsdaten liegen als Klartext-JSON in
`~/.config/vpn-manager/credentials.json` (Datei `chmod 600`).
