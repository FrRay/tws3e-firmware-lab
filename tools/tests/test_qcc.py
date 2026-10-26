"""Exercise QCC parsing/extraction against the bundled historical samples."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from qcc_inspect import extract, inspect, parse_records

ROOT = Path(__file__).resolve().parents[2]


class QccTests(unittest.TestCase):
    def test_all_reference_files_match_manifest_and_parse(self):
        manifest = json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))
        samples = [row for row in manifest['files'] if row['kind']=='reference-firmware']
        self.assertEqual(len(samples), 12)
        for row in samples:
            with self.subTest(path=row['path']):
                path = ROOT/row['path']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'])
                summary, records = inspect(path)
                self.assertEqual(summary['sha256'], row['sha256'])
                self.assertEqual(records[0]['kind'], 'APPUHDR5')
                self.assertEqual(records[-1]['kind'], 'APPUPFTR')
                self.assertIn('7/download_anc_hw_manager.edkcs', summary['files'])

    def test_tws3_pair_has_known_anc_module_change(self):
        old, _ = inspect(ROOT/'library/firmware/TWS3/2.12.2.bin')
        new, _ = inspect(ROOT/'library/firmware/TWS3/2.12.6.bin')
        key = '7/download_anc_hw_manager.edkcs'
        self.assertNotEqual(old['files'][key]['sha256'], new['files'][key]['sha256'])

    def test_truncated_record_rejected(self):
        raw = (ROOT/'library/firmware/TWS3/2.12.2.bin').read_bytes()
        with self.assertRaises(ValueError):
            parse_records(raw[:-1])

    def test_extraction_preserves_partition_payload(self):
        _, records = inspect(ROOT/'library/firmware/TWS3/2.12.2.bin')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'unpacked'
            extract(records, target)
            partition = next(r['data'] for r in records if r.get('partition_id')==7)
            self.assertEqual((target/'partition_07.bin').read_bytes(), partition)
            self.assertTrue((target/'partition_07_files/download_anc_hw_manager.edkcs').is_file())


if __name__ == '__main__':
    unittest.main()
