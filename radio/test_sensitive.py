import unittest,random
from decode_cyrf_sensitive import decode_at,SOP_BITS
class SensitivityTests(unittest.TestCase):
 def test_damaged_sop_keeps_crc_validation(self):
  raw=bytes.fromhex('363333233333333382c79036219eff1725780c6913e2f97f7150b33f64f6870caafd491c0832a8d99f5f09d8ae3f64503301dbf1ebd1d80cfa5cfa02e3686c067d')
  bits=list(''.join(str((v>>i)&1)for v in raw for i in range(8)))
  for i in range(7):bits[64+i]='1' if bits[64+i]=='0' else '0'
  r=decode_at(''.join(bits),64);self.assertIsNotNone(r);self.assertTrue(r['crc_matches']);self.assertEqual(r['frame_hex'],'07123400aa17b57cc57d')
 def test_random_noise_not_accepted(self):
  rng=random.Random(13)
  for _ in range(1000):self.assertIsNone(decode_at(''.join(rng.choices('01',k=1000)),0))
