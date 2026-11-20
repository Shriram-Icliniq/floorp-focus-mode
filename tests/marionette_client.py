import socket,json,itertools,sys
class Marionette:
 def __init__(self,port):
  self.sock=socket.create_connection(('127.0.0.1',port),timeout=15);self.sock.settimeout(90);self.counter=itertools.count(1);self.hello=self.recv();self.cmd('WebDriver:NewSession',{'capabilities':{}});self.cmd('Marionette:SetContext',{'value':'chrome'})
 def recv(self):
  size=b''
  while not size.endswith(b':'):size+=self.sock.recv(1)
  remaining=int(size[:-1]);chunks=[]
  while remaining:
   chunk=self.sock.recv(remaining)
   if not chunk:raise EOFError()
   chunks.append(chunk);remaining-=len(chunk)
  return json.loads(b''.join(chunks))
 def cmd(self,command,params={}):
  id=next(self.counter);data=json.dumps([0,id,command,params]).encode();self.sock.sendall(str(len(data)).encode()+b':'+data)
  while True:
   msg=self.recv()
   if msg[0]==1 and msg[1]==id:
    if msg[2]:raise RuntimeError(msg[2])
    return msg[3]
 def js(self,script,args=[],async_=False):
  return self.cmd('WebDriver:ExecuteAsyncScript' if async_ else 'WebDriver:ExecuteScript',{'script':script,'args':args,'newSandbox':False,'sandbox':'default','scriptTimeout':90000})
if __name__=='__main__':
 m=Marionette(int(sys.argv[1]));print(json.dumps(m.js(sys.stdin.read(),async_="--async" in sys.argv),indent=2))
