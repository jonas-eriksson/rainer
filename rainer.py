#!/usr/bin/env python
# coding: Latin-1


# Creates a web-page interface for DiddyBorg

# Import library functions we need
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
import tty
import termios
import stravalib #sudo pip install stravalib
import math

from PIL import Image
from PIL import ImageDraw
from Adafruit_LED_Backpack import Matrix8x8
from Adafruit_PWM_Servo_Driver import PWM
from RpiLcdBackpack import AdafruitLcd
#import include
import blinkt

logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )



### Init Strava
client = stravalib.client.Client(access_token="c28df4f8b86b35411424c4c46ae04b8b52a59d44") # replace this with your Strava API key



### Yearly km goal for Strava
goal = 5000.0


# Settings for the web-page
webPort = 1983                          # Port number for the web-page, 80 is what web-pages normally use (OBS! Port below 1024 requires sudo)
imageWidth = 240                        # Width of the captured image in pixels
imageHeight = 192                       # Height of the captured image in pixels
frameRate = 25                          # Number of images to capture per second
displayRate = 25                         # Number of images to request per second
photoDirectory = '/home/pi'             # Directory to save photos to

# Global values
global lastFrame
global lockFrame
global camera
global processor
global running
global watchdog
running = True

# Settings for the joystick
leftAxisUpDown = 1                          # Joystick axis to read for up / down position
leftAxisUpDownInverted = False              # Set this to True if up and down appear to be swapped
leftAxisLeftRight = 0                       # Joystick axis to read for left / right position
leftAxisLeftRightInverted = True           # Set this to True if left and right appear to be swapped
buttonResetEpo = 3                      # Joystick button number to perform an EPO reset (Start)
buttonSlow = 8                          # Joystick button number for driving slowly whilst held (L2)
slowFactor = 0.5                        # Speed to slow to when the drive slowly button is held, e.g. 0.5 would be half speed
buttonFastTurn = 9                      # Joystick button number for turning fast (R2)
buttonSelect = 0                        # Operating mode select (Select)
interval = 0.00                         # Time between updates in seconds, smaller responds faster but uses more processor time

buttonArm = 10                          # Hold to control arm (L1)
rightAxisUpDown = 3
rightAxisLeftRight = 2 

buttonHead = 11                         # Hold to control head pan/tilt (R1)
buttonTriangle = 12
buttonCircle = 13
buttonCross = 14
buttonSquare = 15

buttonDL = 7
buttonDR = 5
buttonDU = 4
buttonDD = 6


autonomous = False

pyVideo = False

enableJoy = False

eyenimator_cycle = False
eyeAnim = True

# Power settings
voltageIn = 12.0                        # Total battery voltage to the PicoBorg Reverse
voltageOut = 12.0     

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)


# Eye images
eyeopen=[0x3C, 0x7E, 0xE7, 0xC3, 0xC3, 0xE7, 0x7E, 0x3C]
eyesleep=[0x00, 0x00, 0x00, 0x00, 0x81, 0x7E, 0x00, 0x00]
heart2=[0b00000000, 0b01100110, 0b11111111, 0b11111111, 0b01111110, 0b00111100, 0b00011000, 0b00000000]



# Re-direct our output to standard error, we need to ignore standard out to hide some nasty print statements from pygame
sys.stdout = sys.stderr



def sortby(item):
    return item.start_date

def getstravadistance():
    global totaldistance
    totaldistance = 0
    activitiesthisyear = client.get_activities(after="2017-01-01T00:00:00Z", limit=500) # Download all activities this year

    for activity in activitiesthisyear:
        if activity.type=="Ride":
        #print(activity.type)
            totaldistance += float(stravalib.unithelper.kilometers(activity.distance)) #add up the total distance







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
    os.system('espeak -a20 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav ""%s"" && aplay -q out.wav' % lineToSay)    


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
                    time.sleep(random.randrange(5, 20))
                    if (eyenimator_cycle == False):
                        subprocess.call('../8x8matrixscroll/matrix 1 113 5 &', shell=True) 
                    #print("BLINK!")
                finally:
                    # Reset the event
                    self.event.clear()


#cmd = ["espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav \"" + lines[phrasenum] + "\" && aplay -q out.wav"]

