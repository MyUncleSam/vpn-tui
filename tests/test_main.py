import contextlib
import io
import sys
import types
import unittest
from unittest import mock

from vpn_manager.__main__ import main


class MissingSnackTests(unittest.TestCase):
    """Ohne `snack` kann die TUI nicht starten – das Tool installiert nichts selbst."""

    def test_missing_snack_names_the_command_and_exits_nonzero(self):
        with mock.patch("importlib.util.find_spec", return_value=None), contextlib.redirect_stdout(
            io.StringIO()
        ) as out:
            code = main([])

        self.assertEqual(code, 1)
        self.assertIn("pacman -S newt", out.getvalue())

    def test_missing_snack_installs_nothing(self):
        with mock.patch("importlib.util.find_spec", return_value=None), mock.patch(
            "subprocess.run"
        ) as subprocess_run, contextlib.redirect_stdout(io.StringIO()):
            main([])

        subprocess_run.assert_not_called()


class StartupTests(unittest.TestCase):
    def test_starts_tui_and_passes_dry_run(self):
        # `vpn_manager.tui.app` importiert `snack`, das hier fehlt – daher ein
        # Fake-Modul in sys.modules injizieren statt echt zu importieren.
        fake_app = types.ModuleType("vpn_manager.tui.app")
        fake_app.run = mock.Mock()

        with mock.patch("importlib.util.find_spec", return_value=object()), mock.patch.dict(
            sys.modules, {"vpn_manager.tui.app": fake_app}
        ):
            code = main(["--dry-run"])

        fake_app.run.assert_called_once_with(dry_run=True)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
