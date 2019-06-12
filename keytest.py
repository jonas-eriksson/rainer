import pygame


import sys
import os


# Re-direct our output to standard error, we need to ignore standard out to hide some nasty print statements from pygame
sys.stdout = sys.stderr



os.environ["SDL_VIDEODRIVER"] = "dummy" # Removes the need to have a GUI window


pygame.init()
WIDTH=600
HEIGHT=480
pygame.display.set_mode((1,1))

while True:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                print('this DOES work! :)')
