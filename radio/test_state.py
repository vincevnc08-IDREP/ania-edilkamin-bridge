import unittest, time, json
import numpy as np
from state import parse_frame,Consensus
from decode_cyrf import frame_crc,frame_rank,decode_soft_at,CODEBOOK,SOP_BITS

def frame(temp=20):
 raw=bytes([16])+f'reg {temp:02d}&Creserve '.encode();raw+=frame_crc(raw).to_bytes(2,'little')
 return dict(frame_hex=raw.hex(),continuous_verified=True,quality_pass=True)
META=dict(continuous_verified=True,neutral_poll=True,tx_rc=0,rx_rc=0,tx_errors=0,tx_restarts=0)
class Tests(unittest.TestCase):
 def test_parse_real_display(self):self.assertEqual(parse_frame(frame())['setpoint_c'],20)
 def test_unknown_display_preserved_not_onoff(self):
  raw=bytes([16])+b'OFF             ';raw+=frame_crc(raw).to_bytes(2,'little');f=dict(frame_hex=raw.hex(),continuous_verified=True)
  r=parse_frame(f);self.assertEqual(r['kind'],'display_unparsed');self.assertEqual(r['power_state'],'unknown')
 def test_binary_changed_flags_preserved(self):
  raw=bytes.fromhex('0700ff000010c8e2');raw+=frame_crc(raw).to_bytes(2,'little');r=parse_frame(dict(frame_hex=raw.hex(),continuous_verified=True));self.assertEqual(r['kind'],'binary');self.assertEqual(r['power_state'],'unknown')
 def test_crc_recomputed(self):
  f=frame();f['frame_hex']=f['frame_hex'][:-2]+'00';f['crc_matches']=True;self.assertIsNone(parse_frame(f))
 def test_two_distinct_polls(self):
  c=Consensus();self.assertIsNone(c.add('a',100,[frame()],META,101));self.assertIsNone(c.add('a',100,[frame()],META,101));self.assertEqual(c.add('b',102,[frame()],META,103)['setpoint_c'],20)
 def test_conflict_resets(self):
  c=Consensus();c.add('a',100,[frame()],META,101);self.assertIsNone(c.add('b',102,[frame(21)],META,103))
 def test_stale_unknown(self):
  c=Consensus();c.add('a',100,[frame()],META,101);c.add('b',102,[frame()],META,103);self.assertIsNone(c.current(133))
 def test_failed_tx_not_state(self):self.assertIsNone(Consensus().add('a',100,[frame()],dict(META,tx_rc=-1),101))
 def test_crc_ranking(self):
  good=dict(crc_matches=True,quality_pass=False,symbols=[{'errors':4}],sop_errors=[4,4]);bad=dict(crc_matches=False,quality_pass=True,symbols=[{'errors':0}],sop_errors=[0,0]);self.assertLess(frame_rank(good),frame_rank(bad))
 def test_soft_json_roundtrip(self):
  raw=bytes.fromhex(frame()['frame_hex']);bits=SOP_BITS+'1010'+SOP_BITS+'1'+''.join(''.join(str((CODEBOOK[b]>>i)&1)for i in range(32))for b in raw)
  result=decode_soft_at(np.array([int(b)*2-1 for b in bits]),np.int64(0));self.assertTrue(result['crc_matches']);json.dumps(result)
if __name__=='__main__':unittest.main()
