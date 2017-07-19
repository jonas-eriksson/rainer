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

from PIL import Image
from PIL import ImageDraw
from Adafruit_LED_Backpack import Matrix8x8
from Adafruit_PWM_Servo_Driver import PWM


logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

# Settings for the web-page
webPort = 80                            # Port number for the web-page, 80 is what web-pages normally use
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
axisUpDown = 1                          # Joystick axis to read for up / down position
axisUpDownInverted = False              # Set this to True if up and down appear to be swapped
axisLeftRight = 0                       # Joystick axis to read for left / right position
axisLeftRightInverted = True           # Set this to True if left and right appear to be swapped
buttonResetEpo = 3                      # Joystick button number to perform an EPO reset (Start)
buttonSlow = 8                          # Joystick button number for driving slowly whilst held (L2)
slowFactor = 0.5                        # Speed to slow to when the drive slowly button is held, e.g. 0.5 would be half speed
buttonFastTurn = 9                      # Joystick button number for turning fast (R2)
interval = 0.00                         # Time between updates in seconds, smaller responds faster but uses more processor time

buttonHead = 11                         # Hold to control head pan/tilt (R1)
buttonTriangle = 12
buttonCircle = 13
buttonCross = 14
buttonSquare = 15

buttonDL = 7
buttonDR = 5
buttonDU = 4
buttonDD = 6

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

print '----------------------------'
print '----- RAINER THE ROBOT -----'
print '----------------------------'


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
                    time.sleep(10)
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
                    httpServer.handle_request()
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




print 'Initializing eyes..'
# Create display instance on default I2C address (0x70) and bus number.
display = Matrix8x8.Matrix8x8()

# Initialize the display. Must be called once before using the display.
#display.begin()

# Clear the display buffer.
#display.clear()
# Draw the buffer to the display hardware.
#display.write_display()

# Set led matrices to sleep mode at the beginning
#drawEyes(display,eyesleep,0.1)
subprocess.call('../8x8matrixscroll/matrix 1 113 0', shell=True)
time.sleep(0.5)

print 'Initializing head servos..'
# Initialise the PWM device using the default address
pwm = PWM(0x40)
# Set frequency to 60 Hz
#pwm.setPWMFreq(60)  

servoMin = 150  # Min pulse length out of 4096
servoMax = 600  # Max pulse length out of 4096
servoMid = (servoMax-servoMin)/2+servoMin

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



# Setup pygame and wait for the joystick to become available
PBR.MotorsOff()
os.environ["SDL_VIDEODRIVER"] = "dummy" # Removes the need to have a GUI window
pygame.init()
#pygame.display.set_mode((1,1))
print 'Waiting for joystick... (press CTRL+C to abort)'
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


## Read lines from file
lines = [line.strip('\n') for line in open('lines_se.txt')]
print(len(lines))





# Wake up sequence - open eyes and raise head (tilt)

time.sleep(0.5)
#os.system('./matrix.sh')
#os.system(' ../8x8matrixscroll/matrix 1 112 2')
#call("ls", "-la")
#drawEyes(display,eyeopen,0.0)



subprocess.call('../8x8matrixscroll/matrix 1 113 1 &', shell=True)
time.sleep(0.5)
pwm.setPWMFreq(60)  
pwm.setPWM(1, 0, 500) # tilt servo
#subprocess.call(['espeak', '-a20', '-k1', '-g5', '-p10', '-s160', '-v', 'en-scottish', '-w', 'out.wav', '"Hello!"', '&&', 'sudo', 'aplay', '-q', 'out.wav'])
#os.system('espeak -a20 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Hello!" && sudo aplay -q out.wav')	
time.sleep(1.0)
#talk("Where is my burrito?")

#blinktimer.start()

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

print 'Starting Blinker'
blinker = Blinker()


print 'Setup the watchdog'
watchdog = Watchdog()



#### Added to get rid of "address in use" error
SocketServer.TCPServer.allow_reuse_address = True

# Run the web server until we are told to close
httpServer = SocketServer.TCPServer(("0.0.0.0", webPort), WebServer)

