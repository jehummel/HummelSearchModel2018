__author__ = 'john'

# * * * * * * * * * AlejoModel  First attempt to implement the model I think can account for Alejo & Simona's data  1/16/19

# Model stochastically samples locations, rejecting or accepting them as a function of an accumulator that either crosses threshold or not

# Version 2 (1/17/19): For unattended stimuli, stochastically sample dimensions, with greater weight on relevant (attended) ones

# last modified 1/17/19

# * * * * * * * * * Graphics bullshit * * * * * * * * *

import math, trig, random
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
#
# pygame.init()
#
# # screen set-up
# infoObject = pygame.display.Info()
# screen_width        = 1800 # infoObject.current_w - 100 #1800 # 1024
# screen_height       = infoObject.current_h - 100#1200 # 768
# large_text_height   = 36
# small_text_height   = 18
#
# vert_midline = int(round(screen_width/2)) # the vertical midline
# horiz_midline = int(round(screen_height/2))
#
# # pygame.display.set_mode((infoObject.current_w, infoObject.current_h))
# screen = pygame.display.set_mode((screen_width, screen_height))
# largefont = pygame.font.SysFont('futura', large_text_height)
# smallfont = pygame.font.SysFont('futura', small_text_height)
# pygame.mouse.set_visible(True)
# pygame.font.init()
#
# import simple_tools # some mundane IO functions

# * * * * * * * * * Model-relevant stuff * * * * * * * * *

TARGET_MATCH_TRESHOLD  = 2 # the threshold an item's integrator must exceed to be matched as the target
REJECTION_THRESHOLD    = -1.0 # -0.5  # the negative threshold an item's integrator must reach to be rejected from search altogether

EXACT_MATCH_THRESHOLD  = 0.01 # euclidean distance below which two vectors are considered an exact match

# feature dimension indices (1/17/19). Check these against make_feature_vector for consistency
COLOR_DIMENSIONS = (0,1,2,3,4,5,6,7,8,9,10,11)
SHAPE_DIMENSIONS = (12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28)

# for random sampling during inattention
P_RELEVANT_SAMPLING   = 0.7 # 1.0 # 0.5 # p(sampling) a relevant dimension in unattended processing
P_IRRELEVANT_SAMPLING = 0.05 # 0 # 0.05 # p(sampling) an irrelevant dimension in unattended processing

# for feature weighting under selected processing
RELEVANT_WEIGHT   = 1.0 # how much relevant dimensions contribute to similarity
IRRELEVANT_WEIGHT = 0.1 # how much irrelevant dimensions contribute to similarity

EXACT_MATCH_COST  = 1 # how many iterations does it take to compute the final, exact match for target verification

class VisualItem(object):
    """
    This is the basic VisualItem data class for the model
    VisualItems include the target (in the display), the distractors & lires (which are in the display) and the target template (not in the display)
    """
    def __init__(self,my_list,feature_vector,location=[0,0],name='',is_target=False):
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
        self.color = LIGHTGREEN

        # the working parts
        self.location   = location # location on the screen, in [x,y] coordinates
        self.fix_dist   = 0.0 # distance from fixation
        self.features   = feature_vector # this is a feature vector: will get compared to the template during search
        self.integrator = 0 # the thing that, when it passes upper theshold, registers match (i.e., target found) and when below neg threshold registers mismatch (rejection)
        self.rejected   = False # item is rejected when integrator goes below negative threshold; ceases to be functional part of search

        # for search/random selection on iteration-by-iteration basis
        self.priority   = 1.0 # this is a combination of salience, etc. When priority = 0, item has no chance of being selected; self.rejected, priority = 0
        self.subrange   = [0.0,0.0] # selection range: the subrange within [0...1] in which random.random() must fall in order for this guy to be selected


def randomly_select_item(all_items):
    # takes all visual search items and randomly selects one of them based on their priorities, etc.

    # 1) calculate the sum of all items' priorities
    priority_sum = 0.0
    for item in all_items:
        priority_sum += item.priority

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
            return item

    # 4) if you get to this point, you found nothing: return None
    return None

