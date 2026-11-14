import unittest,zlib
from fast_reply import parse_fast
from decode_cyrf import frame_crc
class FastReplyTests(unittest.TestCase):
 def reply(self,temp=20):
  packet=bytes([16])+f'reg {temp:02d}&Creserve '.encode();packet+=frame_crc(packet).to_bytes(2,'little')
  return (f'POLL tx_rc=0 rx_rc=0 tx_errors=0 tx_restarts=0\nFAST requested=32000 stored=32000 rc=0 lost_pairs=0 gaps=0 segments=1 continuous=1 decode_us=12000 count=1\nF 16000 1 {packet.hex()}\nFAST_END frames_crc32={zlib.crc32(packet)}\n').encode()
 def test_valid(self):
  f,m=parse_fast(self.reply(),123);self.assertTrue(m['continuous_verified']);self.assertTrue(f[0]['crc_matches'])
 def test_gap_invalidates_state(self):
  f,m=parse_fast(self.reply().replace(b'gaps=0',b'gaps=1'),123);self.assertFalse(f[0]['continuous_verified'])
 def test_bad_radio_crc_rejected(self):
  with self.assertRaises(ValueError):parse_fast(self.reply().replace(b'72656720',b'72656721'),123)
 def test_truncated_frame_list_rejected(self):
  with self.assertRaises(ValueError):parse_fast(self.reply().replace(b'count=1',b'count=2'),123)
 def test_duplicate_header_rejected(self):
  raw=self.reply()
  with self.assertRaises(ValueError):parse_fast(raw+raw.splitlines()[1]+b'\n',123)
 def test_transfer_crc_rejected(self):
  raw=self.reply();raw=raw[:raw.rindex(b'=')+1]+b'0\n'
  with self.assertRaises(ValueError):parse_fast(raw,123)
if __name__=='__main__':unittest.main()
