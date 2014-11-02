swanntools
==========

Capture tools for the Swann DVR8-2600 DVR

Do you own a Swann DVR8-2600? Do you hate the finicky app and nauseating browser plugin based methods of viewing your camera streams? Well I did and I decided to do something about it. The result is swanndump.py

swanndump.py takes your camera parameters and dumps a raw .h264 stream to stdout. 

There are basically two different feeds on these boxes; the mobile stream and the media stream. The mobile stream outputs a 320x240 feed and the media stream outputs a 704x480 feed.

The way they are initiated varies greatly, so there are slightly different parameters for each.

Note: This requires firmware version: V2.6.0-20130213. If you don't have this yet, go here and update your box: http://www.swann.com/us/firmware-2600. If you don't, your box is essentially passwordless! See here for more info: http://console-cowboys.blogspot.ca/2013/01/swann-song-dvr-insecurity.html. Again, if you don't update your firmware ANYONE can log in and do whatever they want with your box!

The mobile stream:
-----------------

To initiate a mobile stream you will need to issue a command similar to this:
python swanndump.py --host MYHOST.swanndvr.net --port 18004 --cam 5 --method mobile --user admin --password MYPASS

That will start streaming data directly to stdout (if you got the parameters correct)

The media stream:
----------------

The media stream is a bit more complicated. Unfortunately Swann decided to encrypt the login information on the media stream. And without knowing how exactly they did it I have no way of duplicating their login packet short of packet capturing. 

So in order to view the media stream, we'll need to capture the login packet. If you want to simply try this out without this step, I've included data/login.hex. It it the login packet for the password '000000'.

Here's what I did to generate the login packet:

- Installed Wireshark
- Ensured my Safari browser was completely shut down
- Ran the following command: tshark -c 25 -f 'host MYHOST.swanndvr.net and port 9000' -i en1 -T fields -e data | tr -s '\n' > mycap.hex
- Opened Safari and logged in to my DVR
- Ensured that the tshark command exited successfully. Verified that mcap.hex has a bunch of hex data in it. The line about 10 00 00 00 00 00 00 00 is the one we are interested in.
- Issued the following command: sed '3q;d' mycap.hex | tr -d '\n' > data/login.hex

That command essentially grabs the 3rd line of the mycap.hex file and sticks it in a new file, data/login.hex. So if you followed along you should now have a valid login packet.

Try the following command:

python swanndump.py --host MYHOST.swanndvr.net --port 9000 --cam 3 --method media --login_packet data/login.hex

If it works, then you should see a big stream of h264 data in your stdout...
