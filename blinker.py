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




exitFlag = 0


logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )



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
                    #logging.debug('BLINK!')
                    time.sleep(5)
                    subprocess.call('../8x8matrixscroll/matrix 1 112 5 &', shell=True)
                    
                    print("BLINK!")
                finally:
                    # Reset the event
                    self.event.clear()

class myThread (threading.Thread):
    def __init__(self, threadID, name, counter):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
    def run(self):
        print "Starting " + self.name
        print_time(self.name, self.counter, 5)
        print "Exiting " + self.name

def print_time(threadName, delay, counter):
    while counter:
        if exitFlag:
            threadName.exit()
        time.sleep(delay)
        print "%s: %s" % (threadName, time.ctime(time.time()))
        counter -= 1

# Create new threads
thread1 = myThread(1, "Thread-1", 1)
thread2 = myThread(2, "Thread-2", 2)

# Start new Threads
#thread1.start()
#thread2.start()

#print "Exiting Main Thread"







blinker = Blinker()

