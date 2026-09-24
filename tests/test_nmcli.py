import unittest

from vpn_manager import nmcli


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class BuilderTests(unittest.TestCase):
    def test_build_import_command(self):
        self.assertEqual(
            nmcli.build_import_command("wireguard", "/tmp/nl.conf"),
            ["connection", "import", "type", "wireguard", "file", "/tmp/nl.conf"],
        )

    def test_build_autoconnect_off_command(self):
        self.assertEqual(
            nmcli.build_autoconnect_off_command("MyConn"),
            ["connection", "modify", "MyConn", "connection.autoconnect", "no"],
        )

    def test_build_delete_command(self):
        self.assertEqual(nmcli.build_delete_command("MyConn"), ["connection", "delete", "MyConn"])

    def test_build_list_command(self):
        self.assertEqual(nmcli.build_list_command(), ["-t", "-f", "NAME,TYPE", "connection", "show"])

    def test_build_vpn_data_string(self):
        self.assertEqual(
            nmcli.build_vpn_data_string({"address": "1.2.3.4", "method": "eap"}),
            "address=1.2.3.4,method=eap",
        )

    def test_build_openvpn_credentials_commands(self):
        data_cmd, secret_cmd = nmcli.build_openvpn_credentials_commands("MyConn", "alice", "s3cret")
        self.assertEqual(
            data_cmd,
            ["connection", "modify", "MyConn", "+vpn.data", "connection-type=password,username=alice"],
        )
        self.assertEqual(secret_cmd, ["connection", "modify", "MyConn", "+vpn.secrets", "password=s3cret"])


class ParserTests(unittest.TestCase):
    def test_parse_import_output_success(self):
        stdout = "Connection 'MyConn' (uuid-1234) successfully added.\n"
        self.assertEqual(nmcli.parse_import_output(stdout), "MyConn")

    def test_parse_import_output_unexpected_format(self):
        self.assertIsNone(nmcli.parse_import_output("some unrelated output"))

    def test_parse_connection_list(self):
        output = "MyWireguard:wireguard\nMyOpenVPN:vpn\nHome Wifi:802-11-wireless\n"
        self.assertEqual(
            nmcli.parse_connection_list(output),
            [("MyWireguard", "wireguard"), ("MyOpenVPN", "vpn"), ("Home Wifi", "802-11-wireless")],
        )

    def test_parse_connection_list_escaped_colon(self):
        output = "10.0.0.1\\:443 VPN:vpn\n"
        self.assertEqual(nmcli.parse_connection_list(output), [("10.0.0.1:443 VPN", "vpn")])

    def test_filter_vpn_connections(self):
        parsed = [("MyWireguard", "wireguard"), ("MyOpenVPN", "vpn"), ("Home Wifi", "802-11-wireless")]
        self.assertEqual(nmcli.filter_vpn_connections(parsed), ["MyWireguard", "MyOpenVPN"])


class RunNmcliTests(unittest.TestCase):
    def test_dry_run_never_calls_runner(self):
        calls = []

        def runner(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeCompleted()

        result = nmcli.run_nmcli(["connection", "show"], dry_run=True, runner=runner)
        self.assertTrue(result.dry_run)
        self.assertEqual(calls, [])

    def test_success(self):
        def runner(argv, **kwargs):
            return FakeCompleted(returncode=0, stdout="ok", stderr="")

        result = nmcli.run_nmcli(["connection", "show"], runner=runner)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "ok")

    def test_nonzero_exit_raises(self):
        def runner(argv, **kwargs):
            return FakeCompleted(returncode=1, stdout="", stderr="boom")

        with self.assertRaises(nmcli.NmcliError):
            nmcli.run_nmcli(["connection", "show"], runner=runner)

    def test_nonzero_exit_no_check_does_not_raise(self):
        def runner(argv, **kwargs):
            return FakeCompleted(returncode=1, stdout="", stderr="boom")

        result = nmcli.run_nmcli(["connection", "show"], check=False, runner=runner)
        self.assertEqual(result.returncode, 1)

    def test_missing_nmcli_binary(self):
        def runner(argv, **kwargs):
            raise FileNotFoundError()

        with self.assertRaises(nmcli.NmcliError):
            nmcli.run_nmcli(["connection", "show"], runner=runner)


if __name__ == "__main__":
    unittest.main()