class Eyenimator(threading.Thread):
    def __init__(self):
        super(Eyenimator,self).__init__()
        self.event = threading.Event()
        self.terminated = False
        logging.debug('Starting Eyenimator')
        self.start()

    def run(self):
        while not self.terminated:
            #if self.event.wait(5):
                try:
                    
                    #logging.debug('BLINK!')
                    time.sleep(random.randrange(7, 15))
                    eyenimator_cycle = True
                    eye_cmd = ["../8x8matrixscroll/matrix 1 113 " + str(random.randrange(10,19)) + " &"]
                    #print(eye_cmd)
                    subprocess.call(eye_cmd, shell=True) 
                    time.sleep(random.randrange(2,4))
                    subprocess.call('../8x8matrixscroll/matrix 1 113 2 &', shell=True)
                    eyenimator_cycle = False
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


#======================================================================
# Reading single character by forcing stdin to raw mode
import sys
import tty
import termios

def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ch == '0x03':
        raise KeyboardInterrupt
    return ch

def readkey(getchar_fn=None):
    getchar = getchar_fn or readchar
    c1 = getchar()
    if ord(c1) != 0x1b:
        return c1
    c2 = getchar()
    if ord(c2) != 0x5b:
        return c1
    c3 = getchar()
    return chr(0x10 + ord(c3) - 65)  # 16=Up, 17=Down, 18=Right, 19=Left arrows

# End of single character reading
#======================================================================




################################################################################

###                     RAINER THE ROBOT PROGRAM START                       ###

################################################################################
blinkt.set_clear_on_exit(True)
blinkt.set_pixel(0,255, 0, 0)
blinkt.show()

getstravadistance()

lcd = AdafruitLcd()
lcd.backlight(True)
lcd.blink(False)
lcd.cursor(False)
lcd.clear()
lcd.message("RAINER THE ROBOT")

time.sleep(1)

lcd.setCursor(0,1)
lcd.message(" Initializing.. ")


blinkt.set_pixel(1,255, 0, 0)
blinkt.show()



print '----------------------------'
print '----- RAINER THE ROBOT -----'
print '----------------------------'


print 'Initializing eyes..'
# Create display instance on default I2C address (0x70) and bus number.
display = Matrix8x8.Matrix8x8()

# Initialize the display. Must be called once before using the display.
#display.begin()

# Clear the display buffer.
#display.clear()
# Draw the buffer to the display hardware.
#display.write_display()

print 'Initializing head servos..'
# Initialise the PWM device using the default address
pwm = PWM(0x40)
# Set frequency to 60 Hz
pwm.setPWMFreq(60)

#for z in range(0, 4095,20):
#   pwm.setPWM(4, 0, z) # set status led red
#   time.sleep(0.01)

#pwm.setPWM(4, 1, 0) # set status led red

# Set led matrices to sleep mode at the beginning
#drawEyes(display,eyesleep,0.1)
subprocess.call('../8x8matrixscroll/matrix 1 113 0', shell=True)
time.sleep(0.5)

blinkt.set_pixel(2,255, 0, 0)
blinkt.show()






servoMin = 150  # Min pulse length out of 4096
servoMax = 600  # Max pulse length out of 4096
servoMid = (servoMax-servoMin)/2+servoMin

elbowUDMin = 240
elbowUDMax = 600
elbowUDMid = (elbowUDMax-elbowUDMin)/2+elbowUDMin
elbowUDStart = 540

elbowIOStart = 150
elbowIOMin = 120
elbowIOMax = 600

handOCStart = 400
handOCMin = 230    
handOCMax = 440

wristStart = 500
wristMin = 275
wristMax = 600

# Head pan
#pwm.setPWM(0, 0, servoMid)




#blinktimer = threading.Timer(10, blinkcall)






print 'Initializing motor control..'
# Setup the PicoBorg Reverse
PBR = PicoBorgRev.PicoBorgRev()
#PBR.i2cAddress = 0x44                  # Uncomment and change the value if you have changed the board address
PBR.Init()
if not PBR.foundChip:
    boards = PicoBorgRev.ScanForPicoBorgReverse()
    if len(boards) == 0:
        print 'No PicoBorg Reverse found, check you are attached :)'
    else:
        print 'No PicoBorg Reverse at address %02X, but we did find boards:' % (PBR.i2cAddress)
        for board in boards:
            print '    %02X (%d)' % (board, board)
        print 'If you need to change the I²C address change the setup line so it is correct, e.g.'
        print 'PBR.i2cAddress = 0x%02X' % (boards[0])
    sys.exit()
