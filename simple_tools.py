'''
Simple_tools.py      10/9/15            Last modified 11/5/15

Simple tools for controlling I/O and GUI stuff for experiments written in Python

This version of the code uses Pygame, so be sure to use Python Vers. 2.7x

'''

import random, sys
from screen_stuff import *
from pygame.locals import *



# # Define colors
# WHITE = (255,255,255)
# LIGHTGRAY = (250,250,250)
# GRAY = (150,150,150)
# DARKGRAY = (50, 50, 50)
# BLACK = (0,0,0)
# RED = (255,0,0)
# LIGHTBLUE = (100, 175, 255)
# BLUE = (50,150,255)
# DARKBLUE = (0,0,150)
# GREEN = (0,255,0)
# YELLOW = (255,255,50)
# ORANGE = (255,100,0)
# BROWN = (155, 30, 0)

# screen set-up
# screen_width  = 1800 # 1024
# screen_height = 1200 # 768
# large_text_height   = 36
# small_text_height   = 18
#
# vert_midline = int(round(screen_width/2)) # the vertical midline
# horiz_midline = int(round(screen_height/2))
#
# pygame.init()
# screen = pygame.display.set_mode((screen_width, screen_height))
# large_font = pygame.font.SysFont('futura', large_text_height)
# smallfont = pygame.font.SysFont('futura', small_text_height)
# pygame.mouse.set_visible(True)
# pygame.font.init()

def blit_text(screen,message, line, column, color, size):
    # formats, renders and blits a message to screen on the designated line
    #   but does NOT update the screen.
    # it is for use in cases where it is necessary to put several lines of
    #   text on the screen
    # 1) render the message
    if size == large_text_height:
        the_text  = largefont.render(message, True, color, LIGHTGRAY)
    else:
        the_text  = smallfont.render(message, True, color, LIGHTGRAY)
    # 2) set it's location
    text_rect = [column * size/2,line * size + 5,screen_width,size]
    # 3) blit it to the screen
    screen.blit(the_text, text_rect)
    pygame.display.update()

def blit_file(screen,file_name, first_line = 1, column = 1, color = BLUE, size = large_text_height):
    '''reads a text file and blits it line by line to the screen.
    first_line is the line number on which to write the first line of the file
    column is the column in which to start writing
    color is text color and size is text size
    '''
    text_file = open(file_name,'r')
    line_num = first_line

    # now clear the screen and write the lines
    screen.fill(LIGHTGRAY)
    for line in text_file:
        line = line.rstrip('\n')
        blit_text(line,line_num,column,color,size)
        line_num += 1

def abort_experiment():
    sys.exit(0)
    # this function called when user hits Esc:
    # asks: do you really want to quit?, etc.
    screen.fill(LIGHTGRAY)# GRAY)  # fill it with a middle gray...
    blit_text('Do you really want to quit? (y/n)',5)
    pygame.display.update()
    quit_response = get_keypress()
    if quit_response in ['y','Y']:
        # close the screen
        pygame.display.quit()
        # and quit
        sys.exit()
    else:
        # simply resume
        screen.fill((250,250,250))# GRAY)  # fill it with a middle gray...
        blit_text('Enter response to continue',5)
        pygame.display.update()

def get_keypress(trigger=None):
    # it waits for the user to enter a key in order to move on
    # NOTE: pygame.key.name() always returns the lower case version of the key; integers 0...9 are seen as chars, not ints
    all_done = False
    while not all_done:
        event_list = pygame.event.get()
        for event in event_list:
            # process the_event according to what type of event it is
            if event.type == QUIT:
                sys.exit(0)
                # return pygame.key.name(abort_experiment())
            elif event.type == KEYDOWN:
                # DIAG
                # print pygame.key.name(event.key)+', val = '+str(event.key)
                if type(pygame.key.name(event.key)) == int:
                    print 'is an integer'
                # end DIAG
                if event.key == K_ESCAPE:
                    sys.exit(0)
                    # abort_experiment()
                elif pygame.key.name(event.key) == trigger:
                    all_done = True
                elif trigger == None:
                    # if there's no trigger, then assume that the program
                    # wants to know what the user entered
                    all_done = True
                    return pygame.key.name(event.key)

