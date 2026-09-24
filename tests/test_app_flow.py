"""Regressionstests für den Hauptmenü-Loop.

Hintergrund: snack leitet den Rückgabewert eines Buttons aus dessen Text ab und
schreibt ihn klein, wenn der Button als einfacher String übergeben wird
(`ButtonBar`: `value = blist.lower()`). Zusätzlich baut `ListboxChoiceWindow`
die Liste intern mit `returnExit=1` – wird ein Eintrag direkt mit Enter
bestätigt, ist der zurückgegebene Button-Wert `None`. Beides hatte das Menü
früher als „Beenden" gewertet, wodurch sich die TUI bei jeder Auswahl schloss.

`snack` ist hier nicht installiert, daher wird ein Fake-Modul injiziert; die
nachgebildeten Rückgabewerte stammen aus der echten snack-Quelle.
"""

import sys
import types
import unittest
from unittest import mock

SNACK_NAMES = (
    "SnackScreen",
    "ListboxChoiceWindow",
    "ButtonChoiceWindow",
    "EntryWindow",
    "ButtonBar",
    "CheckboxTree",
    "GridForm",
    "Label",
    "Listbox",
    "Entry",
)


class MainMenuFlowTests(unittest.TestCase):
    def setUp(self):
        fake_snack = types.ModuleType("snack")
        for name in SNACK_NAMES:
            setattr(fake_snack, name, mock.MagicMock(name=name))
        self.snack = fake_snack

        patcher = mock.patch.dict(sys.modules, {"snack": fake_snack})
        patcher.start()
        self.addCleanup(patcher.stop)

        self._purge_tui_modules()
        self.addCleanup(self._purge_tui_modules)

    @staticmethod
    def _purge_tui_modules():
        for name in [m for m in sys.modules if m.startswith("vpn_manager.tui")]:
            del sys.modules[name]

    def test_enter_on_entry_selects_instead_of_quitting(self):
        from vpn_manager.tui import app

        handler = mock.Mock()
        app.MENU_ITEMS = [("Eintrag A", handler), ("Eintrag B", mock.Mock())]
        # 1. Durchlauf: Enter auf Eintrag 0 -> Button-Wert None; 2. Durchlauf: "Beenden"
        self.snack.ListboxChoiceWindow.side_effect = [(None, 0), ("quit", 0)]

        app.run(dry_run=False)

        handler.assert_called_once()
        self.assertEqual(self.snack.ListboxChoiceWindow.call_count, 2)

    def test_select_button_runs_handler(self):
        from vpn_manager.tui import app

        handler = mock.Mock()
        app.MENU_ITEMS = [("Eintrag A", handler)]
        self.snack.ListboxChoiceWindow.side_effect = [("select", 0), ("quit", 0)]

        app.run(dry_run=False)

        handler.assert_called_once()

    def test_quit_button_exits_without_running_handler(self):
        from vpn_manager.tui import app

        handler = mock.Mock()
        app.MENU_ITEMS = [("Eintrag A", handler)]
        self.snack.ListboxChoiceWindow.side_effect = [("quit", 0)]

        app.run(dry_run=False)

        handler.assert_not_called()

    def test_buttons_are_passed_as_tuples_not_plain_strings(self):
        """Plain-String-Buttons würden von snack kleingeschrieben zurückgegeben."""
        from vpn_manager.tui import app

        app.MENU_ITEMS = [("Eintrag A", mock.Mock())]
        self.snack.ListboxChoiceWindow.side_effect = [("quit", 0)]

        app.run(dry_run=False)

        buttons = self.snack.ListboxChoiceWindow.call_args.kwargs["buttons"]
        for button in buttons:
            self.assertIsInstance(button, tuple, f"Button {button!r} muss (Text, Wert) sein")


if __name__ == "__main__":
    unittest.main()
