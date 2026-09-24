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
    @staticmethod
    def _fake_app():
        # `vpn_manager.tui.app` importiert `snack`, das hier fehlt – daher ein
        # Fake-Modul in sys.modules injizieren statt echt zu importieren.
        fake_app = types.ModuleType("vpn_manager.tui.app")
        fake_app.run = mock.Mock()
        return fake_app

    def test_starts_tui_and_passes_dry_run(self):
        fake_app = self._fake_app()

        with mock.patch("importlib.util.find_spec", return_value=object()), mock.patch.dict(
            sys.modules, {"vpn_manager.tui.app": fake_app}
        ), contextlib.redirect_stdout(io.StringIO()):
            code = main(["--dry-run"])

        fake_app.run.assert_called_once_with(dry_run=True, notice=None)
        self.assertEqual(code, 0)

    def test_update_runs_on_start_and_its_notice_reaches_the_tui(self):
        fake_app = self._fake_app()

        with mock.patch("importlib.util.find_spec", return_value=object()), mock.patch.dict(
            sys.modules, {"vpn_manager.tui.app": fake_app}
        ), mock.patch("vpn_manager.updater.update", return_value="Neue Version eingespielt.") as up:
            main([])

        up.assert_called_once_with()
        fake_app.run.assert_called_once_with(dry_run=False, notice="Neue Version eingespielt.")

    def _run_skipping_update(self, argv):
        fake_app = self._fake_app()
        out = io.StringIO()

        with mock.patch("importlib.util.find_spec", return_value=object()), mock.patch.dict(
            sys.modules, {"vpn_manager.tui.app": fake_app}
        ), mock.patch("vpn_manager.updater.update") as up, contextlib.redirect_stdout(out):
            main(argv)

        return up, out.getvalue()

    def test_no_update_flag_skips_the_pull_and_says_so(self):
        up, output = self._run_skipping_update(["--no-update"])

        up.assert_not_called()
        self.assertIn("--no-update", output)

    def test_dry_run_never_touches_the_checkout_and_says_so(self):
        up, output = self._run_skipping_update(["--dry-run"])

        up.assert_not_called()
        self.assertIn("--dry-run", output)


if __name__ == "__main__":
    unittest.main()