def random_sample_feature_match(vect1,vect2,relevant):
    # for unattended processing: decide vect1-vect2 similarity by randomly sampling
    #   dimensions
    # return num_matches - num_mismatches
    match = 0
    len1 = 0
    len2 = 0
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
            # if vect1[i] != 0 or vect2[i] != 0: # if at least one is active...
            #     match += (2*vect1[i]-1) * (2*vect2[i]-1) # +1 if same, -1 if diff

            # Version2: simple product
            match += vect1[i] * vect2[i]

            # Version 2b: cosine
            len1 += pow(vect1[i], 2)
            len2 += pow(vect2[i], 2)
    # now normalize the match score by the max possible
    match /= len(relevant)

    # or (2b) by the product of the lengths
    # len1 = pow(len1,0.5)
    # len2 = pow(len2,0.5)
    # if len1 * len2 > 0:
    #     match /= (len1 * len2)
    return match


def feature_similarity(vect1,vect2,relevant):
    # returns the vector similarity of two vector1 and vector2
    # could be cosine, dot product, whatever...
    # for now, we're gonna do cosine
    len1        = 0.0 # length of vector1
    len2        = 0.0 # length of vector2
    dot_product = 0.0
    for i in xrange(len(vect1)):
        # determine feature weight based on relevance
        if i in relevant: # if i is a feature along the relevant dimension
            weight = RELEVANT_WEIGHT
        else:
            weight = IRRELEVANT_WEIGHT
        len1 += pow(vect1[i] * weight,2)
        len2 += pow(vect2[i] * weight,2)
        dot_product += vect1[i] * weight * vect2[i] * weight
    len_product = len1 * len2
    if len_product > 0:
        return dot_product/len_product
    else:
        print "Error! One or more vectors has length zero."
        return None

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
    item.integrator += similarity * random.random()

    # determine whether rejected
    if item.integrator < REJECTION_THRESHOLD:
        # mark the item as rejected
        item.rejected = True
        item.priority = 0.0


def process_item(item,template,relevant,max_iterations=10):
    # this is what happens when an item is randomly selected:
    # it is compared to the target template and its integrator is either incremented or decremented
    #   until threshold crossed or max_iterations spent
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
    num_iterations = 0
    all_done       = False
    target_found   = False

    # get item/target similarity
    #   (get it before entering loop because it will not change: no need to do each time)
    similarity = feature_similarity(item.features, template.features, relevant)

    # DIAG
    # print 'similarity = %.3f'%similarity

    # process the item until all_done; then return num_iterations and target_found
    while not all_done:
        num_iterations += 1

        # use similarity to update item threshold
        item.integrator += similarity

        # and compare integrator to thresholds
        if item.integrator < REJECTION_THRESHOLD:
            # mark the item as rejected
            item.rejected = True
            item.priority = 0.0
            item.color    = GRAY
            all_done      = True

        elif item.integrator > TARGET_MATCH_TRESHOLD:
            # this is very likely a target: double check for exact match
            target_found = exact_match(item.features,template.features,relevant)
            num_iterations += EXACT_MATCH_COST # add an extra iteration cost for this comparison

        # check to see whether all_done: did we find the target? or is num_iterations >= max_iterations
        if target_found or num_iterations >= max_iterations:
            all_done = True

    return (num_iterations, target_found)

