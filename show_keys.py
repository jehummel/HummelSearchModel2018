__author__ = 'john'

'''A trivial function for showing the value of event.key when user presses key on keyboard'''

import pygame
from pygame.locals import *
pygame.init()

print 'Hit keys to see the numerical value (pygame.event.key) of the keystroke.'
print 'When you grow weary of this game, hit Esc to quit.'

all_done = False
while not all_done:
    event_list = pygame.event.get()
    for event in event_list:
        if event.type == KEYDOWN:
            print 'key value = '+str(event.key)+': '+pygame.key.name(event.key)
            if event.key == K_ESCAPE:
                all_done = True