#PBR.SetEpoIgnore(True)                 # Uncomment to disable EPO latch, needed if you do not have a switch / jumper
# Ensure the communications failsafe has been enabled!
failsafe = False
for i in range(5):
    PBR.SetCommsFailsafe(True)
    failsafe = PBR.GetCommsFailsafe()
    if failsafe:
        break
if not failsafe:
    print 'Board %02X failed to report in failsafe mode!' % (PBR.i2cAddress)
    sys.exit()
PBR.ResetEpo()


blinkt.set_pixel(3,255, 0, 0)
blinkt.show()




#os.system('espeak -a80 -k1 -g5 -p10 -s160 -v swedish -w out.wav "Jag ska vakna nu." && aplay -q out.wav')


# Setup pygame and wait for the joystick to become available
PBR.MotorsOff()
os.environ["SDL_VIDEODRIVER"] = "dummy" # Removes the need to have a GUI window
blinkt.show()
pygame.init()
#blinkt.show()
pygame.mixer.quit()
blinkt.show()
print('kissa2')
pygame.display.init()
print('kissa3')
pygame.display.set_mode((1,1))
print('kissa4')
blinkt.set_pixel(4,255, 0, 0)
if enableJoy == True:

    print 'Waiting for joystick... (press CTRL+C to skip)'
    while True:
        try:
            try:
                pygame.joystick.init()
                # Attempt to setup the joystick
                if pygame.joystick.get_count() < 1:
                    # No joystick attached, toggle the LED
                    PBR.SetLed(not PBR.GetLed())
                    pygame.joystick.quit()
                    time.sleep(0.5)
                else:
                    # We have a joystick, attempt to initialise it!
                    joystick = pygame.joystick.Joystick(0)
                    break
            except pygame.error:
                # Failed to connect to the joystick, toggle the LED
                PBR.SetLed(not PBR.GetLed())
                pygame.joystick.quit()
                time.sleep(0.5)
        except KeyboardInterrupt:
            # CTRL+C exit, give up
            print '\nUser aborted'
            PBR.SetLed(True)
            sys.exit()
    print 'Joystick found'
    joystick.init()
    PBR.SetLed(False)


print('koira')
## Read lines from file
lines = [line.strip('\n') for line in open('lines_se.txt')]
logging.debug('Phrases in text file: %d' % len(lines))





# Wake up sequence - open eyes and raise head (tilt)

time.sleep(0.5)
#os.system('./matrix.sh')
#os.system(' ../8x8matrixscroll/matrix 1 112 2')
#call("ls", "-la")
#drawEyes(display,eyeopen,0.0)
blinkt.set_pixel(5,255, 0, 0)
blinkt.show()

subprocess.call('../8x8matrixscroll/matrix 1 113 7 &', shell=True)
time.sleep(0.5)
subprocess.call('../8x8matrixscroll/matrix 1 113 1 &', shell=True)
time.sleep(0.5)
  
pwm.setPWM(1, 0, 500) # tilt servovo

blinkt.set_pixel(6,255, 0, 0)
blinkt.show()
#subprocess.call(['espeak', '-a20', '-k1', '-g5', '-p10', '-s160', '-v', 'en-scottish', '-w', 'out.wav', '"Hello!"', '&&', 'sudo', 'aplay', '-q', 'out.wav'])
#os.system('espeak -a20 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Hello!" && sudo aplay -q out.wav')    
time.sleep(1.0)
#talk("Where is my burrito?")

#blinktimer.start()




