import PicoBorgRev
import time
import sys
import threading
import SocketServer
import picamera
import picamera.array
import cv2
import datetime
import os
import pygame
import subprocess
import random
import logging


def blinkcall():
	subprocess.call('../8x8matrixscroll/matrix 1 112 5 &', shell=True) 


def drawEyes(disp, img, delay):

  for y in range(0, 8):
    position = 128
    for x in range(0, 8):
      value = position & img[y]
      if (value > 0):
        value = 1
      disp.set_pixel(x, y, value )
      disp.write_display()
      position = position >> 1
  time.sleep(delay)






def talk(lineToSay):
    os.system('espeak -a20 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav ""%s"" && sudo aplay -q out.wav' % lineToSay)	


class Blinker(threading.Thread):
    def __init__(self):
        super(Blinker,self).__init__()
        self.event = threading.Event()
        self.terminated = False
        logging.debug('Starting Blinker')
        self.start()

    def run(self):
        while not self.terminated:
            #if self.event.wait(5):
                try:
                    logging.debug('BLINK!')
                    time.sleep(20)
                    subprocess.call('../8x8matrixscroll/matrix 1 113 5 &', shell=True) 
                    #print("BLINK!")
                finally:
                    # Reset the event
                    self.event.clear()

class Serverer(threading.Thread):
    def __init__(self):
        super(Serverer,self).__init__()
        self.event = threading.Event()
        self.terminated = False
        logging.debug('Starting Serverer')
        self.start()

    def run(self):
        while not self.terminated:
            #if self.event.wait(5):
                try:
                    #logging.debug('BLINK!')
                    #time.sleep(10)
                    httpServer.serve_forever(poll_interval=0.5)
                    #httpServer.handle_request()
                    #subprocess.call('../8x8matrixscroll/matrix 1 113 5 &', shell=True) 
                    #print("BLINK!")
                finally:
                    # Reset the event
                    self.event.clear()





