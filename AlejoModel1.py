__author__ = 'john'

# * * * * * * * * * Attention Model  First attempt to implement the model I think can account for Alejo & Simona's data  1/16/19

# Model stochastically samples locations, rejecting or accepting them as a function of an accumulator that either crosses threshold or not
# Version 2 (1/17/19): For unattended stimuli, stochastically sample dimensions, with greater weight on relevant (attended) ones
# Version 3 (1/17/19): Process attended & unattended genuinely in parallel: one iteration for selected for each w/ everything else
# Version 4 (1/28/19): Implement location, eye movements and graphics: First complete version

# last modified 1/29/19



# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * Run Control Parameters * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *

VERBOSE = False # when true, the model runs only once and tells you events iteration by iteration
GRAPHIC = True # when true, shows one simulation graphically



# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * Major, Theory-relevant Parameters * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

# Search item rejection and acceptance parameters
TARGET_MATCH_TRESHOLD       = 4 # 8 # 16 # 4 # 2 # the threshold an item's integrator must exceed to be matched as the target
REJECTION_THRESHOLD         = -2.0 # -4.0 # -1.0 # -0.5  # the negative threshold an item's integrator must reach to be rejected from search altogether
EXACT_MATCH_THRESHOLD       = 0.01 # euclidean distance below which two vectors are considered an exact match
REJECTION_COST_CONSTANT     = 10 # just a constant added to RT due to rejections

# for random sampling during inattention
P_RELEVANT_SAMPLING        = 0.5 # 0.95# 0.7 # 1.0 # 0.5 # p(sampling) a relevant dimension in unattended processing
P_IRRELEVANT_SAMPLING      = 0.05 # 0 # 0.05 # p(sampling) an irrelevant dimension in unattended processing

# effect of distance between fixation and item location in the display: how much does distance from fixation impair the rate of feature sampling:
DISTANCE_FALLOFF_RATE      = 0.01 # 0 # 10.0/150 #where 150 is the display radius # 0 #  0 = None; large means sharp falloff away from fixation; will be sensitive to how distance is represented

# for feature weighting under selected processing
RELEVANT_WEIGHT            = 1.0 # how much relevant dimensions contribute to similarity
IRRELEVANT_WEIGHT          = 0.1 # how much irrelevant dimensions contribute to similarity
MISMATCH_BIAS              = 10  # how much does a mismatching feature hurt matching compared to a matching feature helping it

# operation cost parameters
ATTENTION_SHIFT_COST       = 2 # how many iterations does it cost to switch attention to a new item
DOUBLE_CHECK_MATCH         = False # do the conservative distance check on matching item and add cost
EXACT_MATCH_COST           = 1 # how many iterations does it take to compute the final, exact match for target verification

# search behavior parameters
INTEGRATOR_GUIDED_PRIORITY = 0.1 #  1.0 # [0...1]: degree to which an item's integrator influences it's selection priority: influence means better-matching items are more likely to be selected for evaluation
PERMIT_EYE_MOVEMENTS       = True # whether model is allowed to change fixation when it moves attention



# * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * Graphics Bullshit * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * *

import math, trig, random
# import pygame

# from pygame import *
#
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

if GRAPHIC:
    import pygame
    pygame.init()
    #
    # screen set-up
    infoObject = pygame.display.Info()
    screen_width        = 1000 # infoObject.current_w - 100 #1800 # 1024
    screen_height       = 1000 # infoObject.current_h - 100#1200 # 768
    large_text_height   = 36
    small_text_height   = 18
    #
    vert_midline = int(round(screen_width/2)) # the vertical midline
    horiz_midline = int(round(screen_height/2))
    #
    # pygame.display.set_mode((infoObject.current_w, infoObject.current_h))
    screen = pygame.display.set_mode((screen_width, screen_height))
    largefont = pygame.font.SysFont('futura', large_text_height)
    smallfont = pygame.font.SysFont('futura', small_text_height)
    pygame.mouse.set_visible(True)
    pygame.font.init()
    #
    import simple_tools # some mundane IO functions



# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * Major Data Structures: Seach Items * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *

# feature dimension indices (1/17/19). Check these against make_feature_vector for consistency

COLOR_DIMENSIONS = ( 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17) #  0...17 = 18
SHAPE_DIMENSIONS = (18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36)    # 18...36 = 19