def get_integer(row,column,prompt='int>'):
    '''places a prompt at location row, column (name units as blit text) and repeatedly reads char inputs until user
    hits return'''
    # figure out piuxel width of prompt
    num_chars = len(prompt)
    # prompt_width = large_text_height * num_chars
    number = 0 # this is the variable that will accumulate what the user enters
    new_column = column + num_chars
    blit_text(prompt,row,column-3)
    all_done = False # will be true when user enters return
    while not all_done:
        event_list = pygame.event.get()
        for event in event_list:
            if event.type == QUIT: sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE: sys.exit()
                elif event.key > 47 and event.key < 58: # 0 = key 48...9 = key 57
                    # it's a number
                    new_column += 1 #  move 1 column to the right
                    number *= 10 # shift the current value one place to the left
                    number += (event.key - 48) # and add the value of the current digit
                    # write the digit to the screen
                    blit_text(pygame.key.name(event.key),row,new_column)
                elif event.key == 13: # the return key
                    all_done = True
                    # erase the number from the screen
                    eraser = '  '
                    eraser_width = 2 * (new_column - column+3)
                    for i in xrange(eraser_width): # add spaces to the eraser
                        eraser = eraser + ' '
                    blit_text(eraser,row,column-3) # and blit the eraser, erasing the text
                    return number

def get_float(row, column):
    '''places a prompt at location row, column (name units as blit text) and repeatedly reads char inputs until user
    hits return.
    This version can read numbers with decimal places.'''
    number = 0.0 # this is the variable that will accumulate what the user enters
    before_decimal = True # reading numbers before the decimal point
    multiplier = 1.0 # for multiplying each successive digit after the decimal
    new_column = column
    blit_text('float>',row,column-5)
    all_done = False # will be true when user enters return
    while not all_done:
        event_list = pygame.event.get()
        for event in event_list:
            if event.type == QUIT: sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE: sys.exit()
                elif event.key == 46: # the decimal
                    new_column += 1
                    before_decimal = False
                    # write the decimal to the screen
                    blit_text(pygame.key.name(event.key),row,new_column)
                elif event.key > 47 and event.key < 58 and before_decimal: # 0 = key 48...9 = key 57
                    # it's a number
                    new_column += 1 #  move 1 column to the right
                    number *= 10 # shift the current value one place to the left
                    number += (event.key - 48) # and add the value of the current digit
                    # write the digit to the screen
                    blit_text(pygame.key.name(event.key),row,new_column)
                elif event.key > 47 and event.key < 58 and not(before_decimal): # after decimal
                    # it's a number
                    new_column += 1 #  move 1 column to the right
                    multiplier /= 10.0
                    addend = (event.key - 48) * multiplier
                    number += addend
                    # write the digit to the screen
                    blit_text(pygame.key.name(event.key),row,new_column)
                elif event.key == 13: # the return key
                    all_done = True
                    # erase the number from the screen
                    eraser = '  '
                    eraser_width = 2 * (new_column - column + 5)
                    for i in xrange(eraser_width): # add spaces to the eraser
                        eraser = eraser + ' '
                    blit_text(eraser,row,column-5) # and blit the eraser, erasing the text
                    return number

def get_text(row, column):
    '''places a prompt at location row, column (name units as blit text) and repeatedly reads char inputs until user
    hits return.
    Interprets the input as a Spring, not a number!'''
    the_text = ''
    blit_text('text>',row,column-4)
    new_column = column
    all_done = False # will be true when user enters return
    while not all_done:
        event_list = pygame.event.get()
        for event in event_list:
            if event.type == QUIT: sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE: sys.exit()
                elif event.key > 47 and event.key < 123: # 0 = key 48...9 = key 57, a = 97, z = 122
                    # it's a char
                    new_column += 1
                    the_text = the_text + str(pygame.key.name(event.key))
                    # write the digit to the screen
                    blit_text(pygame.key.name(event.key),row,new_column)
                elif event.key == 13: # the return key
                    all_done = True
                    # erase the number from the screen
                    eraser = '  '
                    eraser_width = 2 * (new_column - column+4)
                    for i in xrange(eraser_width): # add spaces to the eraser
                        eraser = eraser + ' '
                    blit_text(eraser,row,column-4) # and blit the eraser, erasing the text
                    return the_text

