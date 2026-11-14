import unittest,tempfile,pathlib
from unittest.mock import Mock
from client import Radio,PrecheckError
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Radio.__new__(Radio);self.r.out=pathlib.Path(self.tmp.name);self.r.check=Mock();self.r.cmd=Mock()
 def tearDown(self):self.tmp.cleanup()
 def test_sent_is_not_on(self):
  self.r.cmd.return_value=b'POWER_HOLD packets=47 elapsed_ms=3000 planned_ms=3000 cadence_ms=64 rc=0\nTX_DONE press_rc=0 release_rc=0 release_packets=1\n';d=self.r.power_hold3s();self.assertEqual(d['status'],'sent');self.assertIsNone(d['power_state']);self.r.cmd.assert_called_once()
 def test_cooldown_no_rf(self):
  self.r.cmd.return_value=b'POWER_REJECT cooldown_ms=1000 no_rf=1\n'
  with self.assertRaises(PrecheckError):self.r.power_hold3s()
 def test_missing_release_or_wrong_duration_no_retry(self):
  for raw in [b'POWER_HOLD packets=47 elapsed_ms=100 planned_ms=3000 cadence_ms=64 rc=0\nTX_DONE press_rc=0 release_rc=0\n',b'TX_DONE press_rc=0 release_rc=1\n']:
   self.r.cmd.reset_mock();self.r.cmd.return_value=raw
   with self.assertRaises(RuntimeError):self.r.power_hold3s()
   self.r.cmd.assert_called_once()
