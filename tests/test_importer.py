import tempfile
import unittest
from pathlib import Path

from vpn_manager import importer


class ScanFolderTests(unittest.TestCase):
    def test_scan_folder_filters_by_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "a.conf").write_text("wg")
            (folder / "b.ovpn").write_text("ovpn")
            (folder / "c.txt").write_text("ignore me")
            (folder / "subdir").mkdir()

            items = importer.scan_folder(folder)

            self.assertEqual(len(items), 2)
            by_type = {item.conn_type: item.path.name for item in items}
            self.assertEqual(by_type["wireguard"], "a.conf")
            self.assertEqual(by_type["openvpn"], "b.ovpn")

    def test_scan_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(importer.scan_folder(Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()
