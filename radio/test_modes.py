import unittest,time
from unittest.mock import Mock
from state import parse_frame,Consensus
from decode_cyrf import frame_crc
from client import Radio,PrecheckError
META=dict(continuous_verified=True,neutral_poll=True,tx_rc=0,rx_rc=0,tx_errors=0,tx_restarts=0)
def f(text):
 b=bytes([16])+text.encode().ljust(16);b+=frame_crc(b).to_bytes(2,'little');return dict(frame_hex=b.hex(),continuous_verified=True)
def state(mode,level=None):return dict(mode=mode,power_mode=level,setpoint_c=17 if mode=='AUTO' else None,observed_at=time.time())
class Tests(unittest.TestCase):
 def test_manual_levels_and_dot(self):
  for level in range(1,4):
   for sep in [' ','.']:
    r=parse_frame(f(f'Power {sep}{level}reserve '));self.assertEqual(r['power_mode'],level);self.assertEqual(r['mode'],'MANUAL');self.assertIsNone(r['setpoint_c'])
 def test_setting_menu_formats(self):
  self.assertEqual(parse_frame(f('Auto reg17 &C'))['setpoint_c'],17)
  for level in range(1,4):
   self.assertEqual(parse_frame(f(f'POWER P{level}   +/-'))['power_mode'],level)
  self.assertEqual(parse_frame(f('POWER P4   +/-'))['kind'],'display_unparsed')
 def test_shutdown_not_temperature(self):
  r=parse_frame(f('OFF 13'));self.assertEqual(r['mode'],'SHUTDOWN');self.assertEqual(r['shutdown_counter'],13);self.assertIsNone(r['setpoint_c'])
 def test_manual_conflict_resets_auto_consensus(self):
  c=Consensus();c.add('a',100,[f('reg 17&Creserve ')],META,101)
  self.assertIsNone(c.add('b',102,[f('Power  1reserve ')],META,103))
  self.assertEqual(c.add('c',104,[f('Power .1reserve ')],META,105)['power_mode'],1)
 def radio(self):
  r=Radio.__new__(Radio);r.read_state=Mock();r.button_once=Mock();r.confirm_mode=Mock();return r
 def test_no_action_while_shutdown(self):
  r=self.radio();r.read_state.return_value=state('SHUTDOWN')
  with self.assertRaises(PrecheckError):r.set_mode('P1')
  r.button_once.assert_not_called()
 def test_unknown_mode_no_action(self):
  r=self.radio()
  with self.assertRaises(PrecheckError):r.set_mode('POWER')
  r.read_state.assert_not_called();r.button_once.assert_not_called()
 def test_manual_selection_then_two_confirmed_steps(self):
  r=self.radio();r.read_state.side_effect=[state('AUTO'),state('MANUAL',1),state('MANUAL',2)];r.confirm_mode.side_effect=[state('MANUAL',1),state('MANUAL',2),state('MANUAL',3)]
  self.assertEqual(r.set_mode('P3')['after']['power_mode'],3);self.assertEqual([c.args[0] for c in r.button_once.call_args_list],['manual','plus','plus'])
 def test_mode_timeout_never_steps(self):
  r=self.radio();r.read_state.return_value=state('AUTO');r.confirm_mode.side_effect=RuntimeError('timeout')
  with self.assertRaises(RuntimeError):r.set_mode('P3')
  r.button_once.assert_called_once_with('manual')
 def test_external_change_stops_sequence(self):
  r=self.radio();r.read_state.side_effect=[state('MANUAL',1),state('AUTO')]
  with self.assertRaises(RuntimeError):r.set_mode('P3')
  r.button_once.assert_not_called()
 def test_current_target_sends_nothing(self):
  r=self.radio();r.read_state.return_value=state('MANUAL',2);self.assertEqual(r.set_mode('P2')['actions'],[]);r.button_once.assert_not_called()
