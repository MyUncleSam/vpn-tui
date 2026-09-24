import stat
import tempfile
import unittest
from pathlib import Path

from vpn_manager import credentials as creds


class CredentialStoreTests(unittest.TestCase):
    def test_roundtrip_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "credentials.json"
            profiles = creds.add_profile({}, "Nord", "NordVPN", "alice", "s3cret")
            creds.save_profiles(profiles, path)

            self.assertTrue(path.exists())
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)

            loaded = creds.load_profiles(path)
            self.assertEqual(loaded["Nord"].provider, "NordVPN")
            self.assertEqual(loaded["Nord"].username, "alice")
            self.assertEqual(loaded["Nord"].password, "s3cret")

    def test_load_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "does-not-exist.json"
            self.assertEqual(creds.load_profiles(path), {})

    def test_add_duplicate_name_raises(self):
        profiles = creds.add_profile({}, "Nord", "NordVPN", "alice", "s3cret")
        with self.assertRaises(ValueError):
            creds.add_profile(profiles, "Nord", "NordVPN", "bob", "other")

    def test_update_profile(self):
        profiles = creds.add_profile({}, "Nord", "NordVPN", "alice", "s3cret")
        updated = creds.update_profile(profiles, "Nord", username="bob")
        self.assertEqual(updated["Nord"].username, "bob")
        self.assertEqual(updated["Nord"].provider, "NordVPN")

    def test_update_missing_profile_raises(self):
        with self.assertRaises(ValueError):
            creds.update_profile({}, "Nord", username="bob")

    def test_delete_profile(self):
        profiles = creds.add_profile({}, "Nord", "NordVPN", "alice", "s3cret")
        remaining = creds.delete_profile(profiles, "Nord")
        self.assertEqual(remaining, {})

    def test_delete_missing_profile_raises(self):
        with self.assertRaises(ValueError):
            creds.delete_profile({}, "Nord")


if __name__ == "__main__":
    unittest.main()
