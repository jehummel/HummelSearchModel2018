# * * * * * * * * * Graphics bullshit * * * * * * * * *

import pygame, simple_tools
from pygame import *

# Define colors
WHITE = (255,255,255)
LIGHTGRAY = (250,250,250)
GRAY = (150,150,150)
MIDDLEGRAY = (128,128,128)
DARKGRAY = (48, 48, 48)
BLACK = (0,0,0)
RED = (255,0,0)
CYAN = (0,255,255)
LIGHTBLUE = (100, 175, 255)
BLUE = (50,150,255)
DARKBLUE = (0,0,150)
GREEN = (0,255,0)
MIDDLEGREEN = (16,160,64)
EASYRED = (200,64,64)
PURPLE = (200,16,200)
LIGHTGREEN = (50,255,50)
YELLOW = (255,255,50)
ORANGE = (255,100,0)
BROWN = (155, 30, 0)



pygame.init()

# screen set-up
infoObject = pygame.display.Info()
screen_width        = 1800 # infoObject.current_w - 100 #1800 # 1024
screen_height       = infoObject.current_h - 100#1200 # 768
large_text_height   = 36
small_text_height   = 18

vert_midline = int(round(screen_width/2)) # the vertical midline
horiz_midline = int(round(screen_height/2))

# pygame.display.set_mode((infoObject.current_w, infoObject.current_h))
screen = pygame.display.set_mode((screen_width, screen_height))
largefont = pygame.font.SysFont('futura', large_text_height)
smallfont = pygame.font.SysFont('futura', small_text_height)
pygame.mouse.set_visible(True)
pygame.font.init()
