import sys,pathlib,tempfile,time,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'server/app'))
import bridge
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.radio=Mock();self.s=bridge.Service(self.radio,self.tmp.name+'/db')
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def test_modes_disabled_by_default(self):
  with patch.object(bridge,'MODES_ENABLED',False):self.assertEqual(self.s.command({'command':'mode','mode':'P1','request_id':'a'*32})[0],422)
  self.radio.set_mode.assert_not_called()
 def test_no_internal_command_bypass(self):
  self.assertEqual(self.s.command({'command':'mode:P1','request_id':'a'*32})[0],422);self.radio.set_mode.assert_not_called()
 def test_mode_dedup_and_conflicting_target(self):
  after=dict(mode='MANUAL',power_mode=2,setpoint_c=None,observed_at=time.time());self.radio.set_mode.return_value={'after':after}
  with patch.object(bridge,'MODES_ENABLED',True):
   req={'command':'mode','mode':'P2','request_id':'a'*32};c,r=self.s.command(req);self.assertEqual(c,200);self.assertEqual(r['power_mode'],2);self.assertIsNone(r['setpoint_c']);self.s.command(req);self.radio.set_mode.assert_called_once_with('P2');self.assertEqual(self.s.command(dict(req,mode='P3'))[0],409)
 def test_unknown_result_is_not_replayed(self):
  self.radio.set_mode.side_effect=RuntimeError('unknown')
  with patch.object(bridge,'MODES_ENABLED',True):
   req=dict(command='mode',mode='AUTO',request_id='b'*32);self.assertEqual(self.s.command(req)[1]['status'],'indeterminate');self.s.command(req);self.radio.set_mode.assert_called_once()
 def test_shutdown_snapshot_preserves_counter_not_temperature(self):
  self.s.cache=dict(mode='SHUTDOWN',shutdown_counter=5,power_mode=None,setpoint_c=None,display_raw='OFF 5',observed_at=time.time());c,r=self.s.state();self.assertEqual(c,200);self.assertEqual(r['shutdown_counter'],5);self.assertIsNone(r['setpoint_c']);self.radio.read_state.assert_not_called()