if pyVideo:

    # Create the image buffer frame
    lastFrame = None
    lockFrame = threading.Lock()

    # Startup sequence
    print 'Setup camera'
    camera = picamera.PiCamera()
    camera.resolution = (imageWidth, imageHeight)
    camera.framerate = frameRate

    print 'Setup the stream processing thread'
    processor = StreamProcessor()

    print 'Wait ...'
    time.sleep(2)
    captureThread = ImageCapture()

    print 'Setup the watchdog'
    watchdog = Watchdog()


    #### Added to get rid of "address in use" error
    SocketServer.TCPServer.allow_reuse_address = True

    # Run the web server until we are told to close
    httpServer = SocketServer.TCPServer(("0.0.0.0", webPort), WebServer)

    serverer = Serverer()


#print 'Starting Blinker'

## Start eye animators

if eyeAnim:
    blinker = Blinker()
    eyenimator = Eyenimator()


#time.sleep(3)
#pwm.setPWM(4, 4095, 0) # clear red status led
#time.sleep(0.5)
#pwm.setPWM(3, 1, 0) # set green status led
#time.sleep(0.5)
#pwm.setPWM(3, 4095, 0) # clear green status led
#time.sleep(0.5)
#pwm.setPWM(2, 1, 0) # set blue status led
#time.sleep(0.5)
#pwm.setPWM(3, 1, 0) # set green status led
#time.sleep(0.5)
#pwm.setPWM(4, 1, 0) # set red status led

elbowUDVal = elbowUDStart
elbowIOVal = elbowIOStart
handVal = handOCStart
wristVal = wristStart
blinkt.set_pixel(7,255, 0, 0)
blinkt.show()
pwm.setPWM(5, 0, int(elbowUDVal))
time.sleep(0.5)
pwm.setPWM(2, 0, int(elbowIOVal))
time.sleep(0.5)
pwm.setPWM(7, 0, int(handVal))
time.sleep(0.5)
pwm.setPWM(6, 0, int(wristVal))
time.sleep(0.5)

blinkt.clear()
blinkt.show()
time.sleep(0.1)


blinkt.set_all(0, 255, 0)
blinkt.show()
time.sleep(1)


for i in range (255,0,-2):
    blinkt.set_all(0, i, 0)
    blinkt.show()
    time.sleep(0.005)
#time.sleep(3)

#lcd.clear()
lcd.setCursor(0,1)
lcd.message("     Ready!     ")
blinkt.clear()
blinkt.show()