def make_feature_vector(color,shape):
    # take names for color and shape and make a corresponding feature vector
    # color vectors are [r,r,r,g,g,g,b,b,b,y,y,y]
    #                          [-------B/W-----][-------R/G------][-------B/Y-------]
    color_vectors = {'white' :[ 1, 1, 1,-1,-1,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'black' :[-1,-1,-1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'red'   :[ 0, 0, 0, 0, 0, 0, 1, 1, 1,-1,-1,-1, 0, 0, 0, 0, 0, 0],    # red = red and Not green
                     'green' :[ 0, 0, 0, 0, 0, 0,-1,-1,-1, 1, 1, 1, 0, 0, 0, 0, 0, 0], # green = green and Not red
                     'blue'  :[ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1,-1,-1,-1],  # blue = blue & not yellow
                     'yellow':[ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,-1,-1,-1, 1, 1, 1], # yellow = yellow & blue
                     'orange':[ 0, 0, 0, 0, 0, 0, 1, 1, 0,-1,-1, 0,-1, 0, 0, 1, 0, 0], # orange is 2 red, 2 not green, 1 yellow, 1 not blue
                     'pink'  :[ 1, 1, 0,-1,-1, 0, 1, 0, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0]}
    # shape is v1,v2,h1,h2,d1,d1,d2,d2,L1,L2,L3,L4,T1,T2,T3,T4,X
    #                             [-------V/H-------][-----D-----][-----L----][-----T----][X]
    shape_vectors = {'vertical'  :[ 1, 1, 1,-1,-1,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'horizontal':[-1,-1,-1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'T1'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
                     'T2'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                     'T3'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                     'T4'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                     'L1'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                     'L2'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                     'L3'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                     'L4'        :[ 1, 0, 0, 1, 0, 0,-1, 0,-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                     'D1'        :[-1, 0, 0,-1, 0, 0, 1, 1,-1,-1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'D2'        :[ 0,-1, 0, 0, 0,-1,-1,-1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     'X'         :[-1, 0, 0, 0, 0,-1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1]}
    color_vector = color_vectors[color]
    shape_vector = shape_vectors[shape]
    feature_vector = []
    feature_vector.extend(color_vector)
    feature_vector.extend(shape_vector)

    return feature_vector

class VisualItem(object):
    """
    This is the basic VisualItem data class for the model
    VisualItems include the target (in the display), the distractors & lures (which are in the display) and the target template (not in the display)
    """
    def __init__(self,my_list,feature_vector,color_name='',shape_name='',name='',is_target=False):
        """
        :param my_list:  the list in the larger program to which this item belongs
        :param location: location on the screen, in [x,y] coordinates
        :param name: name (e.g., 'target', 'lure', 'template', etc.
        :param is_target: boolean that indicates whether this visual item is in fact the target
        """
        self.name = name
        self.is_target = is_target  # a boolean that specifies whether this item (in the visual display) is the target
        # get the index in the list
        if my_list:
            self.index = len(my_list)
        else:
            self.index = 0

        # for graphics
        self.color              = color_name
        self.shape              = shape_name # this will be a string like 'vertical' or 'L1' which will tell self.draw() what to draw
        self.currently_selected = False

        # the working parts
        self.location   = None # location on the screen, in [x,y] coordinates
        self.fix_dist   = 0.0 # distance from fixation
        self.dist_wt    = 1.0 # weighting on the acculumlator as a function of the distance from fixation
        self.features   = feature_vector # this is a feature vector: will get compared to the template during search
        self.integrator = 0 # the thing that, when it passes upper theshold, registers match (i.e., target found) and when below neg threshold registers mismatch (rejection)
        self.rejected   = False # item is rejected when integrator goes below negative threshold; ceases to be functional part of search

        # for search/random selection on iteration-by-iteration basis
        self.priority   = 1.0 # this is a combination of salience, etc. When priority = 0, item has no chance of being selected; self.rejected, priority = 0
        self.subrange   = [0.0,0.0] # selection range: the subrange within [0...1] in which random.random() must fall in order for this guy to be selected

        # DIAG
        # print 'item created: '+str(self.index)

    def get_fixation_distance(self,fixation):
        """
        computes the distance between the item and the fixation point
        :param fixation: 
        :return: 
        """
        distance = 0.0
        for i in xrange(len(self.location)):
            distance += (self.location[i] - fixation[i])**2
        self.fix_dist = pow(distance,0.5)

    def draw(self):
        # DIAG
        # print 'drawing item '+str(self.index)+' at '+str(self.location)

        # draw rejected items in gray, others in their own color
        if self.rejected:
            color = GRAY
        else:
            color = self.color
        # draw everything within the rectangle self.location[0],self.location[1],ITEM_RADIUS*2,ITEM_RADIUS*2
        # WHAT you draw depends on the item's shape
        if self.shape == 'vertical':
            # a vertical line through the middle of the rectangle
            x1 = self.location[0] + ITEM_RADIUS
            x2 = x1
            y1 = self.location[1]
            y2 = self.location[1] + 2* ITEM_RADIUS
            pygame.draw.line(screen,color,(x1,y1),(x2,y2),3)
        elif self.shape == 'horizontal':
            # a horizontal line through the middle of the rectangle
            x1 = self.location[0]
            x2 = self.location[0] + 2 * ITEM_RADIUS
            y1 = self.location[1] + ITEM_RADIUS
            y2 = y1
            pygame.draw.line(screen,color,(x1,y1),(x2,y2),3)
        else:
            # DIAG
            print 'No Shape!'

            location = (self.location[0]+ITEM_RADIUS,self.location[1]+ITEM_RADIUS)
            # draw a filled circle if nothing else
            pygame.draw.circle(screen,color,location,ITEM_RADIUS,0)

        # draw black circle around currently selected, light gray around everything else
        location = (self.location[0] + ITEM_RADIUS, self.location[1] + ITEM_RADIUS)
        if self.currently_selected:
            color = BLACK
        else:
            color = LIGHTGRAY
        pygame.draw.circle(screen, color, location, ITEM_RADIUS+1, 1)

        # pygame.display.update()

def make_search_items(existing_list,num,color,shape,name = '',is_target=False):
    """
    creates a (subset of a) search display: makes num items of color and shape
    num: how many to make
    color: what color to make them
    shape: what shape to make them
    disply_list: the larger search display list to which they will be added
    :return: the list of items in the display
    """
    items = existing_list # a list of all items to make

    # get the feature vector
    features = make_feature_vector(color,shape)

    color_name = ORANGE # just a default
    # get color name
    if color == 'red':
        color_name = RED
    elif color == 'green':
        color_name = GREEN
    elif color == 'white':
        color_name = WHITE
    elif color == 'black':
        color_name = BLACK
    elif color == 'blue':
        color_name = BLUE
    else:
        color_name = ORANGE # ToDo: include more actual colors

    # make the required number of these guys
    for i in xrange(num):
        # my_list,feature_vector,color_name='',shape_name='',name='',is_target=False
        items.append(VisualItem(items,features,color_name,shape,name,is_target))

    # return 'em
    return items



# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * Display Characteristics/ Operations * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

# graphics and display constants

ITEM_RADIUS       = 10 # radius of a single search item on the screen. in the case of square items, this is 1/2 the size of a side
ITEM_DISTANCE     = 22 # the distance between adjacent items' upper left (x,y) coordinates: needs to be 2 * ITEM_RADIUS, plus a buffer

CARTESIAN_GRID    = True # the display grid is cartesian; if False, then it's polar

DISPLAY_CENTER    = (300,300) # the center of the search display, in screen coordinates. will also be the initial location of fixation
DISPLAY_RADIUS    = 200 # 150

def make_cartesian_locations():
    """
    Makes a list of locations on an (x,y) cartesian grid for stimuli. 
    param: display_space: a rectangle [center_x,center_y,half_width], center_x and center_y are the coordinates of the center of the display and half_width is half the width of the full display (like a radius)
    :return: a list of locations in a randomized order (random.shuffle()); each location is only (upper_left,upper_right), expressed in screen coordinates
    """
    locations = []
    min_x = DISPLAY_CENTER[0] - DISPLAY_RADIUS
    max_x = min_x + 2*DISPLAY_RADIUS - 2*ITEM_RADIUS
    min_y = DISPLAY_CENTER[1] - DISPLAY_RADIUS
    max_y = min_y + 2*DISPLAY_RADIUS - 2*ITEM_RADIUS

    xpos = min_x # start in upper left: center_x minus half_width
    while (xpos+ITEM_RADIUS) <= max_x: # while you're not wider than the display...
        ypos = min_y  # start in upper left: center_y minus half_width
        while (ypos+ITEM_RADIUS) <= max_y: # while you're not taller than the display
            location = [xpos,ypos]
            locations.append(location)
            ypos += ITEM_DISTANCE
            # DIAG
            # print location
        xpos += ITEM_DISTANCE

    # the locations are constructed: shuffle and return them
    random.shuffle(locations)
    return locations

def make_polar_locations(dense = False):
    """
    makes a list oflocations arrayed in a polar fashion around the center od the display for for stimuli
    :param dense means fill as many angles as possible; if not, then increment abgle by Pi/8 for all radii
    :return: a list of locations in a randomized order (random.shuffle()); each location is (upper_left,upper_right), expressed in screen (cartesian) coordinates
    """
    locations = []
    # add the cenetr of the display
    # locations.append([DISPLAY_CENTER[0]-ITEM_DISTANCE,DISPLAY_CENTER[1]-ITEM_DISTANCE])

    # DIAG
    # if GRAPHIC:
    #     # show center of display
    #     pygame.draw.circle(screen,BLACK,DISPLAY_CENTER,2,0)

    # now iterate through radii in increments of ITEM_DISTANCE
    radius = ITEM_DISTANCE * 2
    while radius+ITEM_RADIUS < DISPLAY_RADIUS:
        angle = 0
        if dense: # fill as many angles as possible
            # figure out the angle_increment for this radius: it is the fraction of the circumference taken by the item width
            circumference = 2 * math.pi * radius
            distance_increment = ITEM_DISTANCE/circumference  # dist. increment is the fraction of the circle you can move
            angle_increment = distance_increment * 2 * math.pi # angle increment is that, expressed in radians basically, the angle increment is set to the number of items that can fit inside the circumference
        else:  # not dense: only fill angles in increments of Pi/8
            angle_increment = math.pi/4.0
        while angle < 2 * math.pi:
            [real_x,real_y] = trig.get_cartesian([radius,angle],[DISPLAY_CENTER[0],DISPLAY_CENTER[1]]) # get the cartesian coordinates at this radius and angle
            location = [int(round(real_x))-ITEM_RADIUS,int(round(real_y))-ITEM_RADIUS]                # round it off to integer values and offset by item radius to center @ location
            locations.append(location)                                                                 # and add it to the list
            angle += angle_increment                                                                   # and increment the angle
        if dense: # increment radius by minimum amount
            radius += ITEM_DISTANCE
        else:
            radius *= 1.5 # += ITEM_DISTANCE # * 1.5

    # DIAG
    # print 'num polar locations = '+str(len(locations))

    # the locations are all made: shuffle & returnthem
    random.shuffle(locations)
    return locations

def assign_locations(search_display):
    """
    assign screen locations to the search items
    :return: the search display, once items have been assigned
    """
    if CARTESIAN_GRID:
        locations = make_cartesian_locations()
    else:
        locations = make_polar_locations()

    # at this point, locations is a randomly ordered set of locations in either cartesian or polar space
    # now iterate through the search_display and assugn these locations ot the search items
    for item in search_display:
        item.location = locations.pop(0)

    # and return the search display
    return search_display



# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * Major Functions: Seach Operations * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *

def randomly_select_item(all_items):
    # takes all visual search items and randomly selects one of them based on their priorities, etc.

    # 1) calculate the sum of all items' priorities
    priority_sum = 0.0
    for item in all_items:
        priority_sum += item.priority
        item.currently_selected = False # init all to False at this point

    # 2) assign each item a subrange: a subset of the range [0...1] whose width is proportional to item/priority/priority_sum
    if priority_sum > 0:
        range_bottom = 0.0
        for item in all_items:
            range_top = range_bottom + item.priority/priority_sum # range width = range_bottom...range_top = item.priority/priority_sum
            item.subrange = [range_bottom,range_top]
            range_bottom = range_top

    # 3) get a random number in [0...1] and select as chosen the item whose subrange includes that number
    the_number = random.random()
    for item in all_items:
        if the_number >= item.subrange[0] and the_number < item.subrange[1]:
            item.currently_selected = True
            return item

    # 4) if you get to this point, you found nothing: return None
    return None

def random_sample_feature_match(vect1,vect2,relevant):
    # for unattended processing: decide vect1-vect2 similarity by randomly sampling
    #   dimensions
    # return num_matches - num_mismatches
    match = 0
    # len1 = 0
    # len2 = 0
    for i in xrange(len(vect1)):
        # randomly sample dimension i depending on whether it's in the relevant set
        if i in relevant:
            do_sample = random.random() < P_RELEVANT_SAMPLING
        else:
            do_sample = random.random() < P_IRRELEVANT_SAMPLING
        if do_sample:
            # sample this dimension:

            # Version 1:
            # if the vectors both 1, then add 1;
            # if they are different, then subtract 1
            if vect1[i] or vect2[i]: # if at least one is active...
                if vect1[i] == vect2[i]: match += 1
                else: match += -1

            # Version2: simple product
            # match += vect1[i] * vect2[i]

            # Version 2b: cosine
            # len1 += pow(vect1[i], 2)
            # len2 += pow(vect2[i], 2)
    # now normalize the match score by the max possible
    match /= len(relevant)

    # or (2b) by the product of the lengths
    # len1 = pow(len1,0.5)
    # len2 = pow(len2,0.5)
    # if len1 * len2 > 0:
    #     match /= (len1 * len2)
    return match

# * * * * * The dot product is entirely the wrong function here * * * * *
#           It's not good enough that the vectors point in the right direction:
#           Mismatches have to count more than matches
#
# def feature_similarity(vect1,vect2,relevant):
#     # returns the vector similarity of two vector1 and vector2
#     # could be cosine, dot product, whatever...
#     # for now, we're gonna do cosine
#     len1        = 0.0 # length of vector1
#     len2        = 0.0 # length of vector2
#     dot_product = 0.0
#     for i in xrange(len(vect1)):
#         # determine feature weight based on relevance
#         if i in relevant: # if i is a feature along the relevant dimension
#             weight = RELEVANT_WEIGHT
#         else:
#             weight = IRRELEVANT_WEIGHT
#         len1 += pow(vect1[i] * weight,2)
#         # len2 += pow(vect2[i] * weight,2)
#         len2 += pow(vect2[i], 2)
#         dot_product += vect1[i] * weight * vect2[i] # * weight
#     len1 = pow(len1,0.5)
#     len2 = pow(len2,0.5)
#     len_product = len1 * len2
#     if len_product > 0:
#         return dot_product/len_product
#     else:
#         print "Error! One or more vectors has length zero."
#         return None

def feature_similarity(vect1,vect2,relevant):
    """
    Determines whether two lists of features are a match or a mismatch.
    This version does NOT work by a simple dot product or cosine:
    Mismatches have to matter Much more than matches.
    This version computes a mismatch score and returns that; returns a positive score if mismatch is zero
    
    :param vect1: one of the two vectors to be compared
    :param vect2: the other vector to be compared
    :param relevant: a list of the dimensions that are relevant to the comparison
    :return: 
    """
    match_sum    = 0
    mismatch_sum = 0
    for i in xrange(len(vect1)):
        if i in relevant:
            weight = RELEVANT_WEIGHT
        else:
            weight = IRRELEVANT_WEIGHT
        if vect1[i] == vect2[i]:
            match_sum += weight
        else:
            mismatch_sum += weight * MISMATCH_BIAS

    # now, probabilistically return a -1 or a 1 as a function of match_sum - mismatch_sum
    probability = 1.0/(1+pow(math.e,-(match_sum-mismatch_sum)))

    if random.random() < probability:
        return 1
    else:
        return -1

def exact_match(vect1,vect2,relevant):
    # returns true if two vectors exactly match on relevant dimensions; False otherwise
    distance = 0.0
    for i in xrange(len(vect1)):
        if i in relevant:
            # count relevant dimensions only!
            distance += pow((vect1[i] - vect2[i]),2)
    distance = pow(distance,0.5)

    if distance < EXACT_MATCH_THRESHOLD:
        return True
    else:
        return False

def process_parallel(item,template,relevant):
    # this is the processing that happens in parallel across all items
    # this method will be called in a loop
    # get item/target similarity
    # similarity = feature_similarity(item.features, template.features)
    # relevant is the set of relevant dimensions, e.g., color or shape
    similarity = random_sample_feature_match(item.features,template.features,relevant)

    # use similarity to update item threshold
    item.integrator += similarity * random.random() * item.dist_wt # dist_wt is the weighting for the item's distance from fixation

    # 1/18/18: experiment: update priority based on integrator
    item.priority += item.integrator * INTEGRATOR_GUIDED_PRIORITY
    if item.priority < 0:
        item.priority = 0.0

    # determine whether rejected
    if item.integrator < REJECTION_THRESHOLD:
        # mark the item as rejected
        item.rejected = True
        item.priority = 0.0
        if VERBOSE:
            print str(item.index)+' rejected in parallel phase'

def process_item(item,template,relevant):
    # this is what happens when an item is randomly selected:
    # it is compared to the target template and its integrator is either incremented or decremented
    #   until threshold crossed or max_iterations spent
    # Version 3: max_iterations obviated. Now one iteration, but same item stays selected (in run_search) until done
    """
    Compare one item to the target template for num_iterations iterations
    without attention, num_iterations = 1 (Alejo & Simona's "stage 1")
    with attention, num_iterations = until item crosses upper or lower threshold
    :param item: 
    :param template: 
    :param max_iterations:
    :param relevant: a lst of the dimensions that are relevant for the task
    :return: num_iterations actually processed
    """

    target_found   = False
    num_iterations = 1 # will be set to 2 before returning if exact match nees to be checked

    # get item/target similarity
    #   (get it before entering loop because it will not change: no need to do each time)
    similarity = feature_similarity(item.features, template.features, relevant)

    # DIAG
    # print 'similarity = %.3f'%similarity

    # use similarity to update item threshold
    item.integrator += similarity * item.dist_wt # dist_wt is the effect of this item's distance from fixation

    # and compare integrator to thresholds
    if item.integrator < REJECTION_THRESHOLD:
        # mark the item as rejected
        item.rejected = True
        if VERBOSE:
            print 'selected item '+str(item.index)+' rejected'
        item.priority = 0.0
        item.color    = GRAY
        item = None # mark item unselected so a new one will get selected next time

    elif item.integrator > TARGET_MATCH_TRESHOLD:
        if DOUBLE_CHECK_MATCH:
            # this is the algorithm that does the last-minute double-check
            # this is very likely a target: double check for exact match
            if VERBOSE:
                print 'Selected item '+str(item.index)+' is a serious candidate'
            target_found = exact_match(item.features,template.features,relevant)
            if VERBOSE:
                if target_found:
                    print 'Selected item '+str(item.index)+' has been identified as the target!'
                else:
                    print 'Although a close match, selected item ' + str(item.index) + ' is not the target!'
            # if this was not in fact the target, then mark it rejected
            if not target_found:
                item.rejected = True
                item.priority = 0.0
                item = None  # mark item unselected so a new one will get selected next time
            num_iterations += EXACT_MATCH_COST # add an extra iteration cost for this comparison
        else:
            # this algorithm does no last-second double-check
            target_found = True
            if VERBOSE:
                 print 'Selected item ' + str(item.index) + ' has been identified as the target!'

    return (num_iterations, target_found, item)

def fixate_selected(selected,search_items):
    """
    changes the fixation point to the location of the selected item and recomputes everyone's distance from fixation    
    :param selected: 
    :param search_items: 
    :return: new fixation location
    """
    fixation = list(selected.location)

    for item in search_items:
        distance = 0
        for i in xrange(len(selected.location)):
            distance += (selected.location[i] - item.location[i])**2
        item.fix_dist = pow(distance,0.5)

        # and compute distance_wt: the weighting onthe accumuators as a function of fixation distance
        scaled_distance = DISTANCE_FALLOFF_RATE * item.fix_dist
        item.dist_wt = 1.0/(1.0 + scaled_distance)

    return fixation

def run_search(display, target_template, relevant):
    """
    search the display until target found or all items rejected
    :return: num_iterations (to find target or say no) and whether response was correct
    """
    if VERBOSE:
        print
        print '* * * * * * * * Starting Search * * * * * * * *'

    iteration = 0
    all_done = False # all done with search
    selected = None  # nothing selected yet; stay on selected until rejected or verified
    found_target = None # the item, if any, the model identifies as the target

    fixation = DISPLAY_CENTER # fixation always starts at center of display; if allowed, it will move with attention

    while not all_done:
        # On Each Iteration...
        if VERBOSE:
            print
            print '* * * Iteration '+str(iteration)+' * * *'

        # 0) process all in parallel
        for item in display:
            if not item.rejected:
                process_parallel(item,target_template, relevant)

        # 1) randomly select one item from the set remaining...
        if not selected:
            selected = randomly_select_item(display)
            # if moving fixation is allowed, move fixation to selected
            if PERMIT_EYE_MOVEMENTS:
                fixation = fixate_selected(selected,display)
            # incur the additional time cost for shifting attention
            iteration += ATTENTION_SHIFT_COST
            # and, if verbose, report that a new thing has been selected
            if VERBOSE:
                print ' item ' + str(selected.index) + ' was just selected'

        # 2) evaluate it
        #                                     process_item(item,template,max_iterations)
        if selected:
            (iteration_increment, target_found, selected) = process_item(selected, target_template, relevant)
        else:
            print 'Caution! Nothing selected!'
            print 'Your display items:'
            for item in display:
                if item.rejected:
                    rejected_text = '        True'
                else:
                    rejected_text = 'False       '
                print str(item.index)+') '+rejected_text+' %.2f'%item.priority
            print
            all_done = True # quit
            iteration_increment = 0
            target_found = False

        # 2.2) update iteration counter
        iteration += iteration_increment

        # look to see whether there are any non-rejected items inthe display. if not, halt and declare no target
        if target_found:
            all_done = True
            found_target = selected

            # DIAG
            # print 'found target is at '+str(found_target.location)
        else:
            num_remaining = 0
            for item in display:
                if not(item.rejected):
                    num_remaining += 1
                    break
            if num_remaining == 0:
                iteration += REJECTION_COST_CONSTANT
                all_done = True

        # update the display
        if GRAPHIC:
            show_display(display, iteration, True) # True means pause

    return (iteration, found_target) # if you found a target, then return it



# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * * * Ancillary Functions * * * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

def show_display(search_display, iteration, wait = True):
    """
    graphically show the display with rejected items in gray
    wait means ask the user for a keypress before moving on
    :return: 
    """
    # show the search window
    if CARTESIAN_GRID:
        # draw a square
        x1 = DISPLAY_CENTER[0]-DISPLAY_RADIUS
        y1 = DISPLAY_CENTER[1]-DISPLAY_RADIUS
        width = height = 2*DISPLAY_RADIUS
        rect = (x1,y1,width,height)
        pygame.draw.rect(screen,BLACK,rect,1)
    else:
        # craw a circle
        pygame.draw.circle(screen,BLACK,DISPLAY_CENTER,DISPLAY_RADIUS,1)

    # show the iteration
    simple_tools.blit_text(str(iteration),1)

    # show the items
    for item in search_display:
        item.draw()

    pygame.display.update()

    if wait:
        simple_tools.get_keypress()

def mean_and_sem(data):
    # compute the mean and std. error of mean (sem) of the data
    mean = 0.0
    # get mean & n
    n = len(data)
    if n > 0:
        for datum in data:
            mean += datum
        mean /= n
        # compute sd
        sd = 0.0
        for datum in data:
            sd += pow(datum-mean,2)
        sd = pow(sd,0.5)
        sem = sd/pow(n,0.5)
        return (mean, sem)
    else:
        return None

def save_data(summary_data, filename):
    """
    saves summary data in tab delimited text fiel for easy import to Excel
    summary_data is a list of data entries of the form [num_lures, mean_RT, sem]
    :return: 
    """
    data_file = open(filename,'w')
    # write header
    data_file.write('# dist, RT, sem\n')
    for entry in summary_data:
        text_parts = [] # will be a list of strings: the elements of the entry stringified, with a carriage return at the end
        for item in entry:
            text_parts.append(str(item))
        text_parts.append('\n')
        line = '\t'.join(text_parts)
        data_file.write(line)
    data_file.close()

def item_comparison(target, display_items, relevant):
    """
    compares the feature vectors of all search items to the target template
    :param items: 
    :return: 
    """
    # prepare to show the relevant dimensions
    relevant_list = []
    for i in xrange(len(target.features)):
        if i in relevant:
            relevant_list.append(1)
        else:
            relevant_list.append(0)
    print 'Relevant dimensions: '+str(relevant_list)
    print 'The target is:       '+str(target.features)
    print 'Similarity of Target to...'
    for item in display_items:
        similarity = feature_similarity(item.features, target.features, relevant)
        #    'The target is:       '
        print item.name+'         ('+str(item.features)+'): %.3f'%similarity


# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * * * Simulations * * * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *

def simulation1(num_lures):
    # DIAG
    # print 'entering simulation1()'

    # an easy search: red vertical target among green horizontal distractors

    # 1) make the search template...
    template = VisualItem(None, make_feature_vector('red', 'vertical'))

    # 1.1) ... and define the relevant dimension(s)
    relevant = COLOR_DIMENSIONS

    # 2) make the search display
    search_display = []
    # 2.1) add the target
    #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
    search_display = make_search_items(search_display, 1, 'red', 'vertical', 'Target', True)
    # make_search_items(1, 'red', 'vertical', search_display, [0, 0], 'Target', True)

    # 2.2) add the lures: green horizontals
    #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
    search_display = make_search_items(search_display, num_lures, 'green', 'vertical', 'GrnVertLure', False)

    # 2.3) finally, locate the items in the display
    search_display = assign_locations(search_display)

    # 2.4) allow the user to view the display
    if GRAPHIC:
        show_display(search_display, 0, True) # True means wait for keypress

    # 3) run the search
    (RT, found_target) = run_search(search_display, template, relevant)

    if VERBOSE or GRAPHIC:
        if found_target:
            print 'Target found at '+str(found_target.location)+' after '+str(RT)+' iterations'
        else:
            print 'Target not found after ' + str(RT) + ' iterations'

    # 4) report the results
    return RT

def simulation2(num_lures):
    # DIAG
    # print 'entering simulation2()'

    # a hard search: red vertical target among green vertical and red horizontal distractors

    # 1) make the search template...
    template = VisualItem(None, make_feature_vector('red', 'vertical'))

    # 1.1) ... and define the relevant dimension(s)
    relevant = COLOR_DIMENSIONS + SHAPE_DIMENSIONS # this + operation concatenates the vectors

    # 2) make the search display
    search_display = []

    # 2.1) add the target
    #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
    search_display = make_search_items(search_display, 1, 'red', 'vertical', 'Target', True)

    # 2.2) add the lures:

    # 2.2.1) the number of each Kind of lure is 1/2 the total number of lures
    num_kind_lures = num_lures/2

    # 2.2.2)green verticals
    #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
    search_display = make_search_items(search_display, num_kind_lures, 'green', 'vertical', 'GrnVertLure', False)

    # 2.2.3)red horizontals
    #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
    search_display = make_search_items(search_display, num_kind_lures, 'red', 'horizontal', 'RedHorizLure', False)

    # 2.3) finally, locate the items in the display
    search_display = assign_locations(search_display,)

    # DIAG -- show item similarity
    # if VERBOSE:
    #     item_comparison(template,search_display,relevant)

    # 2.4) allow the user to view the display
    if GRAPHIC:
        show_display(search_display, 0, True) # True means wait for keypress

    # 3) run the search
    (RT, found_target) = run_search(search_display, template, relevant)

    if VERBOSE or GRAPHIC:
        if found_target:
            print 'Target found at '+str(found_target.location)+' after '+str(RT)+' iterations'
        else:
            print 'Target not found after ' + str(RT) + ' iterations'

    # 4) report the results
    return RT

def run_simulation(target,non_targets,relevant=None):
    """
    Runs a whole simulation
    :param target: a list of the form ['color','shape',n] e.g., ['red','vertical',1] is target present, red vertical
    ['red','vertical',0] is target absent, red vertical
    :param non_targets: a list of lists of the same form ['color','shape',n], e.g.,
    [['red','horizontal',4],['green','vertical',4]] means 4 red horizontals and 4 green verticals,
    :param relevant: which dimensions are relevant. if None, then determine automatically
    otherwise, relevant, set as, e.g., COLOR_DIMENSIONS + SHAPE_DIMENSIONS, specifies it
    :return: RT and whether target was present or absent
    """

    if GRAPHIC:
        screen.fill(LIGHTGRAY)
        pygame.display.update()

    # 1) make the search template...
    template = VisualItem(None, make_feature_vector(target[0], target[1])) # target[0] is color, target[1] is shape

    # 2) define the relevant dimension(s)
    if not(relevant):
        # then determine which dimensions are relevant by looking at the distractors and targets
        if len(non_targets) == 1:
            # if there's only one non-target, then the only relevant dimension is the one on which
            #    it differs from the target
            if target[0] != non_targets[0][0]: # target and non_targets differ on color:
                relevant = COLOR_DIMENSIONS
            elif target[1] != non_targets[0][1]: # target & non_targets differ on shape:
                relevant = SHAPE_DIMENSIONS
            else: # target & non-targets identical: flag an error
                print '* * * Woah! run_simulation() got identical target & non-targets! * * *'
                # and make everything relevant by default
                relevant = COLOR_DIMENSIONS + SHAPE_DIMENSIONS
        elif len(non_targets) == 2:
            # if there's more than one kind of non_target, then look for which dimensions differ
            color_differs = False
            shape_differs = False
            for non_target in non_targets:
                if target[0] != non_target[0]:
                    color_differs = True
                if target[1] != non_target[1]:
                    shape_differs = True
            # DIAG
            # print 'color differs = '+str(color_differs)
            # print 'shape differs = '+str(shape_differs)

            if color_differs and shape_differs:
                relevant = COLOR_DIMENSIONS + SHAPE_DIMENSIONS
            elif color_differs:
                relevant = COLOR_DIMENSIONS
            elif shape_differs:
                relevant = SHAPE_DIMENSIONS
            else: # flag an error
                print '* * * Woah! No color or shape differences in run_simulation() * * *'
                # and make everything relevant by default
                relevant = COLOR_DIMENSIONS + SHAPE_DIMENSIONS

            # DIAG
            # print 'relevant dimensions = '+str(relevant)

    # 3) make the search display
    search_display = []

    # 3.1) if target present, then add the target
    if target[2] == 1: # if there's a non-zero value for num_targets...
        # ... then add the target to the display as the 0th item:
        #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
        name = 'Target='+target[0]+'_'+target[1]
        search_display = make_search_items(search_display, target[2], target[0], target[1], name, True)
        target_present = True
    else:
        target_present = False

    # 3.2) add the non-targets:
    for non_target in non_targets:
        #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
        name = 'Lure='+non_target[0]+'_'+non_target[1]
        search_display = make_search_items(search_display, non_target[2], non_target[0], non_target[1], name, False)

    # 4) finally, locate the items in the display
    search_display = assign_locations(search_display)

    # DIAG -- show item similarity
    # if VERBOSE:
    #     item_comparison(template, search_display, relevant)

    # 5) allow the user to view the display
    if GRAPHIC:
        show_display(search_display, 0, True)  # True means wait for keypress

    # 6) run the search
    (RT, found_target) = run_search(search_display, template, relevant)

    if VERBOSE or GRAPHIC:
        if found_target:
            print 'Target found at ' + str(found_target.location) + ' after ' + str(RT) + ' iterations'
        else:
            print 'Target not found after ' + str(RT) + ' iterations'

    # 7) determine whether response was correct
    if target_present:
        if found_target:
            correct = True
            if VERBOSE:
                print 'Correct Response: HIT: '+found_target.name
        else:
            correct = False
            if VERBOSE:
                print 'INcorrect Response: MISS'
    else:
        if found_target:
            correct = False
            if VERBOSE:
                print 'INcorrect Response: FALSE ALARM: '+found_target.name
        else:
            correct = True
            if VERBOSE:
                print 'Correct Response: CORRECT REJECTION'


    # 7) report the results
    return [RT, correct]

# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * * * * Main Body * * * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *

if GRAPHIC:
    screen.fill(LIGHTGRAY)
    pygame.display.update()

print

if VERBOSE or GRAPHIC:
    print
    print "simulation1(16)"
    rt = simulation1(16) # run one simulation with 8 lures -- old syntax
    print 'RT = '+str(rt)

    print
    print "run(simulation(['red','vertical',0],[['green','vertical',16]])"
    print
    print '* * * Feature Search: red vertical among green vertical: 16 distractors, target present'
    [RT, target] = run_simulation(['red','vertical',1],[['green','vertical',16]])
    # the above arguments to run_simulation are: [target], non-target(s)
    print
    print
    print "run(simulation(['red','vertical',1],[['green','vertical',16]])"
    print
    print '* * * Feature Search: red vertical Absent among green vertical: 16 distractors, target present'
    [RT, target] = run_simulation(['red','vertical',0],[['green','vertical',16]])
    print
    print '* * * Conjunction search: red vertical among green vertical and red horizontal: 16 distractors, target present'
    [RT, target] = run_simulation(['red', 'vertical', 1], [['green', 'vertical', 8],['red','horizontal',8]])
    print
    print '* * * Conjunction search: red vertical Absent among green vertical and red horizontal: 16 distractors, target present'
    [RT, target] = run_simulation(['red', 'vertical', 0], [['green', 'vertical', 8], ['red', 'horizontal', 8]])

else: # not verbose: run many simulations
    NumRunsPer = 200

    # * * * * * feature searches * * * * *
    search_text = 'feat'
    for num_target in (0,1): # target absent and target present
        print
        if num_target:
            target_text = '-pres' # for the filename
        else:
            target_text = '-abs'  # for the filename
        summary_data = [] # for writing summaries over runs to file
        for num_lures in (2,4,8,12,16): # these are number of lures per type
            data = []
            for i in xrange(NumRunsPer):
                # data.append(simulation2(num_lures)) # old syntax
                [RT,correct] = run_simulation(['red','vertical',num_target],[['green','vertical',num_lures]])
                if correct: # count correct responses only
                    data.append(RT)
            [mean, sem] = mean_and_sem(data)
            print str(num_lures)+' lure '+search_text+' search, target'+target_text+', Mean RT (sem) = %.3f, %.3f'%(mean, sem)

            summary_data.append([num_lures,mean,sem])
        # save the data to file
        save_data(summary_data,search_text+target_text+'.txt')

    # * * * * * conjunction searches * * * * *
    search_text = 'conj'
    for num_target in (0, 1):  # target absent and target present
        print
        if num_target:
            target_text = '-pres'  # for the filename
        else:
            target_text = '-abs'  # for the filename
        summary_data = []  # for writing summaries over runs to file
        for num_lures in (1, 2, 4, 6, 8):  # these are number of lures Per Type: total lures is twice this
            data = []
            for i in xrange(NumRunsPer):
                # data.append(simulation2(num_lures)) # old syntax
                [RT, target] = run_simulation(['red', 'vertical', num_target],
                                              [['green', 'vertical', num_lures],
                                               ['red', 'horizontal', num_lures]])
                data.append(RT)
            [mean, sem] = mean_and_sem(data)
            print str(num_lures*2)+' lure '+search_text+' search, target'+target_text+', Mean RT (sem) = %.3f, %.3f'%(mean, sem)
            summary_data.append([num_lures*2, mean, sem])
        # save the data to file
        save_data(summary_data, search_text + target_text + '.txt')

if GRAPHIC:
    pygame.display.quit()
