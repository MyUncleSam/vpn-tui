"""Smoke-Tests, die jeden TUI-Screen einmal durchlaufen.

`snack` ist hier nicht installiert (und die Screens lassen sich ohnehin nicht
interaktiv testen), daher wird ein Fake-`snack`-Modul injiziert und die
Dialog-Helfer aus `common` werden gemockt. Getestet wird damit der Ablauf der
Screens: welche nmcli-Kommandos in welcher Reihenfolge entstehen und wie auf
Fehler reagiert wird.
"""

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from vpn_manager import nmcli

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


class ScreenTestCase(unittest.TestCase):
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

        self.screen = mock.MagicMock(name="SnackScreen")

    @staticmethod
    def _purge_tui_modules():
        for name in [m for m in sys.modules if m.startswith("vpn_manager.tui")]:
            del sys.modules[name]

    @staticmethod
    def ok_result(stdout=""):
        return nmcli.CommandResult(["nmcli"], 0, stdout, "")


class ImportScreenTests(ScreenTestCase):
    def _folder_with(self, *filenames):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for filename in filenames:
            (Path(tmp.name) / filename).write_text("x")
        return tmp.name

    def _fake_nmcli(self, stdout="", created=None):
        """Simuliert nmcli: die Verbindungsliste wächst mit jedem erfolgreichen Import.

        `stdout` ist die (ggf. übersetzte) Meldung des Imports – der Screen darf
        sie nicht auswerten, die neue Verbindung wird über die UUID-Differenz
        bestimmt.
        """
        state: dict[str, str] = {}
        pending = list(created or [])

        def run(args, dry_run=False, **kwargs):
            if "UUID,NAME" in args:
                return self.ok_result("".join(f"{u}:{n}\n" for u, n in state.items()))
            if args[:2] == ["connection", "import"]:
                if pending:
                    name = pending.pop(0)
                    state[f"uuid-{name}"] = name
                return self.ok_result(stdout)
            return self.ok_result()

        return run

    def _profiles(self):
        from vpn_manager import credentials as creds

        return {"Nord": creds.CredentialProfile("NordVPN", "alice", "s3cret")}

    def test_imports_each_file_and_disables_autoconnect_by_uuid(self):
        from vpn_manager.tui import common, import_screen

        folder = self._folder_with("a.conf", "b.ovpn")

        with mock.patch.object(common, "prompt_text", return_value=folder), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "pick_profile", return_value=None), mock.patch.object(
            common, "info"
        ) as info, mock.patch.object(
            import_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli(created=["a", "b"])
        ) as run_nmcli, mock.patch.object(
            import_screen.nmcli, "ensure_autoconnect_off"
        ) as autoconnect_off:
            import_screen.run(self.screen, dry_run=False)

        imported = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertIn(
            ["connection", "import", "type", "wireguard", "file", f"{folder}/a.conf"], imported
        )
        self.assertIn(
            ["connection", "import", "type", "openvpn", "file", f"{folder}/b.ovpn"], imported
        )
        disabled = [call.args[0] for call in autoconnect_off.call_args_list]
        self.assertEqual(disabled, ["uuid-a", "uuid-b"])
        self.assertNotIn("FEHLER", info.call_args.args[2])

    def test_credentials_applied_by_uuid_whatever_the_message_language(self):
        """Regression: früher wurde der Name aus der übersetzten Meldung gelesen."""
        from vpn_manager.tui import common, import_screen

        folder = self._folder_with("server-nl.ovpn")
        german = "Verbindung »server-nl« (uuid-server-nl) erfolgreich hinzugefügt.\n"

        with mock.patch.object(common, "prompt_text", return_value=folder), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(
            import_screen.creds, "load_profiles", return_value=self._profiles()
        ), mock.patch.object(common, "pick_profile", return_value="Nord"), mock.patch.object(
            common, "info"
        ), mock.patch.object(
            import_screen.nmcli,
            "run_nmcli",
            side_effect=self._fake_nmcli(stdout=german, created=["server-nl"]),
        ) as run_nmcli:
            import_screen.run(self.screen, dry_run=False)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertIn(
            [
                "connection",
                "modify",
                "uuid-server-nl",
                "+vpn.data",
                "connection-type=password,username=alice",
            ],
            commands,
        )
        self.assertIn(
            ["connection", "modify", "uuid-server-nl", "+vpn.secrets", "password=s3cret"], commands
        )

    def test_autoconnect_failure_is_reported_explicitly(self):
        from vpn_manager.tui import common, import_screen

        folder = self._folder_with("a.conf")

        with mock.patch.object(common, "prompt_text", return_value=folder), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "pick_profile", return_value=None), mock.patch.object(
            common, "info"
        ) as info, mock.patch.object(
            import_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli(created=["a"])
        ), mock.patch.object(
            import_screen.nmcli,
            "ensure_autoconnect_off",
            side_effect=nmcli.NmcliError(["nmcli"], 1, "boom"),
        ):
            import_screen.run(self.screen, dry_run=False)

        report = info.call_args.args[2]
        self.assertIn("autoconnect", report)
        self.assertIn("NICHT", report)

    def test_import_without_new_connection_is_reported(self):
        from vpn_manager.tui import common, import_screen

        folder = self._folder_with("a.ovpn")

        with mock.patch.object(common, "prompt_text", return_value=folder), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "pick_profile", return_value=None), mock.patch.object(
            common, "info"
        ) as info, mock.patch.object(
            import_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli(created=[])
        ), mock.patch.object(import_screen.nmcli, "ensure_autoconnect_off") as autoconnect_off:
            import_screen.run(self.screen, dry_run=False)

        autoconnect_off.assert_not_called()
        self.assertIn("nicht gefunden", info.call_args.args[2])

    def test_dry_run_uses_filename_and_only_previews(self):
        from vpn_manager.tui import common, import_screen

        folder = self._folder_with("a.ovpn")

        with mock.patch.object(common, "prompt_text", return_value=folder), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "pick_profile", return_value=None), mock.patch.object(
            common, "info"
        ), mock.patch.object(
            import_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli(created=[])
        ) as run_nmcli:
            import_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertIn(["connection", "modify", "a", "connection.autoconnect", "no"], commands)

    def test_cancelled_folder_prompt_does_nothing(self):
        from vpn_manager.tui import common, import_screen

        with mock.patch.object(common, "prompt_text", return_value=None), mock.patch.object(
            import_screen.nmcli, "run_nmcli"
        ) as run_nmcli:
            import_screen.run(self.screen, dry_run=True)

        run_nmcli.assert_not_called()