try:
    if pyVideo:
        print 'Press CTRL+C to terminate the web-server'
    headPan = 0
    headTilt = 0
    driveLeft = 0.0
    driveRight = 0.0
    driveLeftD = 0.0
    driveRightD = 0.0 
    oldLeftD = 0.0
    oldRightD = 0.0        
    running = True
    hadEvent = False
    hadJoyEvent = False
    circleReleased = False
    triangleReleased = False
    upDown = 0.0
    leftRight = 0.0
    # Loop indefinitely
    while running:
        #print 'httpserver'
        #httpServer.handle_request()
        # Get the latest events from the system
        hadEvent = False
        circleReleased = False
        triangleReleased = False
        phrasenum = random.randrange(len(lines))
        events = pygame.event.get()
        #print 'post event get'
        # Handle each event individually
        for event in events:
            if event.type == pygame.QUIT:
                # User exit
                running = False
            elif event.type == pygame.KEYDOWN:
                key = event.key
                logging.debug("Button {} on".format(key))
                # A button on the joystick just got pushed down

                if key == pygame.K_ESCAPE:
                    running = False

                if key == pygame.K_l:
                    # Construct a line to call
                    cmd = ["espeak -a60 -k1 -g5 -p10 -s160 -v swedish -w out.wav \"" + lines[phrasenum] + "\" && aplay -q out.wav"]
                    #print(cmd)
                    subprocess.call(cmd, shell=True)
                    hadEvent = True

                if key == pygame.K_j:
                    # Construct a line to call
                    os.system('espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav "Lotta. Du får köpa en lederjacka om du vill." && aplay -q out.wav')
                    #print(cmd)
                    #subprocess.call(cmd, shell=True)
                    hadEvent = True

                if key == pygame.K_k:
                    # Construct a line to call
                    os.system('espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav "Lotta. Vill du ha kaffe nu?." && aplay -q out.wav')
                    #print(cmd)
                    #subprocess.call(cmd, shell=True)
                    hadEvent = True

                if key == pygame.K_c:
                    # Construct a line to call
                    cmd = ["espeak -a60 -k1 -g5 -p10 -s160 -v swedish -w out.wav \"" "Du har cyclat " + str(totaldistance) + " kilometer och har " + str(goal-totaldistance) + " kilometer kvar. Latbanan." "\" && aplay -q out.wav"]
                    #print(cmd)
                    subprocess.call(cmd, shell=True)
                    hadEvent = True



                if key == pygame.K_TAB:
                    if (autonomous):
                        lcd.setCursor(0,1)
                        lcd.message("Mode: manual    ")
                        autonomous = False
                    else:
                        lcd.setCursor(0,1)
                        lcd.message("Mode: autonomous")
                        autonomous = True
                                                        
                    hadEvent = True
                if key == pygame.K_r:
                    #print 'Square pressed! (not used)'
                    pwm.softwareReset()
                    pwm = PWM(0x40)
                    # Set frequency to 60 Hz
                    pwm.setPWMFreq(60)
                    os.system('espeak -a40 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Hello, Lotta! You look wonderful today!" && aplay -q out.wav')
                    #os.system('echo "Hello, Lotta!" | sudo festival --tts')
                    hadEvent = True
                if key == pygame.K_s:
                    subprocess.call('../8x8matrixscroll/matrix 1 113 22 &', shell=True)
                    os.system('espeak -a40 -k1 -g5 -p10 -s160 -v finnish -w out.wav "Oi maammee Suoo mii synnyinmAA! Sooi saana kuultaai neen! Eei laakso aa aa ee ei kukkUu laa. Ei veettä raa an taa aa rakkaam paa. Kuin koo ti maa tää poh joi neen. Maa kallis roo boot" && aplay -q out.wav')
                    subprocess.call('../8x8matrixscroll/matrix 1 113 23 &', shell=True) 
                    time.sleep(3.5)
                    os.system('espeak -a40 -k1 -g5 -p10 -s120 -v finnish -w out.wav "köh köh" && aplay -q out.wav')
                    time.sleep(0.5)
                    subprocess.call('../8x8matrixscroll/matrix 1 113 22 &', shell=True)
                    os.system('espeak -a40 -k1 -g5 -p10 -s120 -v finnish -w out.wav "Ii. siii. Eeeen!" && aplay -q out.wav')
                    subprocess.call('../8x8matrixscroll/matrix 1 113 24 &', shell=True)
                    #os.system('echo "Hello, Lotta!" | sudo festival --tts')
                    hadEvent = True

                if key == pygame.K_UP:
                    print 'Key up pressed!'
                    driveRightD = 0.75 #PBR.SetMotor1(0.75)
                    driveLeftD = 0.75 #PBR.SetMotor2(-0.75)            
                    hadEvent = True
            
                if key == pygame.K_DOWN:
                    print 'Key down pressed!'
                    driveRightD = -0.75 #PBR.SetMotor1(-0.75)
                    driveLeftD = -0.75 #PBR.SetMotor2(0.75)            
                    hadEvent = True

                if key == pygame.K_LEFT:
                    print 'Key left pressed!'
                    oldRightD = driveRightD
                    oldLeftD = driveLeftD
                    subprocess.call('../8x8matrixscroll/matrix 1 113 4 &', shell=True)
                    driveRightD = -0.75 #PBR.SetMotor1(-0.75)
                    driveLeftD = 0.75 #PBR.SetMotor2(-0.75)            
                    hadEvent = True

                if key == pygame.K_RIGHT:
                    print 'Key right pressed!'
                    oldRightD = driveRightD
                    oldLeftD = driveLeftD
                    subprocess.call('../8x8matrixscroll/matrix 1 113 3 &', shell=True)
                    driveRightD = 0.75 #PBR.SetMotor1(0.75)
                    driveLeftD = -0.75 #PBR.SetMotor2(0.75)            
                    hadEvent = True

            elif event.type == pygame.KEYUP:
                key = event.key
                logging.debug("Button {} off".format(key))
                if key == pygame.K_UP:
                    print 'Key up released!'
                    driveRightD = 0 #PBR.SetMotor1(0)
                    driveLeftD = 0 #PBR.SetMotor2(0)            
                    hadEvent = True

                elif key == pygame.K_DOWN:
                    print 'Key down released!'
                    driveRightD = 0 #PBR.SetMotor1(0)
                    driveLeftD = 0 #PBR.SetMotor2(0)            
                    hadEvent = True

                elif key == pygame.K_RIGHT:
                    print 'Key right released!'
                    subprocess.call('../8x8matrixscroll/matrix 1 113 2 &', shell=True)
                    driveRightD = oldRightD #PBR.SetMotor1(0)
                    driveLeftD = oldLeftD #PBR.SetMotor2(0)            
                    hadEvent = True
                
                elif key == pygame.K_LEFT:
                    print 'Key left released!'
                    subprocess.call('../8x8matrixscroll/matrix 1 113 2 &', shell=True)
                    driveRightD = oldRightD #PBR.SetMotor1(0)
                    driveLeftD = oldLeftD #PBR.SetMotor2(0)            
                    hadEvent = True

            elif (event.type == pygame.JOYBUTTONDOWN):
                button = event.button
                logging.debug("Button {} on".format(button))
                # A button on the joystick just got pushed down

                if joystick.get_button(buttonCircle):
                    #print 'Circle pressed!'
                    # Construct a line to call
                    cmd = ["espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav \"" + lines[phrasenum] + "\" && aplay -q out.wav"]
                    #print(cmd)
                    subprocess.call(cmd, shell=True)
                    hadJoyEvent = True



                if joystick.get_button(buttonSelect):
                    if (autonomous):
                        lcd.setCursor(0,1)
                        lcd.message("Mode: manual    ")
                        autonomous = False
                    else:
                        lcd.setCursor(0,1)
                        lcd.message("Mode: autonomous")
                        autonomous = True
                                    
                    #print 'Triangle pressed!'
                    #os.system('/home/pi/weather-2.2/weather --setpath=/home/pi/weather-2.2 -m efhf | sudo flite -voice rms')                    
                    hadJoyEvent = True
                if joystick.get_button(buttonTriangle):
                    #print 'Triangle pressed!'
                    #os.system('/home/pi/weather-2.2/weather --setpath=/home/pi/weather-2.2 -m efhf | sudo flite -voice rms')                    
                    hadJoyEvent = True
                if joystick.get_button(buttonSquare):
                    #print 'Square pressed! (not used)'
                    pwm.softwareReset()
                    pwm = PWM(0x40)
                    # Set frequency to 60 Hz
                    pwm.setPWMFreq(60)
                    #os.system('espeak -a40 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Hello, Lotta! You look wonderful today!" && sudo aplay -q out.wav')
                    #os.system('echo "Hello, Lotta!" | sudo festival --tts')
                    hadJoyEvent = True
                if joystick.get_button(buttonCross):
                    #print 'Cross pressed! (not used)'
                    #os.system('espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav "Lotta! Här har du en kex!" && sudo aplay -q out.wav')    
                    subprocess.call('../8x8matrixscroll/matrix 1 113 9 &', shell=True)
                    os.system('espeak -a40 -k1 -g5 -p10 -s140 -v finnish -w out.wav "Paljon onnea, Susanna!" && aplay -q out.wav')    
                    subprocess.call('../8x8matrixscroll/matrix 1 113 5 &', shell=True)                
                    hadJoyEvent = True
                if joystick.get_button(buttonDU):
                    print 'D pad up pressed!'
                    driveRightD = 0.75 #PBR.SetMotor1(0.75)
                    driveLeftD = 0.75 #PBR.SetMotor2(-0.75)            
                    hadJoyEvent = True
            
                if joystick.get_button(buttonDD):
                    print 'D pad down pressed!'
                    driveRightD = -0.75 #PBR.SetMotor1(-0.75)
                    driveLeftD = -0.75 #PBR.SetMotor2(0.75)            
                    hadJoyEvent = True

                if joystick.get_button(buttonDL):
                    print 'D pad left pressed!'
                    oldRightD = driveRightD
                    oldLeftD = driveLeftD
                    subprocess.call('../8x8matrixscroll/matrix 1 113 4 &', shell=True)
                    driveRightD = -0.75 #PBR.SetMotor1(-0.75)
                    driveLeftD = 0.75 #PBR.SetMotor2(-0.75)            
                    hadJoyEvent = True

                if joystick.get_button(buttonDR):
                    print 'D pad right pressed!'
                    oldRightD = driveRightD
                    oldLeftD = driveLeftD
                    subprocess.call('../8x8matrixscroll/matrix 1 113 3 &', shell=True)
                    driveRightD = 0.75 #PBR.SetMotor1(0.75)
                    driveLeftD = -0.75 #PBR.SetMotor2(0.75)            
                    hadJoyEvent = True


            elif event.type == pygame.JOYBUTTONUP:
                button = event.button
                logging.debug("Button {} off".format(button))
                if button == buttonDU:
                    print 'D pad up released!'
                    driveRightD = 0 #PBR.SetMotor1(0)
                    driveLeftD = 0 #PBR.SetMotor2(0)            
                    hadJoyEvent = True

                elif button == buttonDD:
                    print 'D pad down released!'
                    driveRightD = 0 #PBR.SetMotor1(0)
                    driveLeftD = 0 #PBR.SetMotor2(0)            
                    hadJoyEvent = True

                elif button == buttonDR:
                    print 'D pad down released!'
                    subprocess.call('../8x8matrixscroll/matrix 1 113 2 &', shell=True)
                    driveRightD = oldRightD #PBR.SetMotor1(0)
                    driveLeftD = oldLeftD #PBR.SetMotor2(0)            
                    hadJoyEvent = True
                
                elif button == buttonDL:
                    print 'D pad down released!'
                    subprocess.call('../8x8matrixscroll/matrix 1 113 2 &', shell=True)
                    driveRightD = oldRightD #PBR.SetMotor1(0)
                    driveLeftD = oldLeftD #PBR.SetMotor2(0)            
                    hadJoyEvent = True

        
            elif event.type == pygame.JOYAXISMOTION:
                # A joystick has been moved
                hadJoyEvent = True
            if hadJoyEvent:
                # Read axis positions (-1 to +1)
                if leftAxisUpDownInverted:
                    upDown = -joystick.get_axis(leftAxisUpDown)
                   # print 'UP/DOWN triggered!\n'
                else:
                    upDown = joystick.get_axis(leftAxisUpDown)
                    #print 'UP/DOWN value: %f' % (upDown)
                if leftAxisLeftRightInverted:
                    leftRight = -joystick.get_axis(leftAxisLeftRight)
                    #print 'L/R triggered!\n'
                else:
                    leftRight = joystick.get_axis(leftAxisLeftRight)
                    #print 'L/R value: %f' % (leftRight)
                # Apply steering speeds
                if not joystick.get_button(buttonFastTurn):
                    #print 'FAST pressed'
                    leftRight *= 0.5
                # Determine the drive power levels
                axisWrist = joystick.get_axis(rightAxisUpDown)
                axisElbowIO = -joystick.get_axis(leftAxisLeftRight)
                axisElbowUD = joystick.get_axis(leftAxisUpDown)
                axisHand = -joystick.get_axis(rightAxisLeftRight)
                driveLeft = -upDown
                driveRight = -upDown
                headPan = (leftRight * (servoMid+75) + servoMax-servoMid+servoMin)
                headTilt = (upDown/2 * (servoMid+75) + 500)
            
                elbowUDVal = elbowUDVal + axisElbowUD*5 #(axisElbowUD/2 * (elbowUDMax+75) + 540) # + elbowUDMax-elbowUDMid+elbowUDMin)
                if (elbowUDVal > elbowUDMax):
                    elbowUDVal = elbowUDMax
                elif (elbowUDVal < elbowUDMin):
                    elbowUDVal = elbowUDMin
                elbowIOVal = elbowIOVal + axisElbowIO*2 #(axisElbowIO * (servoMid+75) + servoMax-servoMid+servoMin)
                if (elbowIOVal > elbowIOMax):
                    elbowIOVal = elbowIOMax
                elif (elbowIOVal < elbowIOMin):
                    elbowIOVal = elbowIOMin
                #print 'axisHand: %f' % (axisHand)
                handVal = handVal - axisHand*5 #(axisHand * (servoMid+75))
                #print 'handval_pre: %f' % (handVal)
                if (handVal > handOCMax):
                    handVal = handOCMax
                elif (handVal < handOCMin):
                    handVal = handOCMin
                wristVal = wristVal + axisWrist * 5 #(axisWrist * (servoMid+75) + 200)
                if (wristVal > wristMax):
                    wristVal = wristMax
                elif (wristVal < wristMin):
                    wristVal = wristMin

                #elbowUDMin = 140
                #elbowUDMax = 540
                #elbowUDMid = (elbowUDMax-elbowUDMin)/2+elbowUDMin

                if leftRight < -0.05:
                    # Turning left
                    driveLeft *= 1.0 + (2.0 * leftRight)
                    #subprocess.call('../8x8matrixscroll/matrix 1 112 3 &', shell=True)
                    #headPan = servoMid + (servoMid * leftRight*2)
                elif leftRight > 0.05:
                    # Turning right
                    driveRight *= 1.0 - (2.0 * leftRight)
                    #subprocess.call('../8x8matrixscroll/matrix 1 112 4 &', shell=True)
                    #headPan = servoMid - (servoMid * leftRight*2) 
                # Check for button presses
                if joystick.get_button(buttonResetEpo):
                    #print 'RESET pressed'
                    PBR.ResetEpo()
                if joystick.get_button(buttonSlow):
                    #print 'SLOW pressed'
                    driveLeft *= slowFactor
                    driveRight *= slowFactor
                if joystick.get_button(buttonHead):
                    pwm.setPWM(0, 0, int(headPan))
                    pwm.setPWM(1, 0, int(headTilt))
                    #print 'headPan value: %f' % (headPan)
                if joystick.get_button(buttonArm):
                    pwm.setPWM(7, 0, int(handVal))
                    pwm.setPWM(5, 0, int(elbowUDVal))
                    pwm.setPWM(6, 0, int(wristVal))
                    pwm.setPWM(2, 0, int(elbowIOVal))
                    print 'wristVal value: %f' % (wristVal)
                    print 'axisWrist value: %f' % (axisWrist) 
                    #print 'axisElbowUD value: %f' % (axisElbowUD)
                    #print 'headTilt value: %f' % (headTilt)
                #else:
            # Set the motors to the new speeds
            PBR.SetMotor1(driveRightD * maxPower)
                    #print 'RSPEED: %f' % (driveRightD)
            PBR.SetMotor2(-driveLeftD * maxPower)
                    #print 'LSPEED: %f' % (-driveLeftD)
        # Change the LED to reflect the status of the EPO latch
        PBR.SetLed(PBR.GetEpo())
        # Wait for the interval period
        time.sleep(interval)
    # Disable all drives
    PBR.MotorsOff()






