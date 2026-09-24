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

    def test_build_uuid_list_command(self):
        self.assertEqual(
            nmcli.build_uuid_list_command(), ["-t", "-f", "UUID,NAME", "connection", "show"]
        )

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
    def test_parse_uuid_list(self):
        output = "uuid-1:MyWireguard\nuuid-2:MyOpenVPN\n"
        self.assertEqual(
            nmcli.parse_uuid_list(output), {"uuid-1": "MyWireguard", "uuid-2": "MyOpenVPN"}
        )

    def test_parse_uuid_list_escaped_colon(self):
        self.assertEqual(
            nmcli.parse_uuid_list("uuid-1:10.0.0.1\\:443 VPN\n"), {"uuid-1": "10.0.0.1:443 VPN"}
        )

    def test_new_connections_returns_only_added(self):
        before = {"uuid-1": "Alt"}
        after = {"uuid-1": "Alt", "uuid-2": "Neu"}
        self.assertEqual(nmcli.new_connections(before, after), [("uuid-2", "Neu")])

    def test_new_connections_empty_when_nothing_added(self):
        same = {"uuid-1": "Alt"}
        self.assertEqual(nmcli.new_connections(same, same), [])

    def test_new_connections_detects_duplicate_name_as_separate_connection(self):
        """Gleicher Name, andere UUID: genau der Fall, den Namensvergleich nicht erkennt."""
        before = {"uuid-1": "server-nl"}
        after = {"uuid-1": "server-nl", "uuid-2": "server-nl"}
        self.assertEqual(nmcli.new_connections(before, after), [("uuid-2", "server-nl")])

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

    def test_filter_excludes_wireguard_for_password_types(self):
        parsed = [("MyWireguard", "wireguard"), ("MyOpenVPN", "vpn"), ("Home Wifi", "802-11-wireless")]
        self.assertEqual(
            nmcli.filter_vpn_connections(parsed, types=nmcli.PASSWORD_VPN_TYPES), ["MyOpenVPN"]
        )

    def test_parse_service_type_terse(self):
        self.assertEqual(
            nmcli.parse_service_type("org.freedesktop.NetworkManager.openvpn\n"), "openvpn"
        )

    def test_parse_service_type_verbose(self):
        output = "vpn.service-type:        org.freedesktop.NetworkManager.openconnect\n"
        self.assertEqual(nmcli.parse_service_type(output), "openconnect")

    def test_parse_service_type_empty(self):
        self.assertEqual(nmcli.parse_service_type("\n"), "")

    def test_build_autoconnect_list_command(self):
        self.assertEqual(
            nmcli.build_autoconnect_list_command(),
            ["-t", "-f", "NAME,TYPE,AUTOCONNECT", "connection", "show"],
        )

    def test_parse_autoconnect_list(self):
        output = "MyWireguard:wireguard:yes\nMyOpenVPN:vpn:no\nHome Wifi:802-11-wireless:yes\n"
        self.assertEqual(
            nmcli.parse_autoconnect_list(output),
            [
                ("MyWireguard", "wireguard", True),
                ("MyOpenVPN", "vpn", False),
                ("Home Wifi", "802-11-wireless", True),
            ],
        )

    def test_parse_autoconnect_list_escaped_colon(self):
        output = "10.0.0.1\\:443 VPN:vpn:yes\n"
        self.assertEqual(nmcli.parse_autoconnect_list(output), [("10.0.0.1:443 VPN", "vpn", True)])

    def test_build_service_type_command(self):
        self.assertEqual(
            nmcli.build_service_type_command("MyConn"),
            ["-t", "-f", "vpn.service-type", "connection", "show", "MyConn"],
        )


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

    def test_forces_stable_locale_so_output_stays_parsable(self):
        captured = {}

        def runner(argv, **kwargs):
            captured.update(kwargs)
            return FakeCompleted(returncode=0, stdout="", stderr="")

        nmcli.run_nmcli(["connection", "show"], runner=runner)

        self.assertEqual(captured["env"]["LC_ALL"], "C")
        self.assertNotIn("LANGUAGE", captured["env"])

    def test_missing_nmcli_binary(self):
        def runner(argv, **kwargs):
            raise FileNotFoundError()

        with self.assertRaises(nmcli.NmcliError):
            nmcli.run_nmcli(["connection", "show"], runner=runner)


if __name__ == "__main__":
    unittest.main()