def make_feature_vector(color,shape):
    # take names for color and shape and make a corresponding feature vector
    # color vectors are [r,r,r,g,g,g,b,b,b,y,y,y]
    color_vectors = {'red':[1,1,1,-1,-1,-1,0,0,0,0,0,0],    # red = red and Not greem
                     'green':[-1,-1,-1,1,1,1,0,0,0,0,0,0], # green = green and Not red
                     'blue':[0,0,0,0,0,0,1,1,1,-1,-1,-1],  # blue = blue & not yellow
                     'yellow':[0,0,0,0,0,0,-1,-1,-1,1,1,1], # yellow = yellow & blue
                     'orange':[1,1,0,-1,-1,0,-1,0,0,1,0,0]} # orange is 2 red, 2 not green, 1 yellow, 1 not blue
    # shape is v1,v2,h1,h2,d1,d1,d2,d2,L1,L2,L3,L4,T1,T2,T3,T4,X
    shape_vectors = {'vertical':[1,1,-1,-1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                     'horizontal':[-1,-1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                     'T1':[1,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
                     'T2':[1,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
                     'T3':[1,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                     'T4':[1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0],
                     'L1':[1,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0],
                     'L2':[1,0,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
                     'L3':[1,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0],
                     'L4':[1,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0],
                     'D1':[0,0,0,0,1,1,-1,-1,0,0,0,0,0,0,0,0],
                     'D2':[0,0,0,0,-1,-1,1,1,0,0,0,0,0,0,0,0],
                     'X':[0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,1]}
    color_vector = color_vectors[color]
    shape_vector = shape_vectors[shape]
    feature_vector = []
    feature_vector.extend(color_vector)
    feature_vector.extend(shape_vector)

    return feature_vector


def make_search_items(num,color,shape,display_list,location=[0,0],name = '',is_target=False):
    """
    creates a (subset of a) search display: makes num items of color and shape
    num: how many to make
    color: what color to make them
    shape: what shape to make them
    disply_list: the larger search display list to which they will be added
    :return: the list of items in the display
    """
    items = [] # a list of all items to make

    # get the feature vector
    features = make_feature_vector(color,shape)

    # make the required number of these guys
    for i in xrange(num):
        items.append(VisualItem(display_list,features,location,name,is_target))

    # return 'em
    return items

def show_display():
    """
    graphically show the display with rejected items in gray
    :return: 
    """
    pass

def run_search(display, target_template, relevant):
    """
    search the display until target found or all items rejected
    :return: num_iterations (to find target or say no) and whether response was correct
    """
    iteration = 0
    all_done = False # all done with search
    while not all_done:
        # On Each Iteration...

        # 0) process all in parallel
        for item in display:
            process_parallel(item,target_template, relevant)

        # 1) randomly select one item from the set remaining...
        selected = randomly_select_item(display)

        # 2) evaluate it
        #                                     process_item(item,template,max_iterations)
        (iteration_increment, target_found) = process_item(selected, target_template, relevant)

        # 2.2) update iteration counter
        iteration += iteration_increment

        # look to see whether there are any non-rejected items inthe display. if not, halt and declare no target
        if target_found:
            all_done = True
        else:
            num_remaining = 0
            for item in display:
                if not(item.rejected):
                    num_remaining += 1
                    break
            if num_remaining == 0:
                all_done = True

    return (iteration, target_found)


def simulation1(num_lures):
    # an easy search: red vertical target among green horizontal distractors

    # 1) make the search template...
    template = VisualItem(None, make_feature_vector('red', 'vertical'))

    # 1.1) ... and define the relevant dimension(s)
    relevant = COLOR_DIMENSIONS

    # 2) make the search display
    search_display = []
    # 2.1) add the target
    #                 make_search_items(num,color,shape,display_list,location=[0,0],name = '',is_target=False):
    search_display.extend(make_search_items(1, 'red', 'vertical', search_display, [0, 0], 'Target', True))

    # 2.2) add the lures: green horizontals
    search_display.extend(make_search_items(num_lures, 'green', 'horizontal', search_display, [0, 0], 'Target', True))

    # 3) run the search
    (RT, target_found) = run_search(search_display, template, relevant)

    if not target_found:
        print 'Error: Target not found'

    # 4) report the results
    return RT

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


# * * * * * * * * * * Main Body * * * * * * * * * *

NumRunsPer = 200

lure_nums = (3,6,9,12,15)

print

for num_lures in lure_nums:
    data = []
    for i in xrange(NumRunsPer):
        data.append(simulation1(num_lures))
    [mean, sem] = mean_and_sem(data)
    print str(num_lures)+' easy lures. Mean RT (sem) = %.3f, %.3f'%(mean, sem)