except KeyboardInterrupt:
    # CTRL+C exit
    print '\nUser shutdown'
finally:
    # Turn the motors off under all scenarios
    print 'Motors off'

#lcd.clear()
lcd.setCursor(0,1)
lcd.message("Shutting down..")

# Tell each thread to stop, and wait for them to end
pwm.setPWM(3, 4095, 0) # clear green status led
time.sleep(0.5)
pwm.setPWM(4, 1, 0) # set red status led
running = False

if pyVideo:
    #time.sleep(1)
    httpServer.shutdown()
    #time.sleep(1)
    httpServer.server_close()
    processor.terminated = True
    watchdog.terminated = True
    serverer.terminated = True
    captureThread.join()
    processor.join()
    watchdog.join()
    serverer.join()

if eyeAnim:
    eyenimator.terminated = True
    eyenimator.join()
    blinker.terminated = True
    blinker.join()

if pyVideo:
    del camera

print 'Web-server terminated.'
PBR.MotorsOff()
time.sleep(0.5)
print 'Shutting down Rainer..'
subprocess.call('../8x8matrixscroll/matrix 1 113 6', shell=True)
#drawEyes(display,eyesleep, 0.1)
time.sleep(0.5)
pwm.softwareReset()
time.sleep(1)
subprocess.call('../8x8matrixscroll/matrix 1 113 8', shell=True)

lcd.clear()   
lcd.backlight(False)
#display.animate([Image.new("RGB", (8, 8)),Image.new("RGB", (8, 8))],0.5)
# Clear the display buffer.
#display.clear()
# Draw the buffer to the display hardware.
#display.write_display()

