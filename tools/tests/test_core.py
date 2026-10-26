"""Integration/negative controls using an untracked user-supplied official BIN."""
import os
from pathlib import Path
import struct
import unittest
from tws3e.core import OFFICIAL_SHA, IMAGE_SHA, SCALE_OFFSET, audit, build, crc_values, official, parse, sha

SOURCE = os.environ.get('TWS3E_ORIGINAL')


@unittest.skipUnless(SOURCE and Path(SOURCE).is_file(), 'Set TWS3E_ORIGINAL to the local official BIN')
class FirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = Path(SOURCE).read_bytes()
        cls.fw = official(cls.raw)

    def test_profile_and_neutral_roundtrip(self):
        self.assertEqual(sha(self.raw), OFFICIAL_SHA)
        self.assertEqual(sha(self.fw.image), IMAGE_SHA)
        self.assertEqual(build(self.raw, 1.0), self.raw)

    def test_half_scale_and_audit(self):
        candidate = build(self.raw, 0.5)
        report = audit(self.raw, candidate, 0.5)
        self.assertTrue(report['only_scale_and_required_container_fields_changed'])
        image = parse(candidate).image
        self.assertEqual(image[SCALE_OFFSET:SCALE_OFFSET+4], struct.pack('<f', 0.5))
        with self.assertRaises(ValueError):
            audit(self.raw, candidate, 1.25)

    def test_wrong_source_rejected_even_with_valid_container(self):
        # A valid candidate cannot serve as a new baseline with fixed offsets.
        with self.assertRaises(ValueError):
            build(build(self.raw, 0.5), 1.25)

    def test_corruption_rejected(self):
        corrupt = bytearray(self.raw)
        corrupt[1000] ^= 1
        with self.assertRaises(ValueError):
            parse(corrupt)

    def test_identity_tampering_rejected_after_all_crc_checks_pass(self):
        candidate = bytearray(build(self.raw, 1.25))
        candidate[0x10] ^= 1  # Project field is outside the CRC-protected payload.
        parse(candidate)
        with self.assertRaises(ValueError):
            audit(self.raw, candidate, 1.25)

    def test_bad_lzma_rejected_even_after_outer_crc_repair(self):
        damaged = bytearray(self.raw)
        damaged[520] = 255  # First LZMA properties byte.
        payload = damaged[512:]
        values = crc_values(payload)
        struct.pack_into('<I', damaged, 8, values[-2])
        struct.pack_into(f'<{len(values)}I', damaged, 0x30, *values)
        with self.assertRaises((ValueError, __import__('lzma').LZMAError)):
            parse(damaged)

    def test_unsupported_scales_rejected(self):
        for value in (float('nan'), float('inf'), -1.0, 0.0, 2.0):
            with self.assertRaises(ValueError):
                build(self.raw, value)


if __name__ == '__main__':
    unittest.main()
