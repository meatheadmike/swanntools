# Dump raw h264 streams from a Swann DVR8-2600
#
# Example usage
# -------------
#
# Play the live feed from cam 3 on the media port using ffplay:
# python swanndump.py --host MYHOST.swanndvr.net --port 9000 --cam 3 --method media --login_packet data/login.hex | ffplay -i /dev/stdin -probesize 32 -fpsprobesize 0 -analyzeduration 0 -f h264
#
# Play the live feed from cam 5 on the mobile port using ffplay:
# python swanndump.py --host MYHOST.swanndvr.net --port 18004 --cam 5 --method mobile --user admin --password MYPASS | ffplay -i /dev/stdin -probesize 32 -fpsprobesize 0 -analyzeduration 0 -f h264
#
# Grab a snapshot from cam 4 and on the media port and save as a .jpg using avconv:
# python swanndump.py --host MYHOST.swanndvr.net --port 9000 --cam 4 --capture_bytes 17408 --method media --login_packet data/login.hex | avconv -c:v h264 -i - -vframes 1 -pix_fmt yuvj420p -f image2 mycap.jpg
#
# Note: on the raspberry pi, I had better luck with avconv with the following params:
#       avconv -probesize 32 -analyzeduration 0 -ss 0 -c:v h264 -i - -vframes 1 -vf scale=704:480 -pix_fmt yuvj420p -f image2 /run/shm/mycap.jpg
# For whatever reason the brew version of livav on OSX doesn't like some of the parameters. 
#
import argparse,time,select,socket,sys,struct

class SwannDump:

  l_onoff = False
  l_linger = 0

  def getMediaLoginPacket(self, file, channel):
    x = bytearray()
    with file as f:
      bytes = f.read(1024)
      if len(bytes) == 1014:
        x = bytearray.fromhex(bytes)
      else:
        raise ValueError('Unexpected media login packet length [%s]!' % len(bytes))
    if channel == 1:
      x[52] = b"\x40"
    elif channel == 4:
      x[52] = b"\x80"
    else:
      x[52] = b"\x00"
    if channel == 2:
      x[158] = b"\x02"
    else: 
      x[158] = b"\x00"
    if channel == 3:
      x[93] = b"\x80"
    else:
      x[93] = b"\x00"
    if channel == 5:
      x[138] = b"\x08"
    else:
      x[138] = b"\x00"
    if channel == 6:
      x[120] = b"\x20"
    else:
      x[120] = b"\x00"
    if channel == 7:
      x[51] = b"\x01"
    else:
      x[51] = b"\x00"
    if channel == 8:
      x[92] = b"\xc1"
    else:
      x[92] = b"\x00"
    self.login_packet = x
 
  def getMobileLoginPacket(self, user, password, channel):
    x = bytearray.fromhex(
      "00 00 00 48 00 00 00 00  28 00 04 00 05 00 00 00"+
      "29 00 38 00 00 00 00 00  00 00 00 00 00 00 00 00"+
      "00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00"+
      "00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00"+
      "00 00 00 00 00 00 00 00  00 00 00 00"
    )
    idx = 20
    x[idx:idx+len(user)] = user
    idx = 52
    x[idx:idx+len(password)] = password
    x[73] = channel - 1
    self.login_packet = x
 
  def getSocket(self, host, port):
    sys.stderr.write("Creating socket.\n")
    self.sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack('LL', 5, 0))
    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('LL', self.l_onoff, self.l_linger))
    self.sock.connect((host, port))
    self.sock.setblocking(0)

  def doLogin(self):
    sys.stderr.write("Sending login packet.\n")
    tries = 5
    while True and tries > 0:
      try:
        self.sock.send(self.login_packet)
        response = self.sock.recv(8)
        if len(response) == 8:
          if response == bytearray.fromhex("10 00 00 00 00 00 00 00"):
            sys.stderr.write("Login success!\n")
            return # successful media response
          if response == bytearray.fromhex("00 00 00 14 00 00 00 00"):
            sys.stderr.write("Login success!\n")
            return # successful mobile response
      except Exception,e:
        tries -= 1
        sys.stderr.write("Login attempt failed! Retries remaining:%s\n" % tries) 
        time.sleep(.1)
    raise NameError('Unable to log in to DVR')

  def streamCam(self,host,port,capture_bytes):
    stream_forever = False
    if capture_bytes < 1:
      stream_forever = True
    self.getSocket(host, port)
    self.doLogin()
    conn = [self.sock]
    sys.stderr.write("Streaming data...\n")
    while stream_forever or capture_bytes > 0:
      read_sockets,write_sockets,error_sockets = select.select(conn,[],[])
      for s in read_sockets:
        try:
          response = s.recv(1024)
          nbytes = len(response) 
          if not stream_forever:
            capture_bytes -= nbytes
          if nbytes == 0:
            sys.stderr.write("Waiting for data...\n")
            time.sleep(.5)
          else:
            sys.stdout.write(response)
        except Exception, e:
          if nbytes > 0:
            capture_bytes = 0
            break 
          sys.stderr.write("Exception:%s\n" % e)
          s.close()
          conn.remove(s)
          self.getSocket(host, port)
          conn.append(self.sock)
          self.doLogin()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Dump raw h264 from DVR')

  parser.add_argument('--host', type=str, required=True, help="enter the dvr host (ie: XXXXX.swanndvr.net)")
  parser.add_argument('--port', type=int, required=True, help="enter your port # (ie: 9000 for media or 18004 for mobile)")
  parser.add_argument('--cam', type=int, choices=range(1,9), required=True, help="enter a camera number")
  parser.add_argument('--method', type=str, required=True, choices=['media','mobile'], help="specify the capture method (mobile=low def, media=hi def)")
  parser.add_argument('--capture_bytes', type=int, required=False, default=0, help="stop after X bytes captured (0=unlimited)")
  parser.add_argument('--login_packet', type=argparse.FileType('rb'), required=False, default="data/login.hex", help="path to media stream login packet")
  parser.add_argument('--user', type=str, required=False, default="admin", help="specify a user name")
  parser.add_argument('--password', type=str, required=False, default="", help="specify a password")

  args=parser.parse_args()

  sd = SwannDump()

  if (args.method == 'mobile'):
    sd.getMobileLoginPacket(args.user, args.password, args.cam)
  else:
    sd.getMediaLoginPacket(args.login_packet, args.cam)

  sd.streamCam(args.host, args.port, args.capture_bytes) 
