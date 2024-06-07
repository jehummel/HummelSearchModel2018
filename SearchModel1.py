__author__ = 'john'

# * * * * * * * * * Search Model  First attempt to implement the model I think can account for Alejo & Simona's data  1/16/19

# Model stochastically samples locations, rejecting or accepting them as a function of an accumulator that either crosses threshold or not
# AlejoModel2 (1/17/19): For unattended stimuli, stochastically sample dimensions, with greater weight on relevant (attended) ones
# AlejoModel3 (1/17/19): Process attended & unattended genuinely in parallel: one iteration for selected for each w/ everything else
# AlejoModel4 (1/28/19): Implement location, eye movements and graphics: First complete version

# SearchModel1 (1/31/19): make the model itself an object, independent of teh inetrface

# last modified 2/14/19

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

        # the fixed parts
        self.name      = name
        self.is_target = is_target  # a boolean that specifies whether this item (in the visual display) is the target
        if my_list:
            self.index = len(my_list)
        else:
            self.index = 0

        self.color           = color_name # this will be a string like 'red'
        self.shape           = shape_name # this will be a string like 'vertical' or 'L1' which will tell the interface what to draw
        self.features        = feature_vector # this is a feature vector: will get compared to the template during search
        self.vector_length   = 0.0 # vector length: will be computed based on what's relevant below

        # the moving parts
        self.location   = None # location on the screen, in [x,y] coordinates
        self.fix_dist   = 0.0 # distance from fixation
        self.dist_wt    = 1.0 # weighting on the acculumlator as a function of the distance from fixation
        self.integrator = 0 # the thing that, when it passes upper theshold, registers match (i.e., target found) and when below neg threshold registers mismatch (rejection)
        self.rejected   = False # item is rejected when integrator goes below negative threshold; ceases to be functional part of search
        self.currently_selected = False

        # for search/random selection on iteration-by-iteration basis
        self.priority   = 1.0 # this is a combination of salience, etc. When priority = 0, item has no chance of being selected; self.rejected, priority = 0
        self.subrange   = [0.0,0.0] # selection range: the subrange within [0...1] in which random.random() must fall in order for this guy to be selected

    def get_vector_length(self,relevant,relevant_weight,irrelevant_weight):
        length = 0.0
        for i in xrange(len(self.features)):
            if i in relevant:
                weight = relevant_weight
            else:
                weight = irrelevant_weight
            length += (self.features[i] * weight)**2
        length = pow(length,0.5)
        self.vector_length = length


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

import random, math, trig


# * * * * * * * * * * * * * * * * * * * * * * * * * * *
# * * * * * * * * The Model Itself * * * * * * * * * *
# * * * * * * * * * * * * * * * * * * * * * * * * * * *


