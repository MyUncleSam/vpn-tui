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

    def test_no_message_when_already_up_to_date(self):
        runner = self._runner(heads=["abc123", "abc123"])
        self.assertIsNone(updater.update(self.repo, runner=runner))

    def test_reports_when_a_new_version_was_pulled(self):
        runner = self._runner(heads=["abc123", "def456"])
        self.assertIn("Neue Version", updater.update(self.repo, runner=runner))

    def test_timeout_is_reported_and_does_not_raise(self):
        runner = self._runner(
            heads=["abc123"], pull=subprocess.TimeoutExpired(cmd="git", timeout=5)
        )
        message = updater.update(self.repo, timeout=5, runner=runner)
        self.assertIn("5s", message)
        self.assertIn("lokale Version", message)

    def test_failed_pull_is_reported_and_does_not_raise(self):
        runner = self._runner(heads=["abc123"], pull=FakeCompleted(returncode=1, stderr="offline"))
        self.assertIn("lokale Version", updater.update(self.repo, runner=runner))

    def test_missing_git_binary_is_silent(self):
        def runner(args, **kwargs):
            raise FileNotFoundError()

        self.assertIsNone(updater.update(self.repo, runner=runner))

    def test_without_git_checkout_nothing_happens(self):
        with tempfile.TemporaryDirectory() as plain:
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                return FakeCompleted()

            self.assertIsNone(updater.update(Path(plain), runner=runner))
            self.assertEqual(calls, [])

    def test_git_is_never_allowed_to_prompt_for_credentials(self):
        """Ein interaktiver Prompt würde am Timeout vorbei den Start blockieren."""
        calls = []
        runner = self._runner(heads=["abc123", "abc123"], calls=calls)
        updater.update(self.repo, runner=runner)

        for args, kwargs in calls:
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertIn("BatchMode=yes", kwargs["env"]["GIT_SSH_COMMAND"])

    def test_pull_runs_with_timeout_and_ff_only(self):
        calls = []
        runner = self._runner(heads=["abc123", "abc123"], calls=calls)
        updater.update(self.repo, timeout=3, runner=runner)

        pull_calls = [(a, k) for a, k in calls if "pull" in a]
        self.assertEqual(len(pull_calls), 1)
        args, kwargs = pull_calls[0]
        self.assertIn("--ff-only", args)
        self.assertEqual(kwargs["timeout"], 3)


if __name__ == "__main__":
    unittest.main()
