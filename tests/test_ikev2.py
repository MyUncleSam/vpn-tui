import unittest

from vpn_manager import ikev2


class Ikev2Tests(unittest.TestCase):
    def test_build_add_ikev2_command(self):
        argv = ikev2.build_add_ikev2_command("MyGateway", "vpn.example.com")
        self.assertEqual(
            argv[:8],
            ["connection", "add", "type", "vpn", "vpn-type", "strongswan", "con-name", "MyGateway"],
        )
        self.assertEqual(argv[8], "vpn.data")
        self.assertIn("address=vpn.example.com", argv[9])
        self.assertIn("method=eap", argv[9])

    def test_build_apply_credentials_commands(self):
        data_cmd, secret_cmd = ikev2.build_apply_credentials_commands("MyGateway", "alice", "s3cret")
        self.assertEqual(
            data_cmd,
            ["connection", "modify", "MyGateway", "+vpn.data", f"{ikev2.STRONGSWAN_USERNAME_KEY}=alice"],
        )
        self.assertEqual(
            secret_cmd, ["connection", "modify", "MyGateway", "+vpn.secrets", "password=s3cret"]
        )


if __name__ == "__main__":
    unittest.main()