class DeleteScreenTests(ScreenTestCase):
    def test_deletes_selected_connections(self):
        from vpn_manager.tui import common, delete_screen

        listing = self.ok_result("MyWireguard:wireguard\nMyOpenVPN:vpn\nHome Wifi:802-11-wireless\n")
        self.snack.ButtonBar.return_value.buttonPressed.return_value = "delete"
        self.snack.CheckboxTree.return_value.getSelection.return_value = ["MyWireguard", "MyOpenVPN"]

        with mock.patch.object(common, "confirm", return_value=True), mock.patch.object(
            common, "info"
        ), mock.patch.object(delete_screen.nmcli, "run_nmcli", return_value=listing) as run_nmcli:
            delete_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertIn(["connection", "delete", "MyWireguard"], commands)
        self.assertIn(["connection", "delete", "MyOpenVPN"], commands)

    def test_only_vpn_connections_are_offered(self):
        from vpn_manager.tui import common, delete_screen

        listing = self.ok_result("MyWireguard:wireguard\nHome Wifi:802-11-wireless\n")
        self.snack.ButtonBar.return_value.buttonPressed.return_value = "back"

        with mock.patch.object(common, "info"), mock.patch.object(
            delete_screen.nmcli, "run_nmcli", return_value=listing
        ):
            delete_screen.run(self.screen, dry_run=True)

        offered = [call.args[0] for call in self.snack.CheckboxTree.return_value.append.call_args_list]
        self.assertEqual(offered, ["MyWireguard"])

    def test_cancel_deletes_nothing(self):
        from vpn_manager.tui import common, delete_screen

        listing = self.ok_result("MyWireguard:wireguard\n")
        self.snack.ButtonBar.return_value.buttonPressed.return_value = "back"

        with mock.patch.object(common, "info"), mock.patch.object(
            delete_screen.nmcli, "run_nmcli", return_value=listing
        ) as run_nmcli:
            delete_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertNotIn(["connection", "delete", "MyWireguard"], commands)


