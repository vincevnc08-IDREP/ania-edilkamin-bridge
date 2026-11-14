import sys,pathlib,tempfile,unittest,time
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'server/app'))
import bridge
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=self.tmp.name+'/db';self.radio=Mock();self.radio.power_hold3s.return_value={'status':'sent','hold_ms':3000,'release_sent':True,'power_state':None};self.s=bridge.Service(self.radio,self.db)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def request(self,rid='p'*32):return self.s.command(dict(command='power',request_id=rid))
 def test_no_optimistic_state_and_duplicate_never_emits(self):
  code,data=self.request();self.assertEqual(code,200);self.assertEqual(data['status'],'sent');self.assertIsNone(data['power_state']);self.assertEqual(self.request()[0],200);self.radio.power_hold3s.assert_called_once();self.radio.read_state.assert_not_called()
 def test_distinct_id_blocked_by_durable_cooldown(self):
  self.request();self.assertEqual(self.request('q'*32)[0],429);self.s.close();self.s=bridge.Service(self.radio,self.db);self.assertEqual(self.request('r'*32)[0],429);self.radio.power_hold3s.assert_called_once()
 def test_failed_command_is_never_retried(self):
  self.radio.power_hold3s.side_effect=TimeoutError('unknown');self.assertEqual(self.request()[1]['status'],'indeterminate');self.request();self.assertEqual(self.request('q'*32)[0],429);self.radio.power_hold3s.assert_called_once()
 def test_new_explicit_request_after_cooldown(self):
  self.request();self.s.db.execute("UPDATE safety SET value=0");self.s.db.commit();self.assertEqual(self.request('q'*32)[0],200);self.assertEqual(self.radio.power_hold3s.call_count,2)
 def test_on_off_and_raw_commands_rejected(self):
  for c in ['on','off','power_hold3s','power_test_hold3s']:
   self.assertEqual(self.s.command(dict(command=c,request_id='x'*32))[0],422)
  self.radio.power_hold3s.assert_not_called()
 def test_optional_gate(self):
  with patch.object(bridge,'POWER_ENABLED',False):self.assertEqual(self.request()[0],422)
  self.radio.power_hold3s.assert_not_called()
