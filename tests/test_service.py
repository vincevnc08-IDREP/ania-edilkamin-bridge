import sys,time,tempfile,unittest,threading
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server/app'))
from bridge import Service
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.radio=Mock();self.s=Service(self.radio,self.tmp.name+'/db')
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def state(self,age=0):return dict(setpoint_c=13,observed_at=time.time()-age,display_raw='reg 13',confirmed_by_polls=['1','2'])
 def test_fresh_state_no_radio_no_fabricated_time(self):
  self.s.cache=self.state();stamp=self.s.cache['observed_at'];self.assertEqual(self.s.state()[1]['observed_at'],stamp);self.radio.read_state.assert_not_called()
 def test_stale_state_requires_read(self):
  self.s.cache=self.state(11);self.radio.read_state.return_value=self.state();self.s.state();self.radio.read_state.assert_called_once()
 def test_command_waits_short_poll_and_never_replays(self):
  self.s.cache=self.state();self.radio.step.return_value={'after':self.state()};self.s.lock.acquire()
  timer=threading.Timer(.05,self.s.lock.release);timer.start()
  data=dict(command='plus',request_id='a'*32);self.assertEqual(self.s.command(data)[0],200);self.assertEqual(self.s.command(data)[0],200);self.radio.step.assert_called_once();timer.join()
 def test_unknown_command_invalidates_cache_no_repeat(self):
  self.s.cache=self.state();self.radio.step.side_effect=RuntimeError('unknown')
  data=dict(command='plus',request_id='b'*32);self.assertEqual(self.s.command(data)[1]['status'],'indeterminate');self.assertIsNone(self.s.cache);self.s.command(data);self.radio.step.assert_called_once()
 def test_pending_command_stops_foreground_read(self):
  self.s.command_pending.set();self.assertEqual(self.s.state()[1]['status'],'unavailable');self.radio.read_state.assert_not_called()

class TargetTests(Tests):
 def target(self,value,rid='t'*32):
  response=self.s.command(dict(command='target',target_c=value,request_id=rid))
  if self.s.target_thread:self.s.target_thread.join(timeout=2)
  return response,self.s.command_status(rid)
 def test_target_steps_each_confirmed(self):
  self.radio.read_state.return_value=self.state()
  self.radio.step.side_effect=[{'after':dict(self.state(),setpoint_c=14)},{'after':dict(self.state(),setpoint_c=15)}]
  response,result=self.target(15)
  self.assertEqual(response[0],202);self.assertEqual(result[1]['status'],'confirmed');self.assertEqual(result[1]['steps_confirmed'],2)
  self.assertEqual([x.args[0] for x in self.radio.step.call_args_list],['plus','plus'])
  self.target(15);self.assertEqual(self.radio.step.call_count,2)
  self.assertEqual(self.s.command(dict(command='target',target_c=14,request_id='t'*32))[0],409)
 def test_target_stops_after_unknown(self):
  self.radio.read_state.return_value=self.state();self.radio.step.side_effect=RuntimeError('unknown')
  _,result=self.target(16);self.assertEqual(result[1]['status'],'indeterminate');self.radio.step.assert_called_once()
 def test_target_same_value_no_transmission(self):
  self.radio.read_state.return_value=self.state();_,result=self.target(13);self.assertEqual(result[1]['status'],'confirmed');self.radio.step.assert_not_called()
 def test_invalid_targets_never_transmit(self):
  for target in (True,9,26,13.5,'14'):
   self.assertEqual(self.s.command(dict(command='target',target_c=target,request_id='t'*32))[0],422)
  self.radio.step.assert_not_called()
 def test_stale_value_is_explicitly_stale(self):
  self.s.last_known=self.state(40);self.s.command_pending.set()
  code,value=self.s.state();self.assertEqual(code,200);self.assertEqual(value['status'],'stale');self.assertEqual(value['setpoint_c'],13)

class MonitorTests(Tests):
 def setUp(self):
  super().setUp();sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radio'))
  self.s.consensus=Mock();self.s.consensus.add.return_value=None
 def test_silence_preserves_fresh_confirmed_timestamp(self):
  self.s.cache=self.state();stamp=self.s.cache['observed_at']
  self.s.observe_poll(('empty',time.time(),[],{}))
  self.assertEqual(self.s.cache['observed_at'],stamp)
 def test_contradiction_invalidates(self):
  from unittest.mock import patch
  self.s.cache=self.state()
  with patch('state.parse_frame',return_value={'kind':'display','setpoint_c':14}):self.s.observe_poll(('different',time.time(),[{}],{}))
  self.assertIsNone(self.s.cache)
 def test_silence_never_refreshes_expired_reading(self):
  self.s.cache=self.state(11);self.s.observe_poll(('empty',time.time(),[],{}));self.assertIsNone(self.s.cache)

if __name__=='__main__':unittest.main()