class ApplyCredentialsScreenTests(ScreenTestCase):
    LISTING = "MyOpenVPN:vpn\nMyGateway:vpn\nMyWireguard:wireguard\nHome Wifi:802-11-wireless\n"

    def _fake_nmcli(self, service_type="org.freedesktop.NetworkManager.openvpn"):
        """Beantwortet die Listen- und vpn.service-type-Abfragen, alles andere mit Erfolg."""

        def run(args, **kwargs):
            if "NAME,TYPE" in args:
                return self.ok_result(self.LISTING)
            if "vpn.service-type" in args:
                return self.ok_result(service_type)
            return self.ok_result()

        return run

    def _profile(self):
        from vpn_manager import credentials as creds

        return {"Nord": creds.CredentialProfile("NordVPN", "alice", "s3cret")}

    def test_applies_credentials_to_each_selected_connection(self):
        from vpn_manager.tui import apply_credentials_screen, common

        with mock.patch.object(
            common, "pick_connections", return_value=["MyOpenVPN", "MyGateway"]
        ), mock.patch.object(
            apply_credentials_screen.creds, "load_profiles", return_value=self._profile()
        ), mock.patch.object(
            common, "pick_profile", return_value="Nord"
        ), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "info") as info, mock.patch.object(
            apply_credentials_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli()
        ) as run_nmcli:
            apply_credentials_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        for name in ("MyOpenVPN", "MyGateway"):
            self.assertIn(
                ["connection", "modify", name, "+vpn.data", "connection-type=password,username=alice"],
                commands,
            )
            self.assertIn(
                ["connection", "modify", name, "+vpn.secrets", "password=s3cret"], commands
            )
        self.assertNotIn("FEHLER", info.call_args.args[2])

    def test_non_openvpn_connection_is_skipped(self):
        from vpn_manager.tui import apply_credentials_screen, common

        with mock.patch.object(common, "pick_connections", return_value=["MyGateway"]), mock.patch.object(
            apply_credentials_screen.creds, "load_profiles", return_value=self._profile()
        ), mock.patch.object(common, "pick_profile", return_value="Nord"), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "info") as info, mock.patch.object(
            apply_credentials_screen.nmcli,
            "run_nmcli",
            side_effect=self._fake_nmcli("org.freedesktop.NetworkManager.openconnect"),
        ) as run_nmcli:
            apply_credentials_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertFalse([c for c in commands if "+vpn.data" in c])
        self.assertIn("übersprungen", info.call_args.args[2])

    def test_wireguard_is_not_offered(self):
        from vpn_manager.tui import apply_credentials_screen, common

        with mock.patch.object(common, "pick_connections", return_value=[]) as pick, mock.patch.object(
            apply_credentials_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli()
        ):
            apply_credentials_screen.run(self.screen, dry_run=True)

        offered = pick.call_args.args[1]
        self.assertEqual(offered, ["MyOpenVPN", "MyGateway"])

    def test_unsupported_type_is_skipped_without_modifying(self):
        from vpn_manager.tui import apply_credentials_screen, common

        with mock.patch.object(common, "pick_connections", return_value=["MyOpenVPN"]), mock.patch.object(
            apply_credentials_screen.creds, "load_profiles", return_value=self._profile()
        ), mock.patch.object(common, "pick_profile", return_value="Nord"), mock.patch.object(
            common, "confirm", return_value=True
        ), mock.patch.object(common, "info") as info, mock.patch.object(
            apply_credentials_screen.nmcli,
            "run_nmcli",
            side_effect=self._fake_nmcli("org.freedesktop.NetworkManager.openconnect"),
        ) as run_nmcli:
            apply_credentials_screen.run(self.screen, dry_run=True)

        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertFalse([c for c in commands if "+vpn.secrets" in c])
        self.assertIn("übersprungen", info.call_args.args[2])

    def test_cancelled_profile_choice_changes_nothing(self):
        from vpn_manager.tui import apply_credentials_screen, common

        with mock.patch.object(common, "pick_connections", return_value=["MyOpenVPN"]), mock.patch.object(
            apply_credentials_screen.creds, "load_profiles", return_value=self._profile()
        ), mock.patch.object(common, "pick_profile", return_value=None), mock.patch.object(
            common, "confirm"
        ) as confirm, mock.patch.object(
            apply_credentials_screen.nmcli, "run_nmcli", side_effect=self._fake_nmcli()
        ) as run_nmcli:
            apply_credentials_screen.run(self.screen, dry_run=True)

        confirm.assert_not_called()
        commands = [call.args[0] for call in run_nmcli.call_args_list]
        self.assertFalse([c for c in commands if "modify" in c])