def choose_condition():
    '''Randomly choose a condition number, 1...6, from the set of all remaining condition numbers:
    Reads ConditionsRemaining file specifying number of remaining subjects in each condition, then randomly chooses
        a condition number from the remaining choises, updates the list of remaining choices and saves the file'''
    # 1) Read the ConditionsRemaining file specifying how many subjects remain to be run in each condition (e.g.,
    #    [5, 3] would mean five remaining in condition 1 and thee in condition 2)
    # 2) Convert those numbers to a list of that many condition numbers (e.g., if it says that are 5 remaining
    #    in condition 1 and 3 in condition 2, make a list of five 1s and three 2s)
    # 3) Randomly choose a condition number from that list
    # 4) Convert that list back into a list of numbers of subjects remaining in each condition
    # 5) Save that list back to file
    # 6) Return the chosen condition number

    # 1) Read the ConditionsRemaining file specifying how many subjects remain to be run in each condition (e.g.,
    #    [5, 3] would mean five remaining in condition 1 and thee in condition 2)
    cr_file = open('ConditionsRemaining.txt','r')  # open the text file
    text_line = cr_file.next()                   # read the one and only line in the file
    text_line = text_line.rstrip('\r')           # strip the carriage return off the end
    numbers_left = list(text_line.split())   # split the line at tabs, saving the results as a list
    cr_file.close()
    # go through the list of numbers and turn them into ints
    for index in xrange(len(numbers_left)):
        numbers_left[index] = int(numbers_left[index])
    # At this point, numbers_left is a list of integers (indexed 0...5) indicating how many subjects remain to be run
    #   in each condition (1...6)

    # 2) Use numbers_left to create the list of condition numbers
    condition_numbers = []
    for i in xrange(len(numbers_left)):
        cond_number = i + 1 # remember that condition numbers go 1...6, indices go 0...5: So get condition number for this index
        # now append numbers_left[i] entries of cond_number to the condition_numbers list
        for j in xrange(numbers_left[i]):
            condition_numbers.append(cond_number)

    # 2.5) ERROR-Check: Make sure there is at least one condition number remaining
    if condition_numbers == []:
        print 'ERROR: You have already run all subjects in all conditions!'
        return 0

    # 3) Randomly choose one number from that list: shuffle the list and pop off the 0th element
    random.shuffle(condition_numbers)
    chosen_condition = condition_numbers.pop(0)

    # DIAG
    print 'Chosen condition = ',chosen_condition

    # 4) Convert what remains of the condition_numbers list back into a numbers_left list:
    #    Simply get the index of that list and decrement the corresponding value by 1
    chosen_index = chosen_condition - 1
    numbers_left[chosen_index] -= 1

    # 5) Re-save the RemainingConditions file
    # convert ints to strings
    str_numbers_left = []
    for number in numbers_left:
        str_numbers_left.append(str(number))
    cr_file = open('ConditionsRemaining.txt','w')  # open the text file
    text_line = '\t'.join(str_numbers_left)
    cr_file.write(text_line)
    cr_file.close()

    # 6) Return the chosen condition
    return chosen_condition



# * * * * Main * * * *
if __name__ == "__main__":

    blit_file('test_text.txt')

    number = get_integer(10,8)
    print 'The integer is ',number

    number = get_float(10,8)
    print 'The float is %.5f' %number

    the_text = get_text(10,8)
    print 'The text is ',the_text

    get_keypress('q')
    pygame.display.quit()
