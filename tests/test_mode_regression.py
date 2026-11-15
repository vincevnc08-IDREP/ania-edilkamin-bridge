import sys,time,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radio'))
from client import Radio,PrecheckError
from state import parse_frame,Consensus
from decode_cyrf import frame_crc
META=dict(continuous_verified=True,neutral_poll=True,tx_rc=0,rx_rc=0,tx_errors=0,tx_restarts=0)
def frame(payload):
 raw=bytes([len(payload)])+payload;raw+=frame_crc(raw).to_bytes(2,'little')
 return dict(frame_hex=raw.hex(),continuous_verified=True)
def state(level=None,menu=False):
 return dict(mode='AUTO' if level is None else 'MANUAL',power_mode=level,setpoint_c=17 if level is None else None,observed_at=time.time(),display_context='setting_menu' if menu else None)
class Tests(unittest.TestCase):
 def test_actual_sixteen_byte_screen(self):
  raw=bytes.fromhex('10504f5745522050332020202b2f2d2020b478')
  self.assertEqual(len(raw[1:-2]),16)
  self.assertEqual(parse_frame(dict(frame_hex=raw.hex(),continuous_verified=True))['power_mode'],3)
  self.assertIsNone(parse_frame(frame(b'POWER P3   +/- ')))
 def test_two_actual_captures_confirm(self):
  c=Consensus();f=frame(b'POWER P3   +/-  ')
  self.assertIsNone(c.add('a',100,[f],META,100))
  self.assertEqual(c.add('b',101,[f],META,101)['power_mode'],3)
 def radio(self):
  r=Radio.__new__(Radio);r.read_state=Mock();r.button_once=Mock();r.confirm_mode=Mock();return r
 def test_auto_to_p1_no_extra_preread(self):
  r=self.radio();r.read_state.return_value=state();r.confirm_mode.side_effect=[state(3,True),state(2,True),state(1,True)]
  result=r.set_mode('P1');self.assertEqual(result['actions'],['manual','minus','minus']);r.read_state.assert_called_once()
 def test_normal_manual_screen_requires_m(self):
  r=self.radio();r.read_state.return_value=state(3);r.confirm_mode.side_effect=[state(3,True),state(2,True)]
  self.assertEqual(r.set_mode('P2')['actions'],['manual','minus'])
 def test_unconfirmed_menu_never_sends_step(self):
  r=self.radio();r.read_state.return_value=state(3);r.confirm_mode.side_effect=RuntimeError('no setting screen')
  with self.assertRaises(RuntimeError):r.set_mode('P2')
  r.button_once.assert_called_once_with('manual')
 def test_preread_failure_not_sent(self):
  r=self.radio();r.read_state.side_effect=RuntimeError('timeout')
  with self.assertRaises(PrecheckError):r.set_mode('P2')
  r.button_once.assert_not_called()
 def test_expired_confirmation_no_step(self):
  r=self.radio();r.read_state.return_value=state(3);old=state(3,True);old['observed_at']-=5;r.confirm_mode.return_value=old
  with self.assertRaises(RuntimeError):r.set_mode('P2')
  r.button_once.assert_called_once_with('manual')
class RecoveryTests(unittest.TestCase):
 def test_check_reconnect_is_no_rf(self):
  r=Radio.__new__(Radio);r.s=Mock(closed=False);r.connect=Mock();r.cmd=Mock(side_effect=[TimeoutError('lost'),b'TX_CHECK rc=0 ready=1 no_rf=1\n'])
  r.check();self.assertEqual([c.args[0] for c in r.cmd.call_args_list],['tx check','tx check']);r.connect.assert_called_once()
 def test_neutral_recovery_bounded(self):
  r=Radio.__new__(Radio);r._poll_once=Mock(side_effect=[TimeoutError('lost'),TimeoutError('lost')]);r.connect=Mock()
  with self.assertRaises(TimeoutError):r.poll()
  self.assertEqual(r._poll_once.call_count,2);r.connect.assert_called_once()
 def test_button_never_replayed(self):
  r=Radio.__new__(Radio);r.gain=10;r.check=Mock();r.cmd=Mock(side_effect=TimeoutError('lost'))
  with self.assertRaises(TimeoutError):r.button_once('manual')
  r.cmd.assert_called_once()