class PickConnectionsTests(ScreenTestCase):
    def test_label_is_displayed_but_connection_name_is_returned(self):
        """Der Anzeigetext darf nie als Verbindungsname zurückkommen."""
        from vpn_manager.tui import common

        self.snack.ButtonBar.return_value.buttonPressed.return_value = "go"
        self.snack.CheckboxTree.return_value.getSelection.return_value = ["MyConn"]

        result = common.pick_connections(
            self.screen,
            ["MyConn"],
            "Titel",
            "Text",
            "Los",
            "go",
            labels={"MyConn": "MyConn  (autoconnect: AN)"},
            preselect={"MyConn"},
        )

        append = self.snack.CheckboxTree.return_value.append.call_args
        self.assertEqual(append.args[0], "MyConn  (autoconnect: AN)")
        self.assertEqual(append.args[1], "MyConn")
        self.assertEqual(append.kwargs["selected"], 1)
        self.assertEqual(result, ["MyConn"])

    def test_without_labels_the_name_is_displayed_unselected(self):
        from vpn_manager.tui import common

        self.snack.ButtonBar.return_value.buttonPressed.return_value = "go"
        self.snack.CheckboxTree.return_value.getSelection.return_value = []

        with mock.patch.object(common, "info"):
            common.pick_connections(self.screen, ["MyConn"], "Titel", "Text", "Los", "go")

        append = self.snack.CheckboxTree.return_value.append.call_args
        self.assertEqual(append.args[0], "MyConn")
        self.assertEqual(append.kwargs["selected"], 0)


class AutoconnectScreenTests(ScreenTestCase):
    LISTING = "MyWireguard:wireguard:yes\nMyOpenVPN:vpn:no\nMyGateway:vpn:yes\nHome Wifi:802-11-wireless:yes\n"

    def test_preselects_connections_with_autoconnect_enabled(self):
        from vpn_manager.tui import autoconnect_screen, common

        with mock.patch.object(
            autoconnect_screen.nmcli, "run_nmcli", return_value=self.ok_result(self.LISTING)
        ), mock.patch.object(common, "pick_connections", return_value=[]) as pick:
            autoconnect_screen.run(self.screen, dry_run=True)

        offered = pick.call_args.args[1]
        self.assertEqual(offered, ["MyWireguard", "MyOpenVPN", "MyGateway"])
        self.assertEqual(pick.call_args.kwargs["preselect"], {"MyWireguard", "MyGateway"})
        self.assertIn("AN", pick.call_args.kwargs["labels"]["MyGateway"])
        self.assertIn("aus", pick.call_args.kwargs["labels"]["MyOpenVPN"])

    def test_disables_autoconnect_for_selected(self):
        from vpn_manager.tui import autoconnect_screen, common

        with mock.patch.object(
            autoconnect_screen.nmcli, "run_nmcli", return_value=self.ok_result(self.LISTING)
        ), mock.patch.object(
            common, "pick_connections", return_value=["MyWireguard", "MyGateway"]
        ), mock.patch.object(common, "info"), mock.patch.object(
            autoconnect_screen.nmcli, "ensure_autoconnect_off"
        ) as autoconnect_off:
            autoconnect_screen.run(self.screen, dry_run=True)

        disabled = [call.args[0] for call in autoconnect_off.call_args_list]
        self.assertEqual(disabled, ["MyWireguard", "MyGateway"])

    def test_nothing_to_do_when_all_already_disabled(self):
        from vpn_manager.tui import autoconnect_screen, common

        listing = self.ok_result("MyOpenVPN:vpn:no\nMyWireguard:wireguard:no\n")
        with mock.patch.object(
            autoconnect_screen.nmcli, "run_nmcli", return_value=listing
        ), mock.patch.object(common, "info") as info, mock.patch.object(
            common, "pick_connections"
        ) as pick:
            autoconnect_screen.run(self.screen, dry_run=True)

        pick.assert_not_called()
        self.assertIn("bereits deaktiviert", info.call_args.args[2])

    def test_cancel_changes_nothing(self):
        from vpn_manager.tui import autoconnect_screen, common

        with mock.patch.object(
            autoconnect_screen.nmcli, "run_nmcli", return_value=self.ok_result(self.LISTING)
        ), mock.patch.object(common, "pick_connections", return_value=[]), mock.patch.object(
            autoconnect_screen.nmcli, "ensure_autoconnect_off"
        ) as autoconnect_off:
            autoconnect_screen.run(self.screen, dry_run=True)

        autoconnect_off.assert_not_called()


class CredentialsScreenTests(ScreenTestCase):
    def test_back_button_leaves_screen(self):
        from vpn_manager.tui import credentials_screen

        self.snack.ButtonBar.return_value.buttonPressed.return_value = "back"

        with mock.patch.object(credentials_screen.creds, "load_profiles", return_value={}):
            credentials_screen.run(self.screen, dry_run=True)

    def test_corrupted_store_is_reported_and_does_not_crash(self):
        from vpn_manager.tui import common, credentials_screen

        error = credentials_screen.creds.CredentialsFileError("kaputt")
        with mock.patch.object(
            credentials_screen.creds, "load_profiles", side_effect=error
        ), mock.patch.object(common, "info") as info:
            credentials_screen.run(self.screen, dry_run=True)

        info.assert_called_once()
        self.assertIn("kaputt", info.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
