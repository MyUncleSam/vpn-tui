import unittest

from vpn_manager import packages


class FakeCompleted:
    def __init__(self, returncode):
        self.returncode = returncode


def make_runner(installed_pkgs):
    def runner(argv, **kwargs):
        pkg = argv[-1]
        return FakeCompleted(0 if pkg in installed_pkgs else 1)

    return runner


class PackagesTests(unittest.TestCase):
    def test_check_installed_true(self):
        runner = make_runner({"wireguard-tools"})
        self.assertTrue(packages.check_installed("wireguard-tools", runner=runner))

    def test_check_installed_false(self):
        runner = make_runner({"wireguard-tools"})
        self.assertFalse(packages.check_installed("networkmanager-strongswan", runner=runner))

    def test_check_installed_pacman_missing(self):
        def runner(argv, **kwargs):
            raise FileNotFoundError()

        self.assertFalse(packages.check_installed("wireguard-tools", runner=runner))

    def test_check_all(self):
        runner = make_runner({"wireguard-tools"})
        result = packages.check_all(["wireguard-tools", "networkmanager-strongswan"], runner=runner)
        self.assertEqual(result, {"wireguard-tools": True, "networkmanager-strongswan": False})

    def test_build_install_command_sudo(self):
        self.assertEqual(
            packages.build_install_command(["newt"], privilege="sudo"),
            ["sudo", "pacman", "-S", "--needed", "newt"],
        )

    def test_build_install_command_pkexec(self):
        self.assertEqual(
            packages.build_install_command(["newt"], privilege="pkexec"),
            ["pkexec", "pacman", "-S", "--needed", "newt"],
        )

    def test_build_install_command_no_privilege(self):
        self.assertEqual(
            packages.build_install_command(["newt"], privilege=""),
            ["pacman", "-S", "--needed", "newt"],
        )


if __name__ == "__main__":
    unittest.main()
