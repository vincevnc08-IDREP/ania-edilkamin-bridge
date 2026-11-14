"""Authenticated LAN transport. One socket; never reconnect/replay within a command."""
import select,socket,time
class NetworkStream:
 def __init__(self,host,port,token,timeout=.005):
  if len(token)<32 or '\n' in token or '\r' in token:raise ValueError('Invalid link token')
  self.sock=socket.create_connection((host,port),timeout=5)
  self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
  self.timeout=timeout;self.closed=False
  try:
   self.sock.sendall(('AUTH '+token+'\n').encode('ascii'))
   line=bytearray()
   while len(line)<64:
    b=self.sock.recv(1)
    if not b:raise ConnectionError('Gateway closed during authentication')
    line.extend(b)
    if b==b'\n':break
   if line!=b'ANIA_DUAL 1\n':raise ConnectionError('Gateway handshake failed')
  except Exception:self.close();raise
 def close(self):
  self.closed=True;self.sock.close()
 @property
 def in_waiting(self):return 65536 if not self.closed and select.select([self.sock],[],[],0)[0] else 0
 def write(self,data):
  if self.closed:raise ConnectionError('Link closed; command was not replayed')
  try:self.sock.sendall(data)
  except Exception:self.close();raise
  return len(data)
 def read(self,n):
  if self.closed:raise ConnectionError('Link closed; command was not replayed')
  try:
   if not select.select([self.sock],[],[],self.timeout)[0]:return b''
   data=self.sock.recv(n)
   if not data:raise ConnectionError('Gateway disconnected; command was not replayed')
   return data
  except Exception:self.close();raise
