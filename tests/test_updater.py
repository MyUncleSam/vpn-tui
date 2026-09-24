import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from vpn_manager import updater


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        (self.repo / ".git").mkdir()

    def _runner(self, heads, pull=None, calls=None):
        """heads: nacheinander gelieferte rev-parse-Ausgaben."""
        remaining = list(heads)

        def runner(args, **kwargs):
            if calls is not None:
                calls.append((args, kwargs))
            if "rev-parse" in args:
                return FakeCompleted(stdout=remaining.pop(0))
            if pull is not None:
                if isinstance(pull, Exception):
                    raise pull
                return pull
            return FakeCompleted()

        return runner

    def _run(self, *args, **kwargs):
        """Führt update() aus und liefert (Rückgabe, Terminalausgabe)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            message = updater.update(*args, **kwargs)
        return message, out.getvalue()

    def test_no_message_when_already_up_to_date(self):
        runner = self._runner(heads=["abc123", "abc123"])
        message, output = self._run(self.repo, runner=runner)
        self.assertIsNone(message)
        self.assertIn("Bereits aktuell", output)

    def test_reports_when_a_new_version_was_pulled(self):
        runner = self._runner(heads=["abc1234567", "def4567890"])
        message, output = self._run(self.repo, runner=runner)
        self.assertIn("Neue Version", message)
        self.assertIn("abc1234", message)
        self.assertIn("def4567", message)
        self.assertIn("Neue Version", output)

    def test_announces_the_check_and_the_command(self):
        """Der Nutzer soll sehen, dass etwas läuft – und was."""
        runner = self._runner(heads=["abc123", "abc123"])
        _, output = self._run(self.repo, runner=runner)
        self.assertIn("Suche nach Updates", output)
        self.assertIn("git", output)
        self.assertIn("pull", output)
        self.assertIn("--ff-only", output)

    def test_pull_output_is_not_captured_so_the_user_sees_git(self):
        calls = []
        runner = self._runner(heads=["abc123", "abc123"], calls=calls)
        self._run(self.repo, runner=runner)

        pull_kwargs = [k for a, k in calls if "pull" in a][0]
        self.assertNotIn("capture_output", pull_kwargs)

    def test_timeout_is_reported_and_does_not_raise(self):
        runner = self._runner(
            heads=["abc123"], pull=subprocess.TimeoutExpired(cmd="git", timeout=5)
        )
        message, output = self._run(self.repo, timeout=5, runner=runner)
        self.assertIn("5s", message)
        self.assertIn("lokale Version", message)
        self.assertIn("lokale Version", output)

    def test_failed_pull_is_reported_and_does_not_raise(self):
        runner = self._runner(heads=["abc123"], pull=FakeCompleted(returncode=1, stderr="offline"))
        message, _ = self._run(self.repo, runner=runner)
        self.assertIn("lokale Version", message)

    def test_missing_git_binary_is_explained(self):
        def runner(args, **kwargs):
            raise FileNotFoundError()

        message, output = self._run(self.repo, runner=runner)
        self.assertIsNone(message)
        self.assertIn("git ist nicht installiert", output)

    def test_without_git_checkout_nothing_runs(self):
        with tempfile.TemporaryDirectory() as plain:
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                return FakeCompleted()

            message, output = self._run(Path(plain), runner=runner)
            self.assertIsNone(message)
            self.assertEqual(calls, [])
            self.assertIn("Kein Git-Checkout", output)

    def test_git_is_never_allowed_to_prompt_for_credentials(self):
        """Ein interaktiver Prompt würde am Timeout vorbei den Start blockieren."""
        calls = []
        runner = self._runner(heads=["abc123", "abc123"], calls=calls)
        self._run(self.repo, runner=runner)

        for args, kwargs in calls:
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertIn("BatchMode=yes", kwargs["env"]["GIT_SSH_COMMAND"])

    def test_pull_runs_with_timeout_and_ff_only(self):
        calls = []
        runner = self._runner(heads=["abc123", "abc123"], calls=calls)
        self._run(self.repo, timeout=3, runner=runner)

        pull_calls = [(a, k) for a, k in calls if "pull" in a]
        self.assertEqual(len(pull_calls), 1)
        args, kwargs = pull_calls[0]
        self.assertIn("--ff-only", args)
        self.assertEqual(kwargs["timeout"], 3)


if __name__ == "__main__":
    unittest.main()