class SearchModel(object):
    def __init__(self):

        self.LAST_MODIFIED               = '2/14/19'
        # 2/12 change from 1/31: modulated effect of distance from fixation by radius of display
        # 2/14 change frm 1/12: add capacity for linear distance cost

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # * * * * * * * * Major, Theory-relevant Parameters * * * * * * * * *
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

        # Search item rejection and acceptance parameters
        self.TARGET_MATCH_THRESHOLD      = 2 # 4 # 8 # 16 # 4 # 2 # the threshold an item's integrator must exceed to be matched as the target
        self.REJECTION_THRESHOLD         = -2.0 # -4.0 # -1.0 # -0.5  # the negative threshold an item's integrator must reach to be rejected from search altogether
        self.EXACT_MATCH_THRESHOLD       = 0.01 # euclidean distance below which two vectors are considered an exact match
        self.TARGET_ABSENT_COST          = 2 # 3 10 # just a constant added to RT due to rejections

        # for random sampling during inattention
        self.P_RELEVANT_SAMPLING        = 0.9 # 0.7 # 0.5 # 0.1 # 0.95# 0.7 # 1.0 # 0.5 # p(sampling) a relevant dimension in unattended processing
        self.P_IRRELEVANT_SAMPLING      = 0.1 # 0.01 # 0.05 # 0 # 0.05 # p(sampling) an irrelevant dimension in unattended processing
        self.MIN_SELECTION_PRIORITY     = 0.1 # the smallest selection priority for non-rejected items is allowed to go

        # effect of distance between fixation and item location in the display: how much does distance from fixation impair the rate of feature sampling:
        self.DISTANCE_FALLOFF_RATE      = 1.0 # Larger means sharper falloff with distance; effect of distance modulated by DISPLAY_RADIUS
        self.LINEAR_DISTANCE_COST       = True # try a linear dropoff with distance

        # for feature weighting under selected processing
        self.RELEVANT_WEIGHT            = 1.0 # how much relevant dimensions contribute to similarity
        self.IRRELEVANT_WEIGHT          = 0 # 0.01 # how much irrelevant dimensions contribute to similarity
        # non-cosine algorithm
        self.MISMATCH_BIAS              = 10  # how much does a mismatching feature hurt matching compared to a matching feature helping it
        # cosine algorithm algorithm (2/2/19)
        self.COSINE_THRESHOLD           = 0.8 # cosines below this threshold are treated as negative
        self.COSINE_GAIN                = 1.0/(1.0 - self.COSINE_THRESHOLD) # so that cosine = 1 --> 1.0

        # operation cost parameters
        self.ATTENTION_SHIFT_COST       = 2 # how many iterations does it cost to switch attention to a new item
        # self.DOUBLE_CHECK_MATCH         = False # do the conservative distance check on matching item and add cost
        # self.EXACT_MATCH_COST           = 1 # how many iterations does it take to compute the final, exact match for target verification

        # search behavior parameters
        self.INTEGRATOR_GUIDED_PRIORITY = 0.1 #  1.0 # [0...1]: degree to which an item's integrator influences it's selection priority: influence means better-matching items are more likely to be selected for evaluation
        self.PERMIT_EYE_MOVEMENTS       = False # whether model is allowed to change fixation when it moves attention
        self.EYE_MOVEMENT_TIME_COST     = 3 # how long it takes to move the eyes

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # * * * * * * * * Display Characteristics * * * * * * * * *
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

        self.ITEM_RADIUS               = 10  # radius of a single search item on the screen. in the case of square items, this is 1/2 the size of a side
        self.ITEM_DISTANCE             = 22  # the distance between adjacent items' upper left (x,y) coordinates: needs to be 2 * ITEM_RADIUS, plus a buffer

        self.CARTESIAN_GRID            = True  # the display grid is cartesian; if False, then it's polar

        self.DISPLAY_CENTER            = (300, 300)  # the center of the search display, in screen coordinates. will also be the initial location of fixation
        self.DISPLAY_RADIUS            = 200  # 150
        # the following is only for use with linear dropoff: the distance at which the distance weight intersects zero
        self.DISTANCE_AT_ZERO           = int(self.DISPLAY_RADIUS * 1.5) # distance weight goes to zero at 1.5 times the radius of the display


        # * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # * * * * * * * * Major Data Structures * * * * * * * *
        # * * * * * * * * * * * * * * * * * * * * * * * * * * *

        # feature dimension indices (1/17/19). Check these against make_feature_vector for consistency

        self.COLOR_DIMENSIONS = ( 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,16,17) #  0...17 = 18
        self.SHAPE_DIMENSIONS = (18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36)    # 18...36 = 19

        self.search_template  = None # this is the template the model will search for
        self.search_items     = []   # the list of items through which the model will search; will get pared down until it's empty as items get rejected
        self.viable_items     = []   # the list of search items that are still viable
        self.rejected_items   = []   # a list of serach items that have been rejected
        self.num_lures        = 0    # hte number of non-targets in the display
        self.selected_item    = None # the item that is the current focus of attention
        self.attn_shift_timer = 0    # a timer that counts down to permit attention shift
        self.relevant         = []   # the list of relevant dimensions
        self.fixation         = self.DISPLAY_CENTER # the locatin of fixation
        self.iteration        = 0
        self.target_found     = False  # boolean indicating whether the target was found
        self.found_target     = None   # a pointer to the target that was found
        self.correct          = False # did the model get the correct answer

        # response stats
        self.num_attended        = 0 # how many things were selected during the run
        self.num_eye_movements   = 0 # how many times de the model move its eyes
        self.num_auto_rejections = 0 # how many things were rejected without being attended

        self.messages         = [] # a list of strings to tell the interface what (if anything) has happened

        self.legal_colors = ('white','black','red','green','blue','yellow','orange','pink')
        self.legal_shapes = ('vertical','horizontal','T1','T2','T3','T4','L1','L2',
                             'L3','L4','D1','D2','X')
    def make_feature_vector(self,color,shape):
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


    def add_search_items(self,num,color,shape,name = '',is_target=False):
        """
        creates a (subset of a) search display: makes num items of color and shape
        num: how many to make
        color: what color to make them
        shape: what shape to make them
        disply_list: the larger search display list to which they will be added
        :return: the list of items in the display
        """
        # get the feature vector
        features = self.make_feature_vector(color,shape)

        # make the required number of these guys
        for i in xrange(num):
            # my_list,feature_vector,color_name='',shape_name='',name='',is_target=False
            self.search_items.append(VisualItem(self.search_items,features,color,shape,name,is_target))


    # * * * * * * * * * * * * * * * * * * * * * * * * * * *
    # * * * * * * * * * Search Display * * * * * * * * * *
    # * * * * * * * * * * * * * * * * * * * * * * * * * * *

    def make_cartesian_locations(self):
        """
        Makes a list of locations on an (x,y) cartesian grid for stimuli. 
        param: display_space: a rectangle [center_x,center_y,half_width], center_x and center_y are the coordinates of the center of the display and half_width is half the width of the full display (like a radius)
        :return: a list of locations in a randomized order (random.shuffle()); each location is only (upper_left,upper_right), expressed in screen coordinates
        """
        locations = []
        min_x = self.DISPLAY_CENTER[0] - self.DISPLAY_RADIUS
        max_x = min_x + 2*self.DISPLAY_RADIUS - 2*self.ITEM_RADIUS
        min_y = self.DISPLAY_CENTER[1] - self.DISPLAY_RADIUS
        max_y = min_y + 2*self.DISPLAY_RADIUS - 2*self.ITEM_RADIUS

        xpos = min_x # start in upper left: center_x minus half_width
        while (xpos+self.ITEM_RADIUS) <= max_x: # while you're not wider than the display...
            ypos = min_y  # start in upper left: center_y minus half_width
            while (ypos+self.ITEM_RADIUS) <= max_y: # while you're not taller than the display
                location = [xpos,ypos]
                locations.append(location)
                ypos += self.ITEM_DISTANCE
                # DIAG
                # print location
            xpos += self.ITEM_DISTANCE

        # the locations are constructed: shuffle and return them
        random.shuffle(locations)
        return locations

    def make_polar_locations(self, dense = False):
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
        radius = self.ITEM_DISTANCE * 2
        while radius+self.ITEM_RADIUS < self.DISPLAY_RADIUS:
            angle = 0
            if dense: # fill as many angles as possible
                # figure out the angle_increment for this radius: it is the fraction of the circumference taken by the item width
                circumference = 2 * math.pi * radius
                distance_increment = self.ITEM_DISTANCE/circumference  # dist. increment is the fraction of the circle you can move
                angle_increment = distance_increment * 2 * math.pi # angle increment is that, expressed in radians basically, the angle increment is set to the number of items that can fit inside the circumference
            else:  # not dense: only fill angles in increments of Pi/8
                angle_increment = math.pi/4.0
            while angle < 2 * math.pi:
                [real_x,real_y] = trig.get_cartesian([radius,angle],self.DISPLAY_CENTER) # get the cartesian coordinates at this radius and angle
                location = [int(round(real_x))-self.ITEM_RADIUS,int(round(real_y))-self.ITEM_RADIUS]                # round it off to integer values and offset by item radius to center @ location
                locations.append(location)                                                                 # and add it to the list
                angle += angle_increment                                                                   # and increment the angle
            if dense: # increment radius by minimum amount
                radius += self.ITEM_DISTANCE
            else:
                radius *= 1.5 # += ITEM_DISTANCE # * 1.5

        # the locations are all made: shuffle & return them
        random.shuffle(locations)
        return locations

    def assign_locations(self):
        """
        assign screen locations to the search items
        :return: the search display, once items have been assigned
        """
        if self.CARTESIAN_GRID:
            locations = self.make_cartesian_locations()
        else:
            locations = self.make_polar_locations()

        # at this point, locations is a randomly ordered set of locations in either cartesian or polar space
        # now iterate through the search_display and assugn these locations ot the search items
        for item in self.search_items:
            item.location = locations.pop(0)


    # * * * * * * * * * * * * * * * * * * * * * * * * * * *
    # * * * * * Major Functions: Search Operations * * * * *
    # * * * * * * * * * * * * * * * * * * * * * * * * * * *

    def init_search(self, verbose_title=''):
        """
        inits all major variables at the start of the search: this called only once per search run
        :return:
        """
        self.viable_items     = list(self.search_items)   # the list of search items that are still viable
        self.rejected_items   = []   # a list of serach items that have been rejected
        self.selected_item    = None # the item that is the current focus of attention
        self.attn_shift_timer = 0    # a timer that counts down to permit attention shift
        self.fixation         = self.DISPLAY_CENTER # the locatin of fixation
        self.iteration        = 0
        self.target_found     = False  # boolean indicating whethr the target was found
        self.found_target     = None   # a pointer to the target that was found
        self.correct          = False # did the model get the correct answer

        self.clear_messages()
        self.messages.append(verbose_title)
        self.messages.append('Fixation at '+str(self.fixation))

        # init the response stats
        self.num_attended        = 0 # how many things were selected during the run
        self.num_eye_movements   = 0 # how many times de the model move its eyes
        self.num_auto_rejections = 0 # how many things were rejected without being attended

        # init the working parts on all the search items
        for item in self.search_items:
            # the working parts
            item.location           = None # location on the screen, in [x,y] coordinates
            item.fix_dist           = 0.0 # distance from fixation
            item.dist_wt            = 1.0 # weighting on the acculumlator as a function of the distance from fixation
            item.integrator         = 0.0 # the thing that, when it passes upper theshold, registers match (i.e., target found) and when below neg threshold registers mismatch (rejection)
            item.rejected           = False # item is rejected when integrator goes below negative threshold; ceases to be functional part of search
            item.currently_selected = False
            item.priority           = 1.0 # this is a combination of salience, etc. When priority = 0, item has no chance of being selected; self.rejected, priority = 0
            item.subrange           = [0.0,0.0] # selection range: the subrange within [0...1] in which random.random() must fall in order for this guy to be selected

        # and assign the items random locations in the display
        self.assign_locations()

        # and set the initial fixation distance weights (new, 2/12/19:previously wasn't doing this till eye movement)
        for item in self.search_items:
            distance = 0
            for i in xrange(len(self.fixation)):
                distance += (self.fixation[i] - item.location[i])**2
            item.fix_dist = pow(distance,0.5)

            # and compute distance_wt: the weighting on the accumuators as a function of fixation distance
            if self.LINEAR_DISTANCE_COST:
                item.dist_wt = 1.0 - (float(item.fix_dist)/self.DISTANCE_AT_ZERO)
                if item.dist_wt < 0.0: item.dist_wt = 0.0
            else: # original (pre-2/14/19) nonlinear distance cost
                scaled_distance = self.DISTANCE_FALLOFF_RATE * (float(item.fix_dist)/self.DISPLAY_RADIUS)
                item.dist_wt = 1.0/(1.0 + scaled_distance)


    def randomly_select_item(self):
        # randomly selects one viable search item based on all viable items' priorities

        # 1) calculate the sum of all items' priorities
        priority_sum = 0.0
        for item in self.viable_items: # self.search_items:
            # make sure rejected items stay rejected
            if item.rejected: item.priority = 0
            priority_sum += item.priority
            item.currently_selected = False # init all to False at this point

        # 2) assign each item a subrange: a subset of the range [0...1] whose width is proportional to item/priority/priority_sum
        if priority_sum > 0:
            range_bottom = 0.0
            for item in self.viable_items: # self.search_items:
                range_top = range_bottom + item.priority/priority_sum # range width = range_bottom...range_top = item.priority/priority_sum
                item.subrange = [range_bottom,range_top]
                range_bottom = range_top

        # 3) get a random number in [0...1] and select as chosen the item whose subrange includes that number
        the_number = random.random()
        for item in self.viable_items: # self.search_items:
            if the_number >= item.subrange[0] and the_number < item.subrange[1]:
                item.currently_selected = True
                self.num_attended += 1 # increment the number of things attended
                return item

        # 4) if you get to this point, you found nothing: return None
        return None

    def random_sample_feature_match(self,vect):
        # for unattended processing: decide vect1-vect2 similarity by randomly sampling
        #   dimensions
        # return num_matches - num_mismatches
        match = 0
        # len1 = 0
        # len2 = 0
        for i in xrange(len(self.search_template.features)):
            # randomly sample dimension i depending on whether it's in the relevant set
            if i in self.relevant:
                do_sample = random.random() < self.P_RELEVANT_SAMPLING
            else:
                do_sample = random.random() < self.P_IRRELEVANT_SAMPLING
            if do_sample:
                # sample this dimension:

                # Version 1:
                # if the vectors both 1, then add 1;
                # if they are different, then subtract 1
                if vect[i] or self.search_template.features[i]: # if at least one is active...
                    if vect[i] == self.search_template.features[i]: match += 1
                    else: match += -1

                # Version2: simple product
                # match += vect1[i] * vect2[i]

                # Version 2b: cosine
                # len1 += pow(vect1[i], 2)
                # len2 += pow(vect2[i], 2)
        # now normalize the match score by the max possible
        match /= len(self.relevant)

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

    # used prior to 2/2/19
    # def feature_similarity(self,vect):
    #     """
    #     Determines whether vect of features is a match or a mismatch to self.search_template on the relevant dimensions.
    #     This version does NOT work by a simple dot product or cosine:
    #     Mismatches have to matter Much more than matches.
    #     This version computes a mismatch score and returns that; returns a positive score if mismatch is zero
    #
    #     :param vect: one of the two vectors to be compared
    #     :return:
    #     """
    #     match_sum    = 0
    #     mismatch_sum = 0
    #     for i in xrange(len(self.search_template.features)):
    #         if i in self.relevant:
    #             weight = self.RELEVANT_WEIGHT
    #         else:
    #             weight = self.IRRELEVANT_WEIGHT
    #         if vect[i] == self.search_template.features[i]:
    #             match_sum += weight
    #         else:
    #             mismatch_sum += weight * self.MISMATCH_BIAS
    #
    #     # now, probabilistically return a -1 or a 1 as a function of match_sum - mismatch_sum
    #     probability = 1.0/(1+pow(math.e,-(match_sum-mismatch_sum)))
    #
    #     if random.random() < probability:
    #         return 1
    #     else:
    #         return -1

    # conservative cosine similarity with a threshold criterion:  2/2/19
    # values below threshold are treated as negative
    def feature_similarity(self, search_item):
        # returns the vector similarity of two vector1 and vector2
        # uses cosine relative to threshold self.COSINE_THRESHOLD
        # cosines less than this are treated as negative
        # len1        = 0.0 # length of vector1
        # len2        = 0.0 # length of vector2
        dot_product = 0.0
        for i in xrange(len(search_item.features)):
            # determine feature weight based on relevance
            if i in self.relevant: # if i is a feature along the relevant dimension
                weight = self.RELEVANT_WEIGHT
            else:
                weight = self.IRRELEVANT_WEIGHT
            # len1 += pow(vector[i],2)
            # len2 += pow(self.search_template.features[i] * weight,2)
            dot_product += search_item.features[i] * self.search_template.features[i] * weight # * weight
        # len1 = pow(len1,0.5)
        # len2 = pow(len2,0.5)
        len_product = search_item.vector_length * self.search_template.vector_length
        cosine = 0
        if len_product > 0:
            cosine = dot_product/len_product

        # the value returned
        return (cosine - self.COSINE_THRESHOLD) * self.COSINE_GAIN

    # def exact_match(self,vect):
    #     # returns true if vect exactly matches search template on relevant dimensions
    #     distance = 0.0
    #     for i in xrange(len(vect)):
    #         if i in self.relevant:
    #             # count relevant dimensions only!
    #             distance += pow((vect[i] - self.search_template.features[i]),2)
    #     distance = pow(distance,0.5)
    #
    #     if distance < self.EXACT_MATCH_THRESHOLD:
    #         return True
    #     else:
    #         return False

    def process_parallel(self,item):
        # this is the processing that happens in parallel across all items
        # this method will be called in a loop
        # get item/target similarity
        # similarity = feature_similarity(item.features, template.features)
        # relevant is the set of relevant dimensions, e.g., color or shape
        similarity = self.random_sample_feature_match(item.features)

        # use similarity to update item threshold
        #ToDo: Should parallel computation be affected by distance from fixatrion? If so, should it be as much as seective processing is?
        item.integrator += similarity * random.random() * item.dist_wt # distance weighting removed 2/14/19: This is supposed to be a LOCAL computation!

        # 1/18/18: experiment: update priority based on integrator
        item.priority += item.integrator * self.INTEGRATOR_GUIDED_PRIORITY
        if item.priority < self.MIN_SELECTION_PRIORITY:
            item.priority = self.MIN_SELECTION_PRIORITY

        # determine whether rejected
        if item.integrator < self.REJECTION_THRESHOLD:
            # mark the item as rejected
            item.rejected = True
            item.priority = 0.0

            # for reporting
            self.make_message('----------'+str(item.index)+' rejected in parallel phase---------')

            self.num_auto_rejections += 1  # record that this was rejected without being attended

    def process_selected_item(self):
        # this is what happens when an item is randomly selected:
        # it is compared to the target template and its integrator is either incremented or decremented
        #   until threshold crossed or max_iterations spent
        # Version 3: max_iterations obviated. Now one iteration, but same item stays selected (in run_search) until done
        """
        Compare one item to the target template for num_iterations iterations
        without attention, num_iterations = 1 (Alejo & Simona's "stage 1")
        with attention, num_iterations = until item crosses upper or lower threshold
        :param item: 
        :return: num_iterations actually processed
        """

        self.target_found   = False

        # get item/target similarity
        #   (get it before entering loop because it will not change: no need to do each time)
        similarity = self.feature_similarity(self.selected_item)

         # use similarity to update item threshold
        delta = similarity * self.selected_item.dist_wt # dist_wt is the effect of this item's distance from fixation
        self.selected_item.integrator += delta # similarity * self.selected_item.dist_wt # dist_wt is the effect of this item's distance from fixation
        # record the delta for the verbose mode
        self.make_message('Selected item fix. dist. = %.3f, integrator change = %.4f, integrator = %.3f'%(self.selected_item.fix_dist,delta,self.selected_item.integrator))

        # and compare integrator to thresholds
        if self.selected_item.integrator < self.REJECTION_THRESHOLD:
            # mark the item as rejected
            self.selected_item.rejected = True
            self.selected_item.priority = 0.0
            self.selected_item.currently_selected = False

            # for reporting
            self.make_message('Selected item '+str(self.selected_item.index)+' rejected')

            # finally, note that no item is currently selected
            self.selected_item          = None # mark item unselected so a new one will get selected next time

        elif self.selected_item.integrator > self.TARGET_MATCH_THRESHOLD:
            # if self.DOUBLE_CHECK_MATCH:
            #     # this is the algorithm that does the last-minute double-check
            #     # this is very likely a target: double check for exact match
            #     self.make_message('Selected item '+str(self.selected_item.index)+' is a serious candidate')
            #
            #     self.target_found = self.exact_match(self.selected_item.features)
            #
            #     if self.target_found:
            #         self.make_message('Selected item '+str(self.selected_item.index)+' has been identified as the target!')
            #         self.found_target = self.selected_item
            #     else:
            #         self.make_message('Although a close match, selected item ' + str(self.selected_item.index) + ' is not the target!')
            #         self.selected_item.rejected = True
            #         self.selected_item.priority = 0.0
            #         self.selected_item          = None  # mark item unselected so a new one will get selected next time
            #     self.iteration += self.EXACT_MATCH_COST # add an extra iteration cost for this comparison
            # else:
            # this algorithm does no last-second double-check
            self.target_found = True
            self.found_target = self.selected_item
            self.make_message('Selected item ' + str(self.selected_item.index) + ' has been identified as the target!')

    def fixate_selected(self):
        """
        changes the fixation point to the location of the selected item and recomputes everyone's distance from fixation    
        """
        self.fixation = list(self.selected_item.location)

        self.make_message('Fixation moved to '+str(self.fixation))
        self.num_eye_movements += 1  # how many times de the model move its eyes

        for item in self.search_items:
            distance = 0
            for i in xrange(len(self.fixation)):
                distance += (self.fixation[i] - item.location[i])**2
            item.fix_dist = pow(distance,0.5)

            # and compute distance_wt: the weighting onthe accumuators as a function of fixation distance
            # and compute distance_wt: the weighting on the accumuators as a function of fixation distance
            if self.LINEAR_DISTANCE_COST:
                item.dist_wt = 1.0 - (float(item.fix_dist)/self.DISTANCE_AT_ZERO)
                if item.dist_wt < 0.0: item.dist_wt = 0.0
            else: # original (pre-2/14/19) nonlinear distance cost
                scaled_distance = self.DISTANCE_FALLOFF_RATE * (float(item.fix_dist)/self.DISPLAY_RADIUS)
                item.dist_wt = 1.0/(1.0 + scaled_distance)

    def update_viability(self):
        """
        moves rejected items to the rejected_items list leaving only viable items (.rejected = False) to the search_items list
        :return: 
        """
        still_viable_items   = [] # a holding pen for those items that are still viable
        # go through all items and either put them in the (temporary) viable list or in the rejected list
        for item in self.viable_items:
            if item.rejected:
                item.currently_selected = False
                self.rejected_items.append(item)
            else:
                still_viable_items.append(item)
        # now reset self.search_items to be just the viable ones
        self.viable_items = still_viable_items

    def run_search_step(self):
        """
        runs one step of the search: this will be called repeatedly by the interface
        """

        all_done = False # all done with search

        # update iteration counter
        self.iteration += 1

        # On Each Iteration...
        self.messages.append('\n* * * Iteration '+str(self.iteration)+' * * *')

        # 0) process all the remaining (viable) in parallel
        for item in self.viable_items: # self.search_items:
            if not item.rejected:
                self.process_parallel(item)

        # 1) move all the rejected items to the self.rejected_items list -- that's in update_viability
        self.update_viability()

        # 2) if nothing is yet the focus of attention, then randomly select one item
        #    from the set remaining...
        if not self.selected_item:
            self.selected_item = self.randomly_select_item()

            # if you found something, then start the timers to shift attention and move the eyes
            if self.selected_item:
                # start the timer to actually get attention to selected item
                self.attn_shift_timer = self.ATTENTION_SHIFT_COST

                # report that a new thing has been selected
                self.make_message('Moving attention to item '+ str(self.selected_item.index)+' at '+str(self.selected_item.location))

        # 3) process selected item
        if self.selected_item:

            # 3.A) if the timer has counted down to zero, then attention has just now gotten to
            #      the selected item...
            if self.attn_shift_timer == 0:
                self.make_message('Attention arrived on item '+str(self.selected_item.index))
                # 3.A.1) move the eyes to the item (if allowed)
                if self.PERMIT_EYE_MOVEMENTS:
                    # 3.A.1.1) pay the eye movement cost:
                    # Simply adding the iterations in this way is tantamount to suspending all
                    #   processing, including unattended processing, during the eye movement
                    self.iteration += self.EYE_MOVEMENT_TIME_COST
                    # 3.A.1.2) and fixate the attended item
                    self.fixate_selected()
                # 3.A.2) process the selected item
                self.process_selected_item()
                # 3.A.3) decrement the attention_shift_timer to -1 so that
                #        3.A.1 is not repeated next time
                self.attn_shift_timer = -1

            # 3.B) if the timer is less than zero, then you're already at the selected item:
            #      just process it
            elif self.attn_shift_timer < 0:
                self.process_selected_item()

            # 3.C) otherwise, the timer is still > 0: just decrement the timer
            else:
                self.attn_shift_timer -= 1

        # else:
        #     self.make_message('Nothing selected! Number of remaining viable items = '+str(len(self.viable_items)))
        #     viable_list = []
        #     for item in self.viable_items:
        #         viable_list.append('[%2i = %.4f]'%(item.index,item.priority))
        #     self.make_message('These are the viable items remaining: '+str(viable_list))
        #     all_done = True # quit
        #     self.target_found = False

        # 4) move all the rejected items to the self.rejected_items list -- that's in update_viability
        self.update_viability()

        # 5) look to see whether you're done. you're done when
        # (a) you've found the target, or
        # (b) there are no non-rejected items in the display. if not, halt and declare no target
        if self.target_found:
            self.found_target = self.selected_item
            self.make_message('Target Found! Item ' + str(self.selected_item.index) + ', '+self.selected_item.name+ ' at ' + str(self.selected_item.location) + ' on iteration '+str(self.iteration)+'\n')
            all_done = True

        elif len(self.viable_items) == 0:
            self.iteration += self.TARGET_ABSENT_COST
            self.make_message('I have concluded the Target is Absent on iteration ' + str(self.iteration) + '\n')
            all_done = True

        return all_done # let whoever called you know whether the simulation is done

    def analyze_result(self):
        """
        at the end of the search, determines whether it got the search right or wrong
        :return: 
        """

        if self.target_found:
            # you found something. make sure it's the target
            self.correct = self.found_target.is_target
        else:
            # you found nothing. make sure there was no target in the display
            correct = True
            for item in self.search_items:
                if item.is_target:
                    correct = False # there was a target and you missed it
                    break
            self.correct = correct

    def run_whole_search(self,verbose_title=''):
        """
        this runs the whole search. if you're calling ths, then you aren't using graphics
        If you wanna use graphics, then use the interface to run the search one iteraiton at a time
        :return: 
        """
        self.init_search(verbose_title)
        all_done = False
        while not all_done:
            all_done = self.run_search_step()
        self.analyze_result() # determine whether your response was correct

    def create_simulation(self,target,non_targets,relevant=None):
        """
        Creates the data structures for a simulation (or batch run thereof)
        :param target: a list of the form ['color','shape',n] e.g., ['red','vertical',1] is target present, red vertical
        ['red','vertical',0] is target absent, red vertical
        :param non_targets: a list of lists of the same form ['color','shape',n], e.g.,
        [['red','horizontal',4],['green','vertical',4]] means 4 red horizontals and 4 green verticals,
        :param relevant: which dimensions are relevant. if None, then determine automatically
        otherwise, relevant, set as, e.g., COLOR_DIMENSIONS + SHAPE_DIMENSIONS, specifies it
        """

        # 1) make the search template...
        self.search_template = VisualItem(None, self.make_feature_vector(target[0], target[1]))  # target[0] is color, target[1] is shape

        # 2) define the relevant dimension(s)
        if relevant:
            # user-defined relevance
            self.relevant = relevant
        else:
            # determine relevance automatically: then determine which dimensions are relevant by looking at the distractors and targets
            if len(non_targets) == 1:
                # if there's only one non-target, then the only relevant dimension is the one on which
                #    it differs from the target
                if target[0] != non_targets[0][0]:  # target and non_targets differ on color:
                    self.relevant = self.COLOR_DIMENSIONS
                elif target[1] != non_targets[0][1]:  # target & non_targets differ on shape:
                    self.relevant = self.SHAPE_DIMENSIONS
                else:  # target & non-targets identical: flag an error
                    print '* * * Woah! create_simulation() got identical target & non-targets! * * *'
                    # and make everything relevant by default
                    self.relevant = self.COLOR_DIMENSIONS + self.SHAPE_DIMENSIONS
            elif len(non_targets) == 2:
                # if there's more than one kind of non_target, then look for which dimensions differ
                color_differs = False
                shape_differs = False
                for non_target in non_targets:
                    if target[0] != non_target[0]:
                        color_differs = True
                    if target[1] != non_target[1]:
                        shape_differs = True

                if color_differs and shape_differs:
                    self.relevant = self.COLOR_DIMENSIONS + self.SHAPE_DIMENSIONS
                elif color_differs:
                    self.relevant = self.COLOR_DIMENSIONS
                elif shape_differs:
                    self.relevant = self.SHAPE_DIMENSIONS
                else:  # flag an error
                    print '* * * Woah! No color or shape differences in run_simulation() * * *'
                    # and make everything relevant by default
                    self.relevant = self.COLOR_DIMENSIONS + self.SHAPE_DIMENSIONS

        # 3) make the search items
        self.search_items = []

        # 3.1) if target present, then add the target
        if target[2] == 1:  # if there's a non-zero value for num_targets...
            # ... then add the target to the display as the 0th item:
            #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
            name = 'Target=' + target[0] + '_' + target[1]
            self.add_search_items(target[2], target[0], target[1], name, True)
            self.target_present = True
        else:
            self.target_present = False

        # 3.2) add the non-targets:
        self.num_lures = 0
        for non_target in non_targets:
            #                make_search_items(existing_list,num,color,shape,name = '',is_target=False)
            name = 'Lure=' + non_target[0] + '_' + non_target[1]
            self.add_search_items(non_target[2], non_target[0], non_target[1], name, False)
            self.num_lures += non_target[2]

        # 4) compute the vector lengths of the target template and the search items
        # get_vector_length(self,relevant,relevant_weight,irrelevant_weight)
        # 4.1) the search template
        self.search_template.get_vector_length(self.relevant,self.RELEVANT_WEIGHT,self.IRRELEVANT_WEIGHT)

        # 4.2) the search items
        for item in self.search_items:
            item.get_vector_length(self.relevant,self.RELEVANT_WEIGHT,self.IRRELEVANT_WEIGHT)


    # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
    # * * * * * * * * * * Ancillary Functions * * * * * * * * * * *
    # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

    def item_comparison(self):
        """
        compares the feature vectors of all search items to the target template
         :return: 
        """
        # prepare to show the relevant dimensions
        relevant_list = []
        for i in xrange(len(self.search_template.features)):
            if i in self.relevant:
                relevant_list.append(1)
            else:
                relevant_list.append(0)
        print 'Relevant dimensions: '+str(relevant_list)
        print 'The target is:       '+str(self.search_template.features)
        print 'Similarity of Target to...'
        for item in self.search_items:
            similarity = self.feature_similarity(item.features)
            print item.name+'         ('+str(item.features)+'): %.3f'%similarity

    def clear_messages(self):
        # siimply inits the warnings list
        self.messages = []

    def make_message(self,text):
        # adds a warning to the list
        full_text = 'Iteration '+str(self.iteration)+') '+text
        self.messages.append(full_text)