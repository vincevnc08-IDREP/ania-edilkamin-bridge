import sys,time,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server/app'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radio'))
from client import Radio
from bridge import Service
class Tests(unittest.TestCase):
 def state(self,age=0):return dict(mode='MANUAL',power_mode=2,setpoint_c=None,display_raw='Power  2reserve ',observed_at=time.time()-age,confirmed_by_polls=['a','b'])
 def radio(self):
  r=Radio.__new__(Radio);r.s=Mock(closed=False);r.read_state=Mock(return_value=self.state());r.button_once=Mock();r.confirm_mode=Mock();r.close=Mock();return r
 def test_fresh_baseline_reused(self):
  r=self.radio();v=r.set_mode('P2',before=self.state());self.assertTrue(v['baseline_reused']);r.read_state.assert_not_called();r.button_once.assert_not_called()
 def test_old_or_disconnected_baseline_reread(self):
  for closed,age in [(False,3),(True,0),(False,-2)]:
   r=self.radio();r.s.closed=closed;r.set_mode('P2',before=self.state(age));r.read_state.assert_called_once()
 def test_single_read_not_reused(self):
  r=self.radio();s=self.state();s['confirmed_by_polls']=['a'];r.set_mode('P2',before=s);r.read_state.assert_called_once()
 def test_recent_normal_state_still_requires_setting_screen(self):
  r=self.radio();before=self.state(5);menu=self.state();menu['display_context']='setting_menu';after=dict(menu,power_mode=3);r.confirm_mode.side_effect=[menu,after]
  result=r.set_mode('P3',before=before)
  self.assertTrue(result['baseline_reused']);r.read_state.assert_not_called()
  self.assertEqual(result['actions'],['manual','plus']);r.confirm_mode.assert_any_call('MANUAL',setting_menu=True)
 def test_too_old_different_level_not_reused(self):
  r=self.radio();r.set_mode('P2',before=dict(self.state(11),power_mode=1));r.read_state.assert_called_once()
 def test_active_monitor_no_competing_reads(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio();s=Service(r,d+'/db');s.monitor=Mock();s.monitor.is_alive.return_value=True;s.monitor.join.return_value=None
   try:
    code,v=s.state();self.assertEqual(code,200);self.assertEqual(v['status'],'unavailable');r.read_state.assert_not_called()
   finally:s.close()
 def test_service_passes_confirmed_baseline(self):
  with tempfile.TemporaryDirectory() as d:
   r=Mock();s=Service(r,d+'/db');before=self.state();s.cache=before;r.set_mode.return_value={'after':before}
   try:
    self.assertEqual(s.command(dict(command='mode',mode='P2',request_id='u'*32))[0],200);r.set_mode.assert_called_once_with('P2',before=before)
   finally:s.close()
class DeadlineTests(unittest.TestCase):
 def test_confirmation_has_elapsed_time_bound(self):
  from unittest.mock import patch
  r=Radio.__new__(Radio);r.poll=Mock(return_value=('a',time.time(),[],{}))
  with patch('client.time.monotonic',side_effect=[0,0,11]):
   with self.assertRaises(RuntimeError):r.confirm_mode('MANUAL',2)
  r.poll.assert_called_once()