serverer = Serverer()
try:
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
            elif event.type == pygame.JOYBUTTONDOWN:
            	button = event.button
            	print("Button {} on".format(button))
                # A button on the joystick just got pushed down
            	if joystick.get_button(buttonCircle):
					#print 'Circle pressed!'
					# Construct a line to call
					cmd = ["espeak -a40 -k1 -g5 -p10 -s160 -v swedish -w out.wav \"" + lines[phrasenum] + "\" && sudo aplay -q out.wav"]
					#print(cmd)
					subprocess.call(cmd, shell=True)
					hadEvent = True
            	if joystick.get_button(buttonTriangle):
					#print 'Triangle pressed!'
					#os.system('/home/pi/weather-2.2/weather --setpath=/home/pi/weather-2.2 -m efhf | sudo flite -voice rms')					
					hadEvent = True
            	if joystick.get_button(buttonSquare):
					#print 'Square pressed! (not used)'
					os.system('espeak -a40 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Hello, Lotta! You look wonderful today!" && sudo aplay -q out.wav')
					#os.system('echo "Hello, Lotta!" | sudo festival --tts')
					hadEvent = True
            	if joystick.get_button(buttonCross):
					#print 'Cross pressed! (not used)'
					os.system('espeak -a40 -k1 -g5 -p10 -s160 -v en-scottish -w out.wav "Lotta!" && sudo aplay -q out.wav')					
					hadEvent = True
            	if joystick.get_button(buttonDU):
					print 'D pad up pressed!'
					driveRightD = 0.75 #PBR.SetMotor1(0.75)
					driveLeftD = 0.75 #PBR.SetMotor2(-0.75)			
					hadEvent = True
            
            	if joystick.get_button(buttonDD):
					print 'D pad down pressed!'
					driveRightD = -0.75 #PBR.SetMotor1(-0.75)
					driveLeftD = -0.75 #PBR.SetMotor2(0.75)			
					hadEvent = True

            	if joystick.get_button(buttonDL):
					print 'D pad left pressed!'
					oldRightD = driveRightD
					oldLeftD = driveLeftD
					driveRightD = -0.75 #PBR.SetMotor1(-0.75)
					driveLeftD = 0.75 #PBR.SetMotor2(-0.75)			
					hadEvent = True

            	if joystick.get_button(buttonDR):
					print 'D pad right pressed!'
					oldRightD = driveRightD
					oldLeftD = driveLeftD
					driveRightD = 0.75 #PBR.SetMotor1(0.75)
					driveLeftD = -0.75 #PBR.SetMotor2(0.75)			
					hadEvent = True


            elif event.type == pygame.JOYBUTTONUP:
            	button = event.button
            	print("Button {} off".format(button))
            	if button == buttonDU:
					print 'D pad up released!'
					driveRightD = 0 #PBR.SetMotor1(0)
					driveLeftD = 0 #PBR.SetMotor2(0)			
					hadEvent = True

            	elif button == buttonDD:
					print 'D pad down released!'
					driveRightD = 0 #PBR.SetMotor1(0)
					driveLeftD = 0 #PBR.SetMotor2(0)			
					hadEvent = True

            	elif button == buttonDR:
					print 'D pad down released!'
					driveRightD = oldRightD #PBR.SetMotor1(0)
					driveLeftD = oldLeftD #PBR.SetMotor2(0)			
					hadEvent = True
            	
            	elif button == buttonDL:
					print 'D pad down released!'
					driveRightD = oldRightD #PBR.SetMotor1(0)
					driveLeftD = oldLeftD #PBR.SetMotor2(0)			
					hadEvent = True

        
            elif event.type == pygame.JOYAXISMOTION:
                # A joystick has been moved
                hadEvent = True
            if hadEvent:
                # Read axis positions (-1 to +1)
                if axisUpDownInverted:
                    upDown = -joystick.get_axis(axisUpDown)
                   # print 'UP/DOWN triggered!\n'
                else:
                    upDown = joystick.get_axis(axisUpDown)
                    #print 'UP/DOWN value: %f' % (upDown)
                if axisLeftRightInverted:
                    leftRight = -joystick.get_axis(axisLeftRight)
                    #print 'L/R triggered!\n'
                else:
                    leftRight = joystick.get_axis(axisLeftRight)
                    #print 'L/R value: %f' % (leftRight)
                # Apply steering speeds
                if not joystick.get_button(buttonFastTurn):
                    #print 'FAST pressed'
                    leftRight *= 0.5
                # Determine the drive power levels
                driveLeft = -upDown
                driveRight = -upDown
                headPan = (leftRight * (servoMid+75) + servoMax-servoMid+servoMin)
                headTilt = (upDown/2 * (servoMid+75) + 500)
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
# Tell each thread to stop, and wait for them to end
running = False
captureThread.join()
processor.terminated = True
watchdog.terminated = True
blinker.terminated = True
serverer.terminated = True
processor.join()
watchdog.join()
blinker.join()
serverer.join()
del camera
print 'Web-server terminated.'
PBR.MotorsOff()
time.sleep(0.5)
print 'Shutting down Rainer..'
subprocess.call('../8x8matrixscroll/matrix 1 113 0', shell=True)
#drawEyes(display,eyesleep, 0.1)
time.sleep(0.5)
pwm.softwareReset()
time.sleep(1)
    
#display.animate([Image.new("RGB", (8, 8)),Image.new("RGB", (8, 8))],0.5)
# Clear the display buffer.
#display.clear()
# Draw the buffer to the display hardware.
#display.write_display()

