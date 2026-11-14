import unittest,tempfile,pathlib,json,time
from unittest.mock import Mock,patch
from client import Radio
class GuardTests(unittest.TestCase):
 def radio(self,path):
  r=Radio.__new__(Radio);r.out=pathlib.Path(path);r.index=0;r.button_once=Mock();return r
 def test_v8_waits_for_done_not_iq_dump(self):
  with tempfile.TemporaryDirectory() as d:
   r=Radio.__new__(Radio);r.out=pathlib.Path(d);r.index=0;r.gain=8;r.check=Mock();r.cmd=Mock(return_value=b'TX_DONE press_rc=0 release_rc=0\n')
   r.button_once('plus');self.assertEqual(r.cmd.call_count,1);self.assertIn(b'TX_DONE',r.cmd.call_args.args[1]);self.assertNotIn(b'RING_END',r.cmd.call_args.args[1])
 def test_old_readback_keeps_polling_without_button(self):
  r=Radio.__new__(Radio);r.poll=Mock(return_value=('p',0,[],{}))
  with patch('client.Consensus') as c:
   c.return_value.add.side_effect=[{'setpoint_c':20},{'setpoint_c':21}]
   self.assertEqual(r.read_state(expected=21)['setpoint_c'],21);self.assertEqual(r.poll.call_count,2)
 def test_fallback_window_and_bounded_failure(self):
  r=Radio.__new__(Radio);r.poll=Mock(return_value=('p',0,[],{}))
  with patch('client.Consensus') as c:
   c.return_value.add.return_value=None
   with self.assertRaises(RuntimeError):r.read_state()
  self.assertEqual([x.kwargs['window']for x in r.poll.call_args_list],[8]*4+[20]*8)
 def test_recognized_replies_keep_short_window(self):
  r=Radio.__new__(Radio);r.poll=Mock(return_value=('p',0,[{}],{}))
  with patch('client.Consensus') as c,patch('client.parse_frame',return_value={'kind':'binary'}):
   c.return_value.add.side_effect=[None]*5+[{'setpoint_c':20}]
   r.read_state()
  self.assertEqual([x.kwargs['window']for x in r.poll.call_args_list],[8]*6)
 def test_expected_state_has_bounded_longer_confirmation(self):
  r=Radio.__new__(Radio);r.poll=Mock(return_value=('p',0,[],{}))
  with patch('client.Consensus') as c:
   c.return_value.add.return_value=None
   with self.assertRaises(RuntimeError):r.read_state(expected=22)
  self.assertEqual(r.poll.call_count,18)
 def test_unknown_before_never_transmits(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio(d);r.read_state=Mock(side_effect=RuntimeError('unknown'))
   with self.assertRaises(RuntimeError):r.step('plus')
   r.button_once.assert_not_called()
 def test_unknown_after_never_retries(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio(d);r.read_state=Mock(side_effect=[{'setpoint_c':20},RuntimeError('unknown')])
   with self.assertRaises(RuntimeError):r.step('plus')
   r.button_once.assert_called_once_with('plus');self.assertEqual(json.loads(next(pathlib.Path(d).glob('command*')).read_text())['result'],'indeterminate')
 def test_wrong_state_never_retries(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio(d);r.read_state=Mock(side_effect=[{'setpoint_c':20},{'setpoint_c':20}])
   with self.assertRaises(RuntimeError):r.step('plus')
   r.button_once.assert_called_once_with('plus')
 def test_recent_confirmed_baseline_skips_pre_read(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio(d);r.read_state=Mock(return_value={'setpoint_c':21})
   baseline={'setpoint_c':20,'observed_at':time.time(),'confirmed_by_polls':['a','b']}
   result=r.step('plus',before=baseline);self.assertTrue(result['baseline_reused']);r.read_state.assert_called_once_with(expected=21)
 def test_stale_or_single_read_baseline_revalidated(self):
  for age,ids in [(11,['a','b']),(0,['a']),(0,['a','a']),(-10,['a','b'])]:
   with tempfile.TemporaryDirectory() as d:
    r=self.radio(d);r.read_state=Mock(side_effect=[{'setpoint_c':20},{'setpoint_c':21}])
    result=r.step('plus',before={'setpoint_c':20,'observed_at':time.time()-age,'confirmed_by_polls':ids});self.assertFalse(result['baseline_reused']);self.assertEqual(r.read_state.call_count,2)
 def test_confirmed_change(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.radio(d);r.read_state=Mock(side_effect=[{'setpoint_c':20},{'setpoint_c':21}]);self.assertEqual(r.step('plus')['result'],'confirmed_by_readback')
if __name__=='__main__':unittest.main()
