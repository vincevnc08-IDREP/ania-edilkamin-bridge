import pathlib,sys,socket,threading,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'radio'))
from network_stream import NetworkStream
TOKEN='a'*64
class NetworkTests(unittest.TestCase):
 def server(self,handler):
  sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen();self.addCleanup(sock.close)
  errors=[]
  def run():
   try:
    c,_=sock.accept()
    with c:handler(c)
   except Exception as e:errors.append(e)
  t=threading.Thread(target=run,daemon=True);t.start();return sock.getsockname()[1],t,errors
 def test_drop_after_command_does_not_replay(self):
  seen=[]
  def handler(c):
   f=c.makefile('rb');self.assertEqual(f.readline(),('AUTH '+TOKEN+'\n').encode());c.sendall(b'ANIA_DUAL 1\n')
   seen.append(f.readline());f.close()
  port,t,errors=self.server(handler);s=NetworkStream('127.0.0.1',port,TOKEN);self.addCleanup(s.close)
  s.write(b'tx plus_once 10\n');t.join(2)
  with self.assertRaises(ConnectionError):s.read(1)
  with self.assertRaises(ConnectionError):s.write(b'tx plus_once 10\n')
  self.assertEqual(seen,[b'tx plus_once 10\n']);self.assertFalse(errors)
 def test_bad_banner_never_sends_command(self):
  def handler(c):c.recv(128);c.sendall(b'wrong\n')
  port,t,errors=self.server(handler)
  with self.assertRaises(ConnectionError):NetworkStream('127.0.0.1',port,TOKEN)
  t.join(2);self.assertFalse(errors)
 def test_fragmented_banner_and_data(self):
  def handler(c):
   c.recv(128)
   for b in b'ANIA_DUAL 1\n':c.sendall(bytes([b]))
   self.assertEqual(c.recv(128),b'rx status\n');c.sendall(b'first\nsecond\n')
  port,t,errors=self.server(handler);s=NetworkStream('127.0.0.1',port,TOKEN);self.addCleanup(s.close);s.write(b'rx status\n')
  data=b''
  while len(data)<13:data+=s.read(2)
  self.assertEqual(data,b'first\nsecond\n');t.join(2);self.assertFalse(errors)
if __name__=='__main__':unittest.main()