# Timeout thread
class Watchdog(threading.Thread):
    def __init__(self):
        super(Watchdog, self).__init__()
        self.event = threading.Event()
        self.terminated = False
        logging.debug('Starting Watchdog')
        self.start()
        self.timestamp = time.time()

    def run(self):
        timedOut = True
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for a network event to be flagged for up to one second
            if timedOut:
                if self.event.wait(1):
                    # Connection
                    print 'Reconnected...'
                    timedOut = False
                    self.event.clear()
            else:
                if self.event.wait(1):
                    self.event.clear()
                else:
                    # Timed out
                    print 'Timed out...'
                    timedOut = True
                  

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        logging.debug('Starting StreamProcessor')
        self.start()
        self.begin = 0

    def run(self):
        global lastFrame
        global lockFrame
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and save globally
                    self.stream.seek(0)
                    flippedArray = cv2.flip(self.stream.array, -1) # Flips X and Y
                    retval, thisFrame = cv2.imencode('.jpg', flippedArray)
                    del flippedArray
                    lockFrame.acquire()
                    lastFrame = thisFrame
                    lockFrame.release()
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print 'Start the stream using the video port'
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print 'Terminating camera processing...'
        processor.terminated = True
        processor.join()
        print 'Processing terminated.'

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Class used to implement the web server
class WebServer(SocketServer.BaseRequestHandler):
    def handle(self):
        global lastFrame
        global watchdog
        # Get the HTTP request data
        reqData = self.request.recv(1024).strip()
        reqData = reqData.split('\n')
        # Get the URL requested
        getPath = ''
        for line in reqData:
            if line.startswith('GET'):
                parts = line.split(' ')
                getPath = parts[1]
                break
        watchdog.event.set()
        if getPath.startswith('/cam.jpg'):
            # Camera snapshot
            lockFrame.acquire()
            sendFrame = lastFrame
            lockFrame.release()
            if sendFrame != None:
                self.send(sendFrame.tostring())

        elif getPath.startswith('/photo'):
            # Save camera photo
            lockFrame.acquire()
            captureFrame = lastFrame
            lockFrame.release()
            httpText = '<html><body><center>'
            if captureFrame != None:
                photoName = '%s/Photo %s.jpg' % (photoDirectory, datetime.datetime.utcnow())
                try:
                    photoFile = open(photoName, 'wb')
                    photoFile.write(captureFrame)
                    photoFile.close()
                    httpText += 'Photo saved to %s' % (photoName)
                except:
                    httpText += 'Failed to take photo!'
            else:
                httpText += 'Failed to take photo!'
            httpText += '</center></body></html>'
            self.send(httpText)
        elif getPath == '/':
            # Main page, click buttons to move and to stop
            httpText = '<html>\n'
            httpText += '<title>Rainer the Robot Camera Stream</title>'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function Drive(left, right) {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' var slider = document.getElementById("speed");\n'
            httpText += ' left *= speed.value / 100.0;'
            httpText += ' right *= speed.value / 100.0;'
            httpText += ' iframe.src = "/set/" + left + "/" + right;\n'
            httpText += '}\n'
            httpText += 'function Off() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/off";\n'
            httpText += '}\n'
            httpText += 'function Photo() {\n'
            httpText += ' var iframe = document.getElementById("setDrive");\n'
            httpText += ' iframe.src = "/photo";\n'
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body>\n'
            httpText += '<iframe src="/stream" width="100%" height="500" frameborder="0"></iframe>\n'
            httpText += '<iframe id="setDrive" src="/off" width="100%" height="50" frameborder="0"></iframe>\n'
            httpText += '<center>\n'
            #httpText += '<button onclick="Drive(-1,1)" style="width:200px;height:100px;"><b>Spin Left</b></button>\n'
            #httpText += '<button onclick="Drive(1,1)" style="width:200px;height:100px;"><b>Forward</b></button>\n'
            #httpText += '<button onclick="Drive(1,-1)" style="width:200px;height:100px;"><b>Spin Right</b></button>\n'
            #httpText += '<br /><br />\n'
            #httpText += '<button onclick="Drive(0,1)" style="width:200px;height:100px;"><b>Turn Left</b></button>\n'
            #httpText += '<button onclick="Drive(-1,-1)" style="width:200px;height:100px;"><b>Reverse</b></button>\n'
            #httpText += '<button onclick="Drive(1,0)" style="width:200px;height:100px;"><b>Turn Right</b></button>\n'
            #httpText += '<br /><br />\n'
            #httpText += '<button onclick="Off()" style="width:200px;height:100px;"><b>Stop</b></button>\n'
            #httpText += '<br /><br />\n'
            httpText += '<button onclick="Photo()" style="width:640px;height:100px;"><b>Save Photo</b></button>\n'
            httpText += '<br /><br />\n'
            #httpText += '<input id="speed" type="range" min="0" max="100" value="100" style="width:600px" />\n'
            httpText += '</center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
        elif getPath == '/stream':
            # Streaming frame, set a delayed refresh
            displayDelay = int(1000 / displayRate)
            httpText = '<html>\n'
            httpText += '<head>\n'
            httpText += '<script language="JavaScript"><!--\n'
            httpText += 'function refreshImage() {\n'
            httpText += ' if (!document.images) return;\n'
            httpText += ' document.images["rpicam"].src = "cam.jpg?" + Math.random();\n'
            httpText += ' setTimeout("refreshImage()", %d);\n' % (displayDelay)
            httpText += '}\n'
            httpText += '//--></script>\n'
            httpText += '</head>\n'
            httpText += '<body onLoad="setTimeout(\'refreshImage()\', %d)">\n' % (displayDelay)
            httpText += '<center><img src="/cam.jpg" style="width:640;height:480;" name="rpicam" /></center>\n'
            httpText += '</body>\n'
            httpText += '</html>\n'
            self.send(httpText)
        else:
            # Unexpected page
            self.send('Path : "%s"' % (getPath))

    def send(self, content):
        self.request.sendall('HTTP/1.0 200 OK\n\n%s' % (content))




