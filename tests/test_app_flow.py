"""Regressionstests für den Hauptmenü-Loop.

Hintergrund: snack leitet den Rückgabewert eines Buttons aus dessen Text ab und
schreibt ihn klein (`ButtonBar`: `value = blist.lower()`), wenn der Button als
einfacher String übergeben wird. Zusätzlich beenden Listen mit `returnExit=1`
das Formular direkt – `buttonPressed()` liefert dann `None`. Beides hatte das
Menü früher als „Beenden" gewertet, wodurch sich die TUI bei jeder Auswahl
schloss. Die Auswahl läuft deshalb über `common.choose`, das beides kapselt.

`snack` ist hier nicht installiert, daher wird ein Fake-Modul injiziert.
"""

import sys
import types
import unittest
from unittest import mock

SNACK_NAMES = (
    "SnackScreen",
    "ButtonBar",
    "CheckboxTree",
    "Entry",
    "Grid",
    "GridForm",
    "Label",
    "Listbox",
    "TextboxReflowed",
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

    def test_selecting_an_entry_runs_it_and_keeps_the_menu_open(self):
        from vpn_manager.tui import app, common

        handler = mock.Mock()
        app.MENU_ITEMS = [("Eintrag A", handler), ("Eintrag B", mock.Mock())]

        with mock.patch.object(common, "choose", side_effect=[0, None]) as choose:
            app.run(dry_run=False)

        handler.assert_called_once()
        self.assertEqual(choose.call_count, 2)

    def test_cancelling_the_menu_exits(self):
        from vpn_manager.tui import app, common

        handler = mock.Mock()
        app.MENU_ITEMS = [("Eintrag A", handler)]

        with mock.patch.object(common, "choose", return_value=None):
            app.run(dry_run=False)

        handler.assert_not_called()
        self.snack.SnackScreen.return_value.finish.assert_called_once()

    def test_esc_hint_and_quit_button_are_offered(self):
        from vpn_manager.tui import app, common

        app.MENU_ITEMS = [("Eintrag A", mock.Mock())]

        with mock.patch.object(common, "choose", return_value=None) as choose:
            app.run(dry_run=False)

        text = choose.call_args.args[2]
        self.assertIn("ESC", text)
        # Plain-String-Buttons würde snack kleingeschrieben zurückgeben.
        self.assertIsInstance(choose.call_args.kwargs["cancel"], tuple)

    def test_notice_from_self_update_is_shown_in_the_menu(self):
        from vpn_manager.tui import app, common

        app.MENU_ITEMS = [("Eintrag A", mock.Mock())]

        with mock.patch.object(common, "choose", return_value=None) as choose:
            app.run(dry_run=False, notice="Neue Version eingespielt.")

        self.assertIn("Neue Version eingespielt.", choose.call_args.args[2])

    def test_ctrl_c_exits_cleanly_and_restores_the_terminal(self):
        """Notausstieg, falls Ctrl+C als SIGINT durchkommt – kein Traceback."""
        from vpn_manager.tui import app, common

        app.MENU_ITEMS = [("Eintrag A", mock.Mock())]

        with mock.patch.object(common, "choose", side_effect=KeyboardInterrupt):
            app.run(dry_run=False)

        self.snack.SnackScreen.return_value.finish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
