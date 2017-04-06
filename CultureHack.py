################################################################################
################################################################################
#------------------------CULTUREHACK-------------------------------------------#
#----------------------------DESIGN BY BILL MILLET-----------------------------#
#----------------------------PROGRAMMED BY GABE HADDON-HILL--------------------#
################################################################################
################################################################################

#Importing necessary modules
import libtcodpy as libtcod
import math
import textwrap
import shelve

#------------------------Global and Constant Declarations----------------------#
#Constants for root console size
SCREEN_WIDTH = 100
SCREEN_HEIGHT = 60
LIMIT_FPS = 17 #limits the speed that the game updates

INVENTORY_WIDTH = 50

ROOM_MAX_SIZE = 14
ROOM_MIN_SIZE = 1

FOV_ALGO = 0 #FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 30 #FOV radius

HEAL_AMOUNT = 20

ARC_DAMAGE = 90
ARC_RANGE = 5

SHELL_RADIUS = 3
SHELL_DAMAGE = 12

CONFUSE_NUM_TURNS = 15
CONFUSE_RANGE = 8

#constants for map dimensions to fit with GUI panel
MAP_WIDTH = 98
MAP_HEIGHT = 53

#Colours for wall and floor parts of map
color_dark_wall = libtcod.Color(90, 90, 90)
color_dark_ground = libtcod.Color(145,145,145)
color_light_wall = libtcod.Color(60, 110, 110)
color_light_ground = libtcod.Color(198,250,250)

#constants for panel dimensions
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

#constants for experience levelling
BASIC_LEVEL_UP = 300
LEVEL_UP_INCREMENT = 300

#Character info screen width
CHAR_INFO_W = 40

game_msgs = [] #in-game message list

#------------------------------------------------------------------------------#
#------------------------------Initialisation----------------------------------#

#initialising font, window and console

libtcod.console_set_custom_font('terminal10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Culture Hack', False)

con1 = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

################################################################################
#------------------------------------------------------------------------------#
#----------------------------------CLASSES-------------------------------------#
#------------------------------------------------------------------------------#
################################################################################
class Object:
    #this is the generic object class
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter = None, ai = None, item=None, equipment=None, gun=None):
        self.name = name #The object's name
        self.blocks = blocks #Whether the object blocks movement
        self.always_visible = always_visible #Whether the object is visible regardless of FOV
        self.x = x #Object map coords
        self.y = y
        self.char = char #ASCII char that represents object
        self.color = color #colour of object
        self.fighter = fighter #the object's fighter component (if it has one)

        #telling components who their owner is
        if self.fighter:
            self.fighter.owner = self

        self.ai = ai
        if self.ai:
            self.ai.owner = self

        self.item = item
        if self.item:
            self.item.owner = self

        self.equipment = equipment

        if self.equipment:
            self.equipment.owner = self

            self.item = Item() #If an object is equipment, it must also be an item
            self.item.owner = self

        self.gun = gun
        if self.gun:
            self.gun.owner = self

    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            #move by given amount in given direction(s)
            self.x += dx
            self.y += dy

        #if the move is blocked, attempt to move in a random direction
        else:
            if self is not player:
                dx = libtcod.random_get_int(0,-1,1)
                dy = libtcod.random_get_int(0,-1,1)
                if not is_blocked(self.x + dx, self.y + dy):
                    self.move(dx, dy)

            else:
                if self is not player:
                    dx = libtcod.random_get_int(0,-1,1)
                    dy = libtcod.random_get_int(0,-1,1)

    def draw(self):
        #set the colour and then draw the char of this obj
        if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and map[self.x][self.y].explored)):
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        #erase char
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def move_towards(self, target_x, target_y):
        #vector from this obj to target coords
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        self.move(dx, dy)

    def move_away(self, target_x, target_y):
        #vector from this obj to target coords
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        self.move(-dx, -dy)

    def distance_to(self, other): #return distance to another object
        #normalised vector to object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def send_to_back(self): #send object to the front of list to be drawn last
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def distance(self,x,y):
        #return distance to coords
        return math.sqrt((x-self.x) ** 2 + (y - self.y) ** 2)

    def destroy(self): #remove the object from the object list
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)
        objects.remove(self)
################################################################################
################################################################################
class ConfusedMonster:
    #ai for confusioned NPC
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS+libtcod.random_get_int(0, -5, 20)):
        self.old_ai = old_ai #needs to remember what it's previous ai component was
        self.num_turns = num_turns #the amount of time that the monster will be confused for

    def take_turn(self): #triggers in the loop if player has taken a turn
        if self.num_turns > 0:
            #move randomly
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, -1))
            self.num_turns -= 1

        else: #the npc is no longer confused
            self.owner.ai = self.old_ai
            if libtcod.map_is_in_fov(fov_map, self.owner.x, self.owner.y):
                message('The ' + self.owner.name + ' is no longer confused.', libtcod.red)
################################################################################
################################################################################
class Tile:
    #a tile in the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
        self.explored = False
        #by default, if a tile is blocked, it blocks line of sight too
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight


################################################################################
################################################################################
class Rect:
    #a rectangle which is used to create rooms
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self): #returns the centre coords of the rectangle
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        #returns true if the rectangle is intersecting
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

################################################################################
################################################################################
class Fighter:
    #combat related properties and methods
    def __init__(self, hp, agility, strength, dexterity, accuracy, xp, armour=0, death_function=None, blood_colour1=libtcod.red, blood_colour2=libtcod.dark_red, blood_colour3=libtcod.light_red):
        self.death_function = death_function
        self.max_hp = hp
        self.hp = hp
        self.base_dexterity = dexterity
        self.base_accuracy = accuracy
        self.base_agility = agility
        self.base_strength = strength
        self.base_armour = armour
        self.xp = xp
        self.blood_colour1 = blood_colour1
        self.blood_colour2 = blood_colour2
        self.blood_colour3 = blood_colour3

    #attribute properties to calculate base attribute along with any modifiers on demand

    @property
    def strength(self):
        bonus = sum(equipment.strength_bonus for equipment in get_all_equipped(self.owner))
        return self.base_strength + bonus

    @property
    def agility(self):
        bonus = sum(equipment.agility_bonus for equipment in get_all_equipped(self.owner))
        return self.base_agility + bonus

    @property
    def dexterity(self):
        bonus = sum(equipment.dexterity_bonus for equipment in get_all_equipped(self.owner))
        return self.base_dexterity + bonus

    @property
    def accuracy(self):
        bonus = sum(equipment.accuracy_bonus for equipment in get_all_equipped(self.owner))
        return self.base_accuracy + bonus

    @property
    def armour(self):
        bonus = sum(equipment.armour_bonus for equipment in get_all_equipped(self.owner))
        return self.base_armour + bonus

    def attack(self, target):
        #object's melee attack method

        dex_mod = attribute_test(self.dexterity) #test dexterity

        if dex_mod >= 0: #if the test was passed:

            message(self.owner.name.capitalize() + ' strikes ' + target.name, libtcod.cyan)
            agi_mod = attribute_test(target.fighter.agility) #test target's agility
            agi_mod -= dex_mod

            if agi_mod < 0: #if attacker won test:
                str_mod = attribute_test(self.strength) #strength test
                if str_mod > 0: #if passed:

                    def_mod = attribute_test(target.fighter.base_strength) #target strength test
                    if def_mod < 0: #if failed:
                        def_mod = 0

                    damage = str_mod - def_mod - target.fighter.armour #calculate damage

                    if damage == 0:
                        message('The attack was blocked!', libtcod.red)

                    elif damage <= 10:
                        message('The attack was quite weak.', libtcod.light_red)

                    elif damage <= 30:
                        message('The attack connected well.', libtcod.light_orange)

                    elif damage <= 50:
                        message('The attack connected very well.', libtcod.light_green)

                    elif damage > 50:
                        message('The attack was a brutal transfer of energy!', libtcod.flame)

                    if damage < 0:
                        damage = 0

                #if attack failed:

                elif str_mod <= 0:
                    message('The attack has no effect!', libtcod.red)
                    damage = 0

            elif agi_mod >= 0:
                message(target.name + ' dodges the attack!', libtcod.amber)
                damage = 0
        elif dex_mod < 0:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but misses!', libtcod.amber)
            damage = 0


        if damage > 0:
            #cause damage
            target.fighter.take_damage(damage)


    def take_damage(self, damage):
        #apply damage if possible

        if damage > 10 and damage <= 30:

            splat = Object(self.owner.x + libtcod.random_get_int(0,-2,2), self.owner.y + libtcod.random_get_int(0,-2,2), '.', self.owner.name + ' blood spatter', self.blood_colour1, blocks=False, fighter=None, ai=None)
            objects.append(splat) #create debris object
            splat.send_to_back()

        elif damage <= 50:

            splat = Object(self.owner.x + libtcod.random_get_int(0,-1,1), self.owner.y + libtcod.random_get_int(0,-1,1), ',', self.owner.name + ' blood spatter', self.blood_colour2, blocks=False, fighter=None, ai=None)
            objects.append(splat)
            splat.send_to_back()

        elif damage > 50:

            splat = Object(self.owner.x + libtcod.random_get_int(0,-1,1), self.owner.y + libtcod.random_get_int(0,-1,1), '*', self.owner.name + ' chunk', self.blood_colour3, blocks=False, fighter=None, ai=None)
            objects.append(splat)
            splat.send_to_back()

            splat = Object(self.owner.x + libtcod.random_get_int(0,-1,1), self.owner.y + libtcod.random_get_int(0,-1,1), '"', self.owner.name + ' blood splat', self.blood_colour1, blocks=False, fighter=None, ai=None)
            objects.append(splat)
            splat.send_to_back()

        if damage > 0:

            if self.owner.ai==BasicMonster:
                self.owner.ai.courage -= damage


            self.hp -= damage #remove hp from fighter

        if self.hp <= 0:

            if self.owner != player: #if the object isn't the player, raise the player's xp
                player.fighter.xp += self.xp

            self.hp = 0
            function = self.death_function #object dies if its hp is 0 or lower
            if function is not None:
                function(self.owner)

        return

    def heal(self, amount): #heal fighter by amount
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp



################################################################################
################################################################################
class BasicMonster:
    #ai for basic enemy

    def __init__(self, courage, gun=None, aiming_time_max=2):
        self.last_x = None
        self.last_y = None
        self.state = 'idling'
        self.courage = courage
        self.gun = gun
        self.confused_num_turns = 0
        self.aiming_time_max = aiming_time_max
        self.aiming_time = self.aiming_time_max

    def take_turn(self): #triggers in the main loop if the player has taken a turn
        monster = self.owner
        if self.state <> 'confused':

            if libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and self.courage > 0:
                if libtcod.random_get_int(0, 0, int(monster.distance_to(player))) > 2 and self.gun is not None:
                    #if the NPC has a gun, and they aren't next to the player, randomly choose between shooting or chasing
                    if self.gun.ammo_count > 0:
                        self.state = 'shooting'
                    else: #if the npc has no ammo, chase the player
                        self.state = 'chasing'
                else:
                    self.state = 'chasing'

            elif self.courage < 0: #if the npc's has no courage, the npc flees
                if self.state <> 'fleeing':
                    self.aiming_time = self.aiming_time_max
                    message('The ' + monster.name + ' is fleeing!', libtcod.orange)

                self.state = 'fleeing'

            elif self.last_x is not None and self.last_y is not None: #search for player at last known coords
                self.aiming_time = self.aiming_time_max
                self.state = 'hunting'

            else:
                self.aiming_time = self.aiming_time_max #npc needs to aim in order to shoot again
                self.state = 'idling'

        if self.state == 'chasing':

            self.aiming_time = int(self.aiming_time_max/2) #npc takes less time to aim

            #remember the player's coords in case they go out of sight

            self.last_x = player.x

            self.last_y = player.y

            #move towards player if close
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)

            #attack the player
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)

        elif self.state == 'hunting': #look for player at last known coords

            if monster.distance(self.last_x, self.last_y) >= 2:
                monster.move_towards(self.last_x, self.last_y)

            else:
                self.last_x = None
                self.last_y = None

        elif self.state == 'fleeing': #move away from player

            if monster.distance_to(player) <= 5:
                monster.move_away(player.x, player.y)

            dice = libtcod.random_get_int(0, 1, 10)
            #npc has a chance of regaining courage
            if dice < 3:
                self.courage += 1

                if self.courage > 0:
                    message('The ' + monster.name + ' is no longer fleeing.', libtcod.light_green)
                    self.state = 'idling'


        elif self.state == 'idling':
            #move randomly
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, -1))

        elif self.state == 'shooting':
            if self.aiming_time == 0: #if finished aiming
                curx = monster.x
                cury = monster.y
                x = player.x
                y = player.y
                blocked = False

                while(curx,cury)<>(x,y):

                    #get vector to target

                    dx = x - curx
                    dy = y - cury
                    distance = math.sqrt(dx ** 2 + dy ** 2)

                    #normalise to 1 length and round it, converting to int
                    dx = int(round(dx / distance))
                    dy = int(round(dy / distance))

                    if not libtcod.map_is_in_fov(fov_map, curx + dx, cury + dy):
                        #if the next coords are not in the fov, stop here
                        x = curx
                        y = cury

                    for obj in objects:
                        if obj.x == curx+dx and obj.y == cury+dy and obj.blocks==True and obj is not player:
                            #if there is a friendly npc in the way, don't shoot
                            blocked = True

                    curx += dx #increment coords
                    cury += dy

                if blocked == False:
                    #fire weapon if not blocked
                    self.gun.fire_weapon(monster.x, monster.y, monster.fighter, player.x, player.y)
                    self.aiming_time += libtcod.random_get_int(0, 0, self.aiming_time_max)
            else:
                self.aiming_time -= 1

        elif self.state == 'confused':
            #move randomly if confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, -1))

            if self.confused_num_turns == 0:
                self.state = 'idling'
                if libtcod.map_is_in_fov(fov_map, self.owner.x, self.owner.y):
                    message('The ' + self.owner.name + ' is no longer confused.', libtcod.red)

            self.confused_num_turns -= 1

################################################################################
################################################################################
class FluidBehaviour:
    #behaviour for smoke, fire and naturally decaying processes

    def __init__(self, iteration_number, decay_chance):
        self.iteration_number = iteration_number #the instance generation
        self.decay_chance = decay_chance #chance of particle being removed

    def take_turn(self): #run in the game loop if player takes turn
        particle = self.owner

        if libtcod.random_get_int(0, 0, self.iteration_number) < 2:

            if self.decay_chance > 0:
                self.decay_chance -= 1 #increase the chance of decaying
            #new particle with higher generation number:
            ai_component = FluidBehaviour(self.iteration_number+1, self.decay_chance)

            newparticle = Object(self.owner.x + libtcod.random_get_int(0,-1,1), self.owner.y + libtcod.random_get_int(0,-1,1), self.owner.char, self.owner.name, self.owner.color, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle) #create new particle

        if libtcod.random_get_int(0,0,self.decay_chance)==self.decay_chance:
            self.owner.destroy() #destroy particle


################################################################################
################################################################################
class PodBehaviour:
    #behaviour for a creature spawner

    def __init__(self, spawn_chance):
        self.spawn_chance = spawn_chance #probability of spawning

    def take_turn(self): #run in the game loop if player takes turn

        if libtcod.random_get_int(0, 1, 100) <= self.spawn_chance:
            #spawn at random adjacent coords
            x = libtcod.random_get_int(0,-1,1)
            y = libtcod.random_get_int(0,-1,1)

            if not is_blocked(self.owner.x + x,self.owner.y + y): #if x or y isn't blocked
                #spawn lavae

                fighter_component = Fighter(hp=libtcod.random_get_int(0,30,40), agility=libtcod.random_get_int(0,30,60), strength=libtcod.random_get_int(0,20,50), dexterity=libtcod.random_get_int(0,30,50), accuracy=25, xp=15, death_function = monster_death, blood_colour1=libtcod.green, blood_colour2=libtcod.dark_green, blood_colour3=libtcod.darker_green)
                ai_component = BasicMonster(courage=50)

                monster = Object(self.owner.x + x, self.owner.y + y, 'a', 'Arachnoid Lava', libtcod.purple, blocks=True, fighter=fighter_component, ai=ai_component)
                objects.append(monster)

################################################################################
################################################################################
class Grenade: #class for grenade object that explodes after a set timer

    def __init__(self, turns, fire_damage):
        self.turns = turns #timer length
        self.fire_damage = fire_damage #explosive damage

    def take_turn(self): #run once in the loop if player takes turn

        if self.turns == 0: #if the timer has run out

            #explode the grenade, creating smoke, flames and a crater:

            x = self.owner.x
            y = self.owner.y

            crater = Object(x, y, 10, 'Crater', libtcod.dark_grey, blocks=False)
            objects.append(crater)
            crater.send_to_back()

            ai_component = FluidBehaviour(1, 3)
            newparticle = Object(x, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle)
            ai_component = FluidBehaviour(1, 3)
            newparticle = Object(x+1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle)
            ai_component = FluidBehaviour(1, 3)
            newparticle = Object(x-1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle)
            ai_component = FluidBehaviour(1, 3)
            newparticle = Object(x, y+1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle)
            ai_component = FluidBehaviour(1, 3)
            newparticle = Object(x, y-1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
            objects.append(newparticle)

            ai_component = FluidBehaviour(5, 2)
            flame = Object(x, y, 176, 'Flame', libtcod.flame, blocks=False, fighter=None, ai=ai_component)
            objects.append(flame)

            hasbeenhit = [] #keeps track of which objects have been hit

            for obj in objects: #find fighters in explosion range and damage them
                if obj.distance(x,y) <= SHELL_RADIUS and obj.fighter and obj not in hasbeenhit:
                    if obj == player:
                        name = obj.name
                    else:
                        name = 'The ' + obj.name

                    damage = self.fire_damage - (obj.distance(x,y))**2
                    if damage < 0:
                        damage = 0
                    message(name + ' is caught in the explosion!', libtcod.orange)
                    hasbeenhit.append(obj)
                    obj.fighter.take_damage(int(damage))

            hasbeenhit = None

            self.owner.destroy()

        self.turns -= 1 #subtract 1 from the timer
################################################################################
################################################################################
class FlashBehaviour:

    def __init__(self, turns):
        self.turns = turns

    def take_turn(self):
        self.owner.destroy()

################################################################################
################################################################################
class MindBehaviour:

    def __init__(self):
        self.has_been_seen = False

    def take_turn(self):
        if self.has_been_seen == False and libtcod.map_is_in_fov(fov_map, self.owner.x, self.owner.y):
            msgbox('Mind: I know it is me you are looking for. You have obviously fought very hard.')
            self.has_been_seen = True

################################################################################
################################################################################
class Item:
    #a useable item
    def __init__(self, use_function=None):
        self.use_function = use_function

    def use(self):
        #call use function if it has one

        if self.owner.equipment: #if this is equipment, toggle its state
            self.owner.equipment.toggle_equip()
            return

        if self.use_function is None: #if there is no use function
            message('The ' + self.owner.name + ' cannot be used.')

        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) # remove after use
    def pick_up(self):
        #add to inventory and remove from the map
        if len(inventory) >= 26:
            message('You cannot carry anything else!', libtcod.red)

        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You pick up the ' + self.owner.name + '.', libtcod.lighter_violet)

    def drop(self):
        #add to the map and remove from the inventory list

        if self.owner.equipment:
            self.owner.equipment.dequip()

        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You drop the ' + self.owner.name + '.', libtcod.yellow)
################################################################################
################################################################################
class Equipment: #an item which can be equipped and has passive effects on the player

    def __init__(self, slot, strength_bonus=0, agility_bonus=0, dexterity_bonus=0, armour_bonus=0, accuracy_bonus=0):
        self.strength_bonus = strength_bonus
        self.agility_bonus = agility_bonus
        self.dexterity_bonus = dexterity_bonus
        self.armour_bonus = armour_bonus
        self.accuracy_bonus = accuracy_bonus

        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self): #toggle equipped state
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self): #set state to equipped

        old_equipment = check_equipment_slot(self.slot)

        if old_equipment is not None:
            old_equipment.dequip()

        self.is_equipped = True
        message('You equip ' + self.owner.name, libtcod.light_green)

    def dequip(self): #set state to unequipped

        if not self.is_equipped: return

        self.is_equipped = False
        message('You unequip ' + self.owner.name, libtcod.light_green)
################################################################################
################################################################################
class Gun: #class for a ranged weapon that uses ammunition

    def __init__(self, fire_range, fire_mode, fire_damage, ammo_count, accuracy_modifier=1):
        self.fire_range = fire_range
        self.fire_mode = fire_mode #the function called when weapon is fired
        self.fire_damage = fire_damage
        self.ammo_count = ammo_count
        self.accuracy_modifier = accuracy_modifier

    def fire_weapon(self, xFr, yFr, firer, x=None, y=None):
        self.firer = firer
        #ask player to target a tile
        if self.ammo_count > 0:
            if self.firer.owner == player:
                message('Left-click to target a tile to shoot, or right-click to cancel.', libtcod.cyan)
                (x,y) = target_tile(self.fire_range)
            if x is not None:
                #fire the weapon:
                self.ammo_count -= 1
                range_mod = int(self.firer.accuracy/self.firer.owner.distance(x,y))
                mod = attribute_test(self.firer.accuracy-range_mod)
                fire_damage = self.fire_damage
                self.fire_mode(x, y, mod, fire_damage, firer)
        else:
            message('This weapon has no ammo!', libtcod.red)
################################################################################
################################################################################
################################################################################
#------------------------------------------------------------------------------#
#----------------------------------Functions-----------------------------------#
#------------------------------------------------------------------------------#
################################################################################
def attribute_test(attribute): #function for making attribute tests

    dice = libtcod.random_get_int(0,1,100) #roll a 100 sided dice

    effective_skill = 100 - attribute #subtract attribute from 100

    if effective_skill < 0: #if the attribute is greater than 95, the effective skill will still be 5
        effective_skill = 5

    return (dice - effective_skill) #return modifier (>= 0 is a pass, < 0 is a fail)
################################################################################
def handle_keys(): #function for handling user input
    global keys

    if key.vk == libtcod.KEY_ESCAPE:
        return 'exit' #exit game

    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_KP8 or key.vk == libtcod.KEY_UP:
            player_move_attack(0, -1)

        elif key.vk == libtcod.KEY_KP9:
            player_move_attack(1, -1)

        elif key.vk == libtcod.KEY_KP7:
            player_move_attack(-1, -1)

        elif key.vk == libtcod.KEY_KP2 or key.vk == libtcod.KEY_DOWN:
            player_move_attack(0, 1)

        elif key.vk == libtcod.KEY_KP3:
            player_move_attack(1, 1)

        elif key.vk == libtcod.KEY_KP4 or key.vk == libtcod.KEY_LEFT:
            player_move_attack(-1, 0)

        elif key.vk == libtcod.KEY_KP1:
            player_move_attack(-1, 1)

        elif key.vk == libtcod.KEY_KP6 or key.vk == libtcod.KEY_RIGHT:
            player_move_attack(1, 0)

        elif key.vk == libtcod.KEY_KP5:
            return

        else:
            #check for other keypresses
            key_char = chr(key.c)

            if key_char == 'g':
                #pick an item from the floor
                for object in objects:
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        break

            elif key_char == 'i': #show inventory
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()
                else:
                    return 'didnt-take-turn'

            elif key_char == 'd': #bring up inventory to drop an item
                chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel. \n')
                if chosen_item is not None:
                    chosen_item.drop()

            elif key_char == 'r': #enter ranged firing mode
                for object in get_all_equipped(player):
                    if object.owner.gun:
                        object.owner.gun.fire_weapon(player.x, player.y, player.fighter)
                        break
            else:

                if key_char == '<': #exit level if there are stairs
                    if stairs.x == player.x and stairs.y == player.y:
                        next_level()

                if key_char == 'c':
                    #display character info
                    level_xp = BASIC_LEVEL_UP + player.level*LEVEL_UP_INCREMENT

                    str_mod = player.fighter.strength - player.fighter.base_strength
                    agi_mod = player.fighter.agility - player.fighter.base_agility
                    dex_mod = player.fighter.dexterity - player.fighter.base_dexterity

                    if str_mod == 0:
                        str_txt = ''
                    elif str_mod > 0:
                        str_txt = ' (+'+str(str_mod)+')'
                        str_col = libtcod.light_green
                    elif str_mod < 0:
                        str_txt = ' ('+str(str_mod)+')'
                        str_col = libtcod.light_red

                    if agi_mod == 0:
                        agi_txt = ''
                    elif agi_mod > 0:
                        agi_txt = ' (+'+str(agi_mod)+')'
                        agi_col = libtcod.light_green
                    elif agi_mod < 0:
                        agi_txt = ' ('+str(agi_mod)+')'
                        agi_col = libtcod.light_red

                    if dex_mod == 0:
                        dex_txt = ''
                    elif dex_mod > 0:
                        dex_txt = ' (+'+str(dex_mod)+')'
                        dex_col = libtcod.light_green
                    elif dex_mod < 0:
                        dex_txt = ' ('+str(dex_mod)+')'
                        dex_col = libtcod.light_red

                    msgbox(player.name + '\n\n Level: '+str(player.level)+'\n Xp: '+str(player.fighter.xp)+'\n Xp to next: '+str(level_xp)+'\n\n Max HP: '+str(player.fighter.max_hp)+'\n Strength: '+str(player.fighter.base_strength)+str_txt+'\n Agility: '+str(player.fighter.base_agility)+agi_txt+'\n Dexterity: '+str(player.fighter.base_dexterity)+dex_txt+'\n\n Armour rating: '+str(player.fighter.armour), CHAR_INFO_W)

                return 'didnt-take-turn'

################################################################################
def next_level(): #function for moving up a level
    global ship_level, max_rooms

    message('You descend further into the depths of the ship...')
    ship_level += 1
    if max_rooms < 70: #increase maximum rooms per level
        max_rooms += 2
    make_map()
    initialize_fov()
################################################################################
def target_tile(max_range=None):
    #return position of tile left-clicked in player's FOV
    global key, mouse
    while True:
        #render the screen and show names under the mouse
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        for object in objects:
            object.clear()

        (x, y) = (mouse.cx, mouse.cy)

        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None) #cancel if player pressed right or esc

         #accept the target if player clicked in FOV
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and (max_range is None or player.distance(x,y) <= max_range)):
            return (x,y)
################################################################################
def target_monster(max_range=None): #get fighter that player clicked
    while True:
        (x, y) = target_tile(max_range)

        if x is None:
            return None

        #return the clicked monster
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
               return obj

################################################################################
def get_names_under_mouse(): #show the names of object under the mouse
    global mouse

    (x, y) = (mouse.cx, mouse.cy)

    #create a list with the names of objects at mouse
    names = [obj.name for obj in objects
        if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]

    names = ', '.join(names) #join names, seperate by commas
    return names.capitalize()
################################################################################
def player_move_attack(dx,dy): #function for moving the player
    global fov_recompute

    #direction the player is moving in with coords
    x = player.x + dx
    y = player.y + dy

    #check if player will attack
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
        if object.name == 'Mind' and object.x == x and object.y == y:
            save_game()
            win_game()
            exit()

    #attack if necessary
    if target is not None:
        player.fighter.attack(target)

    else:
        player.move(dx, dy)
        fov_recompute = True

################################################################################
def level_check():
    #check if player has leveled up
    level_xp = BASIC_LEVEL_UP + player.level * LEVEL_UP_INCREMENT

    if player.fighter.xp > level_xp:
        #the player levels up
        player.level += 1
        player.fighter.xp -= level_xp
        message('Your practice has paid off! You have refined your skills & gained a level!', libtcod.light_green)

        player.fighter.max_hp += (10+libtcod.random_get_int(0,-5,5))
        player.fighter.hp = player.fighter.max_hp

        player.fighter.base_strength += libtcod.random_get_int(0,0,2)
        player.fighter.base_agility += libtcod.random_get_int(0,0,2)
        player.fighter.base_dexterity += libtcod.random_get_int(0,0,2)
        player.fighter.base_accuracy += libtcod.random_get_int(0,0,2)

################################################################################
def menu(header, options, width):
    if len(options) > 26: raise ValueError('Menu has more than 26 items.')

    #calculate height of menu
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0

    height = len(options) + header_height

    #create off-screen console for the menu
    window = libtcod.console_new(width, height)

    #print the header and autowrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window,0,0,width,height,libtcod.BKGND_NONE, libtcod.LEFT, header)

    #print options to menu
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    #blit changes to screen
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x,y, 1.0, 0.9)

    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

################################################################################
def inventory_menu(header):
    #show inventory menu
    if len(inventory) == 0: #if there is nothing in inventory
        options = ['Inventory is empty.']
    else:
        options = []

        for item in inventory:
            if item.gun: #if it's a gun, show the ammo count too
                text=item.name + ' (' + str(item.gun.ammo_count) + ')'
            else:
                text=item.name

            if item.equipment and item.equipment.is_equipped:
                #if it's equipment, show the slot
                text = text + ' (' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, INVENTORY_WIDTH)

    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item
################################################################################
def cast_heal():
    #heal the player by set amount
    if player.fighter.hp == player.fighter.max_hp:
        message('You are not injured!', libtcod.red)
        return 'cancelled'

    message('The MediSphere dissolves into a silver cloud and repairs some of your injuries.', libtcod.green)
    player.fighter.heal(HEAL_AMOUNT)
################################################################################
def cast_arc():
    #find closest enemy to the player
    monster = closest_monster(ARC_RANGE)
    if monster is None:
        message('There is no enemy within range.', libtcod.red)
        return 'cancelled'
    #damage the enemy
    dice = libtcod.random_get_int(0, -12, 12)
    message('A blue arc strike the ' + monster.name + ' with a loud crack!', libtcod.light_blue)
    monster.fighter.take_damage(ARC_DAMAGE)
################################################################################
def cast_shot(x, y, mod, fire_damage, firer): #function for explosive ranged attack

    message(firer.owner.name+' fires an explosive shell!', libtcod.flame)

    #base accuracy on attribute test score
    if mod <= -50:
        message('The shot backfires!', libtcod.red)
        x = firer.owner.x
        y = firer.owner.y
    elif mod <= -30:
        message('The shot misses quite badly!', libtcod.light_orange)
        x += libtcod.random_get_int(0,0,3)
        y += libtcod.random_get_int(0,0,3)
    elif mod < 0:
        message('The shot is slightly off target.', libtcod.light_orange)
        x += libtcod.random_get_int(0,0,2)
        y += libtcod.random_get_int(0,0,2)
    elif mod <= 20:
        message('The shot is reasonably on target.', libtcod.light_green)
        x += libtcod.random_get_int(0,0,1)
        y += libtcod.random_get_int(0,0,1)
    else:
        message('The shot is a direct hit!', libtcod.light_green)

    (curx,cury)=(firer.owner.x,firer.owner.y)

    while(curx,cury)<>(x,y):
        #check if shot has been blocked
        dx = x - curx
        dy = y - cury
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        if not libtcod.map_is_in_fov(fov_map, curx + dx, cury + dy):
            x = curx
            y = cury

        for obj in objects:
            if obj.x == curx+dx and obj.y == cury+dy and obj.blocks==True:
                x=curx+dx
                y=cury+dy

        curx += dx
        cury += dy

    #create debris objects

    crater = Object(x, y, 10, 'Crater', libtcod.dark_grey, blocks=False)
    objects.append(crater)
    crater.send_to_back()

    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x+1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x-1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y+1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y-1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)

    ai_component = FluidBehaviour(5, 2)
    flame = Object(x, y, 176, 'Flame', libtcod.flame, blocks=False, fighter=None, ai=ai_component)
    objects.append(flame)

    #check for hits

    hasbeenhit = []

    for obj in objects:
        if obj.distance(x,y) <= SHELL_RADIUS and obj.fighter and obj not in hasbeenhit:
            if obj == player:
                name = obj.name
            else:
                name = 'The ' + obj.name

            damage = fire_damage - (obj.distance(x,y))**2
            if damage < 0:
                damage = 0
            message(name + ' is caught in the explosion!', libtcod.orange)
            hasbeenhit.append(obj)
            obj.fighter.take_damage(int(damage))

    hasbeenhit = None

################################################################################
def cast_plasma(x, y, mod, fire_damage, firer): #function for plasma ranged attack

    message(firer.owner.name+' fires a plasma bolt!', libtcod.flame)

    #base accuracy on attribute test score:
    if mod <= -50:
        message('The shot backfires!', libtcod.red)
        x = firer.owner.x
        y = firer.owner.y
    elif mod <= -30:
        message('The shot misses quite badly!', libtcod.light_orange)
        x += libtcod.random_get_int(0,0,3)
        y += libtcod.random_get_int(0,0,3)
    elif mod < 0:
        message('The shot is slightly off target.', libtcod.light_orange)
        x += libtcod.random_get_int(0,0,2)
        y += libtcod.random_get_int(0,0,2)
    elif mod <= 20:
        message('The shot is reasonably on target.', libtcod.light_green)
        x += libtcod.random_get_int(0,0,1)
        y += libtcod.random_get_int(0,0,1)
    else:
        message('The shot is a direct hit!', libtcod.light_green)

    (curx,cury)=(firer.owner.x,firer.owner.y)

    while(curx,cury)<>(x,y):
        #check if shot is blocked
        dx = x - curx
        dy = y - cury
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        if not libtcod.map_is_in_fov(fov_map, curx + dx, cury + dy):
            x = curx
            y = cury

        for obj in objects:
            if obj.x == curx+dx and obj.y == cury+dy and obj.blocks==True:
                x=curx+dx
                y=cury+dy

        curx += dx
        cury += dy

        #draw tracer

        libtcod.console_put_char_ex(con, curx, cury, 177, libtcod.blue, libtcod.BKGND_NONE)

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    render_all()
    libtcod.console_flush()

    libtcod.console_clear(con)

    #create debris objects

    crater = Object(x, y, 10, 'Crater', libtcod.dark_grey, blocks=False)
    objects.append(crater)
    crater.send_to_back()

    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x+1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x-1, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y+1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)
    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y-1, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)

    ai_component = FluidBehaviour(2, 2)
    flame = Object(x, y, 176, 'Plasma', libtcod.blue, blocks=False, fighter=None, ai=ai_component)
    objects.append(flame)
    ai_component = FluidBehaviour(2, 2)
    flame = Object(x, y, 176, 'Plasma', libtcod.light_blue, blocks=False, fighter=None, ai=ai_component)
    objects.append(flame)
    ai_component = FluidBehaviour(2, 2)
    flame = Object(x, y, 176, 'Plasma', libtcod.dark_blue, blocks=False, fighter=None, ai=ai_component)
    objects.append(flame)

    #check for hits

    hasbeenhit = []

    for obj in objects:
        if obj.distance(x,y) <= SHELL_RADIUS and obj.fighter and obj not in hasbeenhit:
            if obj == player:
                name = obj.name
            else:
                name = 'The ' + obj.name

            damage = fire_damage - (obj.distance(x,y))**2
            if damage < 0:
                damage = 0
            message(name + ' is hit by the blast!', libtcod.orange)
            hasbeenhit.append(obj)
            obj.fighter.take_damage(int(damage))

    hasbeenhit = None

################################################################################
def laserburst(x, y, mod, fire_damage, firer): #function for laser ranged attack

    message(firer.owner.name+' fires a laser!')

    #calculate accuracy modifier

    if mod <= -50:
        message('The shot misfires!', libtcod.red)
        x = firer.owner.x
        y = firer.owner.y
    elif mod <= -30:
        message('The shot misses badly.', libtcod.light_red)
        x += libtcod.random_get_int(0, -5, 5)
        y += libtcod.random_get_int(0, -5, 5)
    elif mod < 0:
        message('The shot is off target.', libtcod.light_orange)
        x += libtcod.random_get_int(0, -3, 3)
        y += libtcod.random_get_int(0, -3, 3)
    elif mod <= 50:
        message('The shot is close to the target.', libtcod.light_green)
        x += libtcod.random_get_int(0, -1, 1)
        y += libtcod.random_get_int(0, -1, 1)
    else:
        message('The shot is a direct hit!', libtcod.crimson)

    (curx,cury)=(firer.owner.x,firer.owner.y)

    while(curx,cury)<>(x,y):

        #check blocks

        dx = x - curx
        dy = y - cury
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        if not libtcod.map_is_in_fov(fov_map, curx + dx, cury + dy):
            x = curx
            y = cury

        for obj in objects:
            if obj.x == curx+dx and obj.y == cury+dy and obj.blocks==True:
                x=curx+dx
                y=cury+dy

        curx += dx
        cury += dy

        #draw tracer

        libtcod.console_put_char_ex(con, curx, cury, '.', libtcod.red, libtcod.BKGND_NONE)

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    render_all()
    libtcod.console_flush()

    libtcod.console_clear(con)

    #create smoke

    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)

    damage = fire_damage + mod

    if damage < 0:
        damage = 0

    #check for hits

    hasbeenhit = []

    for obj in objects:

        if obj.x == x and obj.y == y and obj.fighter and obj.fighter is not firer and obj not in hasbeenhit:

                if obj == player:
                    name = obj.name
                else:
                    name = 'the ' + obj.name

                if damage == 0:
                    message(name + ' is only scratched by the laser!', libtcod.light_green)
                elif damage < 30:
                    message(name + ' is hit by the laser!', libtcod.orange)
                elif damage < 60:
                    message(name + ' is sprayed by the laser!', libtcod.light_red)
                else:
                    message('Smoke plummets from ' + name + ' as they are engulfed in flames!', libtcod.red)

                hasbeenhit.append(obj)

                obj.fighter.take_damage(int(damage))

    hasbeenhit = None

################################################################################
def bullet(x, y, mod, fire_damage, firer): #function for bullet ranged attack

    message(firer.owner.name+' fires a bullet!')

    #accuracy modifier

    if mod <= -50:
        message('The shot misfires!', libtcod.red)
        x = firer.owner.x
        y = firer.owner.y
    elif mod <= -40:
        message('The shot misses badly.', libtcod.light_red)
        x += libtcod.random_get_int(0, -3, 3)
        y += libtcod.random_get_int(0, -3, 3)
    elif mod < 0:
        message('The shot is off target.', libtcod.light_orange)
        x += libtcod.random_get_int(0, -2, 2)
        y += libtcod.random_get_int(0, -2, 2)
    elif mod <= 40:
        message('The shot is close to the target.', libtcod.light_green)
        x += libtcod.random_get_int(0, -1, 1)
        y += libtcod.random_get_int(0, -1, 1)
    else:
        message('The shot is a direct hit!', libtcod.crimson)

    (curx,cury)=(firer.owner.x,firer.owner.y)

    while(curx,cury)<>(x,y):

        #check blocked

        dx = x - curx
        dy = y - cury
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalise to 1 length and round it, converting to int
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))

        if not libtcod.map_is_in_fov(fov_map, curx + dx, cury + dy):
            x = curx
            y = cury

        for obj in objects:
            if obj.x == curx+dx and obj.y == cury+dy and obj.blocks==True:
                x=curx+dx
                y=cury+dy

        curx += dx
        cury += dy

        #draw tracer

        libtcod.console_put_char_ex(con, curx, cury, '`', libtcod.yellow, libtcod.BKGND_NONE)

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    render_all()
    libtcod.console_flush()

    libtcod.console_clear(con)

    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(x, y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)

    ai_component = FluidBehaviour(1, 3)
    newparticle = Object(firer.owner.x, firer.owner.y, 177, 'Smoke', libtcod.dark_grey, blocks=False, fighter=None, ai=ai_component)
    objects.append(newparticle)

    damage = fire_damage + mod
    if damage < 0:
        damage = 0

    #check for hits

    hasbeenhit = []

    for obj in objects:
        if obj.x == x and obj.y == y and obj.fighter and obj.fighter is not firer and obj not in hasbeenhit:

            if obj == player:
                name = obj.name
            else:
                name = 'the ' + obj.name

            if damage == 0:
                message(name + ' is only scraped by the bullet!', libtcod.light_green)
            elif damage < 30:
                message(name + ' is hit by the bullet!', libtcod.orange)
            elif damage < 60:
                message(name + ' is struck squarely by the bullet!', libtcod.light_red)
            else:
                message('Blood squirts from ' + name + ' as the bullet leaves a hole where it entered!', libtcod.red)

            hasbeenhit.append(obj)

            obj.fighter.take_damage(int(damage))

    hasbeenhit = None

################################################################################
def grenade_toss(timer=2,fire_damage=65): #function for throwing grenade object

    message('Left-click to select a tile, right-click to cancel', libtcod.cyan)

    x, y = target_tile(int(player.fighter.strength/4)) #limit range by strength

    if x != None and y != None:
        message(player.name +' throws a grenade!', libtcod.flame)
        ai_component = Grenade(timer,fire_damage)
        nade = Object(x, y, '*', 'Grenade', libtcod.dark_green, blocks=False,ai=ai_component)
        objects.append(nade)


################################################################################
def cast_confuse():
    #find enemy and make it confused
    message('Left-click an enemy to fire at them, right-click to cancel.', libtcod.cyan)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None: return 'cancelled'
    #set ai state to confused
    monster.ai.state = 'confused'
    monster.ai.confused_num_turns = libtcod.random_get_int(0, 5, 25)
    message('The Synaptic Inhibitor blasts the ' + monster.name + ', making them disorientated and confused!', libtcod.sea)
################################################################################
def cast_teleport(): #function for teleporting player to random part of map
    global map, fov_recompute

    searching = True

    while searching == True:
        tele_x = libtcod.random_get_int(0, 1, MAP_WIDTH-1)
        tele_y = libtcod.random_get_int(0, 1, MAP_HEIGHT-1)

        #make sure tile isn't blocked

        if map[tele_x][tele_y].blocked == False:
            searching = False

    player.x = tele_x
    player.y = tele_y

    fov_recompute = True

    render_all()

    message('You teleport to another part of the map.', libtcod.cyan)


################################################################################
def make_map(): #function for creating the map
    global map, objects, stairs, max_rooms, ship_level
    objects = [player]

    #fill map with blocked tiles from which to carve
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT)]
            for x in range(MAP_WIDTH)]

    rooms = []
    num_rooms = 0

    for r in range(max_rooms):
        #random width & height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without leaving max values
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        new_room = Rect(x, y, w, h)

        #run through other rooms and see if they intersect
        failed = False

        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            #this will trigger if there are no intersections

            create_room(new_room)
            if num_rooms != 0:
                place_objects(new_room)
            #centre coordinates
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                #if this is the first room:
                player.x = new_x
                player.y = new_y

            else:
                #rooms need connecting with corridors

                #centre coords of last room created
                (prev_x, prev_y) = rooms[num_rooms-1].center()

                #toss a coin
                coin = libtcod.random_get_int(0,0,3)
                if coin == 0:
                    #horiz then vert
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)

                elif coin == 1:
                    #vertical tunnel then horiz
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

                elif coin == 2:
                    #vertical tunnel then horiz
                    create_v_tunnel_2(prev_y, new_y, prev_x)
                    create_h_tunnel_2(prev_x, new_x, new_y)

                elif coin == 3:
                    #vertical tunnel then horiz
                    create_v_tunnel_2(prev_y, new_y, prev_x)
                    create_h_tunnel_2(prev_x, new_x, new_y)

            #append new room to list of rooms
            rooms.append(new_room)
            num_rooms += 1

    #create the stairs or objective
    if ship_level == 20:
        ai_component = MindBehaviour()
        mind = Object(new_x, new_y, '0', 'Mind', libtcod.dark_grey, blocks=True, fighter=None, ai=ai_component)
        objects.append(mind)

    stairs = Object(new_x, new_y, 31, 'Stairs', libtcod.darkest_cyan, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()

################################################################################
def closest_monster(max_range):
    #find closest enemy to player
    closest_enemy = None
    closest_dist = max_range + 1

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance
            dist = player.distance_to(object)
            if dist < closest_dist: #closest so far, so store
                closest_enemy = object
                closest_dist = dist

    return closest_enemy
################################################################################
def check_equipment_slot(slot):
    #check if the state of equipment slot
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment

    return None
################################################################################
def get_all_equipped(obj): #returns all the items currecntly equipped
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)

        return equipped_list
    else:
        return []
################################################################################
def render_all(): #function for rendering all changes to screen
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_dark_wall
    global fov_recompute

    if fov_recompute:
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = map[x][y].block_sight
            if not visible:
                if map[x][y].explored:

                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
            else:
                #it's visible
                if wall:
                    libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                else:
                    libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)

                map[x][y].explored = True
    #draw all objects in FOV
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    #blit contents of con onto root
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)



    #show player's stats
    libtcod.console_set_default_background(panel, libtcod.darkest_gray)
    libtcod.console_clear(panel)

    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.darker_grey, libtcod.darkest_crimson)
    render_bar(1, 3, BAR_WIDTH, 'XP', player.fighter.xp, BASIC_LEVEL_UP + player.level*LEVEL_UP_INCREMENT, libtcod.darker_grey, libtcod.darkest_sea)

    libtcod.console_print_ex(panel, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, 'Ship Lvl: ' + str(ship_level))

    libtcod.console_set_default_foreground(panel, libtcod.turquoise)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)


################################################################################
################################################################################
def create_room(room):
    global map
    #go through tiles in rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

################################################################################
#######################corridor creation functions##############################
################################################################################
def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
################################################################################
def create_v_tunnel(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
################################################################################
def create_h_tunnel_2(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y+1].blocked = False
        map[x][y].block_sight = False
        map[x][y+1].block_sight = False
################################################################################
def create_v_tunnel_2(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x+1][y].blocked = False
        map[x][y].block_sight = False
        map[x+1][y].block_sight = False
################################################################################
def place_objects(room):
    #choose random number of monsters based on the level
    max_monsters = progression_table([[2, 1], [3, 2], [5, 3], [3, 4], [3, 5], [2, 6], [2, 7], [4, 8], [4, 9], [1, 10], [3, 11],[4,12],[5,13]])
    max_items = progression_table([[1, 1], [1, 2], [2, 3], [2, 4], [3, 5], [1, 6], [2, 7], [2, 8], [3, 9], [1, 10], [1, 11]])

    eny_chan = {}

    #the probability of each monster appearing depends on the level

    #idirans
    eny_chan['med'] = progression_table([[10,10],[3,12]])
    eny_chan['isoldier'] = progression_table([[5,10],[10,11],[15,12],[10,13]])
    eny_chan['icapt'] = progression_table([[5,10],[10,11],[1,12]])

    #pirates
    eny_chan['hpirate'] = progression_table([[10,7],[10,8],[10,9],[0,10]])
    eny_chan['hpiratecapt'] = progression_table([[2,7],[5,8],[6,9],[0,10]])

    #creatures
    eny_chan['giantspacerat'] = progression_table([[1,1],[1,2],[2,3],[0,4]])
    eny_chan['arachnoidworker'] = progression_table([[10,4],[10,5],[0,6],[0,7]])
    eny_chan['arachnoidqueen'] = progression_table([[1,4],[10,5],[0,6],[0,7]])
    eny_chan['arachnoidpod'] = progression_table([[0,4],[10,5],[10,6],[0,7]])
    eny_chan['tunnelcreeper'] = progression_table([[1,2],[2,3],[0,4],[0,7]])

    #bosses

    item_chan = {}

    #items

    item_chan['heal'] = 60
    item_chan['arc'] = progression_table([[10,1],[35,2],[1,3],[20,4],[15,5],[3,6]])
    item_chan['explosiveweapon'] = progression_table([[1,1],[3,2],[5,3],[5,4],[5,5],[3,6]])
    item_chan['syn'] = progression_table([[10,1],[15,2],[12,3],[20,4],[15,5],[3,6]])
    item_chan['patch'] = progression_table([[0,1],[1,3]])
    item_chan['shorts'] = progression_table([[0,1],[2,3]])
    item_chan['laser'] = progression_table([[4,1],[5,2],[5,3],[2,4],[5,5],[3,6]])
    item_chan['projectilerifle'] = progression_table([[1,1],[7,2],[8,3],[9,4],[9,5],[3,6]])
    item_chan['teleport'] = progression_table([[4,1],[10,2],[10,3],[10,4],[15,5],[3,6]])
    item_chan['hardvest'] = progression_table([[10,1],[35,2],[1,3],[20,4],[15,5],[3,6]])
    item_chan['leatherjack'] = progression_table([[10,1],[35,2],[1,3],[20,4],[15,5],[3,6]])
    item_chan['carbonhelm'] = progression_table([[1,1],[4,2],[5,3],[20,4],[15,5],[3,6]])
    item_chan['carbonjack'] = progression_table([[1,1],[5,2],[5,3],[20,4],[15,5],[3,6]])
    item_chan['chainmail'] = progression_table([[0,1],[2,3]])
    item_chan['mithrilplate'] = progression_table([[0,1],[1,3]])
    item_chan['mithrilblade'] = progression_table([[0,1],[1,3]])
    item_chan['combatknife'] = progression_table([[10,1],[15,2],[13,3],[20,4],[15,5],[3,6]])
    item_chan['diamondsword'] = progression_table([[0,1],[1,3]])
    item_chan['excalibur'] = progression_table([[0,1],[1,5]])
    item_chan['raygun'] = progression_table([[3,1],[7,2],[10,3],[20,4],[15,5],[3,6]])
    item_chan['plasmacannon'] = progression_table([[1,1],[5,2],[3,3],[2,4],[15,5],[3,6]])
    item_chan['energysabre'] = progression_table([[1,1],[2,2],[3,3],[2,4],[15,5],[3,6]])
    item_chan['powerfist'] = progression_table([[3,1],[6,2],[8,3],[2,4],[15,5],[3,6]])
    item_chan['mithrilhelm'] = progression_table([[0,1],[1,3]])
    item_chan['adamantiumplate'] = progression_table([[0,1],[1,3]])
    item_chan['adamantiumhelm'] = progression_table([[0,1],[1,3]])
    item_chan['combatjack'] = progression_table([[3,1],[12,2],[11,3],[13,4],[15,5],[12,6]])
    item_chan['combathelm'] = progression_table([[3,1],[12,2],[11,3],[13,4],[15,5],[19,6]])
    item_chan['grenade'] = progression_table([[10,1],[15,2],[15,3],[20,4],[25,5],[25,6]])
    item_chan['spacejeans'] = progression_table([[10,1],[35,2],[3,3],[10,4],[15,5],[3,6]])
    item_chan['combattrous'] = progression_table([[1,1],[3,2],[11,3],[20,4],[15,5],[3,6]])
    item_chan['laserpist'] = progression_table([[4,1],[6,2],[4,3],[5,4],[6,5],[6,6]])
    item_chan['laserrifle'] = progression_table([[1,1],[5,2],[5,3],[8,4],[15,5],[8,6]])
    item_chan['bfcannon'] = progression_table([[0,1],[2,3]])
    item_chan['paddedtrous'] = progression_table([[5,1],[10,2],[10,3],[20,4],[15,5],[3,6]])
    item_chan['metalshorts'] = progression_table([[0,1],[1,3]])
    item_chan['gumshield'] = progression_table([[0,1],[1,3]])
    item_chan['diamondcrown'] = progression_table([[0,1],[1,3]])
    item_chan['projpist'] = progression_table([[5,1],[5,2],[5,3],[10,4],[15,5],[5,6]])
    item_chan['spaceaxe'] = progression_table([[1,1],[3,2],[10,3],[20,4],[20,5],[20,6]])
    item_chan['techstaff'] = progression_table([[1,1],[3,2],[10,3],[20,4],[20,5],[20,6]])

    num_monsters = libtcod.random_get_int(0,0, max_monsters)


    for i in range(num_monsters):
        #pick random location for object
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        if not is_blocked(x, y):

            choice=rnd_dict(eny_chan)

            if choice == 'med':

                dice = libtcod.random_get_int(0,0,3)

                if dice < 1:
                    gun_component=Gun(30,laserburst,10,20)
                else:
                    gun_component=None

                fighter_component = Fighter(hp=50, agility=50, strength=30, dexterity=50, accuracy=50, xp=50, death_function = monster_death, blood_colour1=libtcod.purple, blood_colour2=libtcod.dark_purple, blood_colour3=libtcod.light_purple)
                ai_component = BasicMonster(courage=30, gun=gun_component)

                monster = Object(x, y, 'm', 'Medjel', libtcod.dark_orange, blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'isoldier':
                if libtcod.random_get_int(0,1,100) <= 20:
                    gun_component=Gun(30,cast_plasma, 70, 6)
                else:
                    gun_component=Gun(10,laserburst,30,10)
                fighter_component = Fighter(hp=libtcod.random_get_int(0, 200, 300), agility=libtcod.random_get_int(0, 30, 50), strength=libtcod.random_get_int(0, 75, 100), dexterity=libtcod.random_get_int(0, 40, 70), accuracy=libtcod.random_get_int(0, 40, 70), xp=200, death_function = monster_death, blood_colour1=libtcod.purple, blood_colour2=libtcod.dark_purple, blood_colour3=libtcod.light_purple)
                ai_component = BasicMonster(courage=190, gun=gun_component)

                monster = Object(x, y, 'i', 'Idiran Soldier', libtcod.darker_red, blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'hpirate':
                gun_component=Gun(10,bullet,20,10)
                fighter_component = Fighter(hp=100, agility=50, strength=60, dexterity=60, accuracy=50, xp=100, death_function = monster_death)
                ai_component = BasicMonster(courage=80, gun=gun_component)

                monster = Object(x, y, 'P', 'Pirate', libtcod.lighter_pink, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'hpiratecapt':
                dice = libtcod.random_get_int(0, 0, 6)
                if dice < 6:
                    gun_component=Gun(50, bullet, 20, 10)
                else:
                    gun_component=Gun(20, cast_shot, 40, 4)

                fighter_component = Fighter(hp=libtcod.random_get_int(0, 90, 140), agility=libtcod.random_get_int(0, 35, 60), strength=libtcod.random_get_int(0, 60, 70), dexterity=libtcod.random_get_int(0, 50, 60), accuracy=libtcod.random_get_int(0, 40, 60), xp=200, death_function = monster_death)
                ai_component = BasicMonster(courage=libtcod.random_get_int(0, 90, 100), gun=gun_component)

                monster = Object(x, y, 'C', 'Pirate Captain', libtcod.lighter_pink, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'icapt':
                if libtcod.random_get_int(0,1,100) <= 70:
                    gun_component=Gun(30,cast_plasma, 70, 6)
                else:
                    gun_component=Gun(10,laserburst,30,10)

                fighter_component = Fighter(hp=libtcod.random_get_int(0, 250, 370), agility=libtcod.random_get_int(0, 30, 50), strength=libtcod.random_get_int(0, 70, 110), dexterity=libtcod.random_get_int(0, 40, 90), accuracy=libtcod.random_get_int(0, 40, 70), xp=250, death_function = monster_death, blood_colour1=libtcod.purple, blood_colour2=libtcod.dark_purple, blood_colour3=libtcod.light_purple)
                ai_component = BasicMonster(courage=245, gun=gun_component)

                monster = Object(x, y, 'I', 'Idiran Section Leader', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'giantspacerat':

                fighter_component = Fighter(hp=libtcod.random_get_int(0,30,70), agility=libtcod.random_get_int(0,30,50), strength=libtcod.random_get_int(0,30,50), dexterity=libtcod.random_get_int(0,30,50), accuracy=50, xp=50, death_function = monster_death, blood_colour1=libtcod.red, blood_colour2=libtcod.dark_red, blood_colour3=libtcod.light_red)
                ai_component = BasicMonster(courage=50)

                monster = Object(x, y, 'R', 'Giant Space-Rat', libtcod.dark_grey, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'arachnoidworker':

                fighter_component = Fighter(hp=libtcod.random_get_int(0,40,90), agility=libtcod.random_get_int(0,40,70), strength=libtcod.random_get_int(0,40,60), dexterity=libtcod.random_get_int(0,30,70), accuracy=50, xp=75, death_function = monster_death, blood_colour1=libtcod.green, blood_colour2=libtcod.dark_green, blood_colour3=libtcod.light_green)
                ai_component = BasicMonster(courage=50)

                monster = Object(x, y, 'w', 'Arachnoid Worker', libtcod.dark_purple, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'arachnoidqueen':

                fighter_component = Fighter(hp=libtcod.random_get_int(0,90,140), agility=libtcod.random_get_int(0,60,80), strength=libtcod.random_get_int(0,60,80), dexterity=libtcod.random_get_int(0,50,80), accuracy=50, xp=150, death_function = monster_death, blood_colour1=libtcod.green, blood_colour2=libtcod.dark_green, blood_colour3=libtcod.light_green)
                ai_component = BasicMonster(courage=150)

                monster = Object(x, y, 'Q', 'Arachnoid Queen', libtcod.dark_purple, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'arachnoidpod':

                fighter_component = Fighter(hp=libtcod.random_get_int(0,100,140), agility=0, strength=0, dexterity=0, accuracy=0, xp=90, death_function = pod_death, blood_colour1=libtcod.green, blood_colour2=libtcod.dark_green, blood_colour3=libtcod.light_green)
                ai_component = PodBehaviour(4)

                monster = Object(x, y, 'O', 'Arachnoid Birth Pod', libtcod.darkest_purple, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'tunnelcreeper':

                fighter_component = Fighter(hp=libtcod.random_get_int(0,30,50), agility=libtcod.random_get_int(0,60,80), strength=libtcod.random_get_int(0,20,40), dexterity=libtcod.random_get_int(0,50,80), accuracy=50, xp=60, death_function = monster_death, blood_colour1=libtcod.red, blood_colour2=libtcod.dark_red, blood_colour3=libtcod.light_red)
                ai_component = BasicMonster(courage=50)

                monster = Object(x, y, 't', 'Tunnel Creeper', libtcod.dark_green, blocks=True, fighter=fighter_component, ai=ai_component)

            objects.append(monster)

    #create items
    num_items = libtcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)


        if not is_blocked(x,y):
            dice = rnd_dict(item_chan)

            if dice == 'heal':
                #create med
                item_component = Item(use_function=cast_heal)
                item = Object(x, y, '+', 'MediSphere', libtcod.violet, item=item_component)

            elif dice == 'arc':
                item_component = Item(use_function=cast_arc)
                item = Object(x,y,'*', 'Arc Caster', libtcod.black, item=item_component)

            elif dice == 'explosiveweapon':
                gun_component=Gun(30,cast_shot,90,3)
                equipment_component = Equipment(slot='Hands', accuracy_bonus=-10)
                item = Object(x,y,'L', 'Explosive Projectile Weapon', libtcod.black, equipment=equipment_component, gun=gun_component)

            elif dice == 'projectilerifle':
                gun_component=Gun(10,bullet,34,30)
                equipment_component = Equipment(slot='Hands', accuracy_bonus=10)
                item = Object(x,y,'L', 'Projectile Rifle', libtcod.black, equipment=equipment_component, gun=gun_component)

            elif dice == 'syn':

                item_component = Item(use_function=cast_confuse)
                item = Object(x, y, '*', 'Synaptic Inhibitor', libtcod.black, item=item_component)

            elif dice == 'patch':
                equipment_component = Equipment(slot='Left Eye', armour_bonus=1)
                item_component = Item()
                item = Object(x, y, '-', 'Very Fashionable Eye-Patch', libtcod.pink, equipment=equipment_component)

            elif dice == 'shorts':
                equipment_component = Equipment(slot='Legs', armour_bonus=8)
                item_component = Item()
                item = Object(x, y, 'n', 'Plated Kilt', libtcod.blue, equipment=equipment_component)

            elif dice == 'laser':
                gun_component=Gun(100,laserburst,20,10)
                equipment_component = Equipment(slot='Hands', accuracy_bonus=30)
                item = Object(x, y, '?', 'Laser Carbine', libtcod.light_crimson, equipment=equipment_component, gun=gun_component)

            elif dice == 'teleport':
                item_component = Item(use_function=cast_teleport)
                item = Object(x,y,'*','Teleport', libtcod.dark_blue, item=item_component)

            elif dice == 'hardvest':
                equipment_component = Equipment(slot='Upper Body', armour_bonus=20, dexterity_bonus=-5, agility_bonus=-7)
                item_component=Item()
                item = Object(x,y,'#','Hard Vest',libtcod.dark_sepia,equipment=equipment_component)

            elif dice == 'leatherjack':
                equipment_component = Equipment(slot='Upper Body', armour_bonus=4, agility_bonus=-1)
                item_component=Item()
                item = Object(x,y,'#', 'Leather Jacket', libtcod.sepia, equipment=equipment_component)

            elif dice == 'carbonhelm':
                equipment_component = Equipment(slot='Head', armour_bonus=8)
                item_component=Item()
                item=Object(x,y,'^','Carbon Helmet',libtcod.darkest_grey,equipment=equipment_component)

            elif dice == 'carbonjack':
                equipment_component = Equipment(slot='Upper Body', armour_bonus=12)
                item_component=Item()
                item=Object(x,y,'#', 'Carbon Jacket', libtcod.darkest_grey,equipment=equipment_component)

            elif dice == 'chainmail':
                equipment_component=Equipment(slot='Upper Body', armour_bonus=10,agility_bonus=-10,dexterity_bonus=-5)
                item_component=Item()
                item = Object(x,y,'#','Chain Mail Vest',libtcod.grey,equipment=equipment_component)

            elif dice == 'mithrilplate':
                equipment_component=Equipment(slot='Upper Body', armour_bonus=20)
                item_component=Item()
                item = Object(x,y,'#','Mithril Chest Plate',libtcod.light_grey,equipment=equipment_component)

            elif dice == 'mithrilblade':
                equipment_component=Equipment(slot='Hands', agility_bonus=10,dexterity_bonus=5,strength_bonus=17)
                item_component=Item()
                item = Object(x,y,'/','Mithril Blade',libtcod.light_grey,equipment=equipment_component)

            elif dice == 'combatknife':
                equipment_component=Equipment(slot='Hands', strength_bonus=8, dexterity_bonus=2)
                item_component=Item()
                item = Object(x,y,'/','Combat Knife',libtcod.grey,equipment=equipment_component)

            elif dice == 'diamondsword':
                equipment_component=Equipment(slot='Hands',strength_bonus=15,agility_bonus=-7, dexterity_bonus= -1)
                item_component=Item()
                item = Object(x,y,'/','Diamond Sword',libtcod.darkest_sky,equipment=equipment_component)

            elif dice == 'excalibur':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=5, strength_bonus=25)
                item_component=Item()
                item = Object(x,y,'#','Excalibur',libtcod.grey,equipment=equipment_component)

            elif dice == 'raygun':
                equipment_component=Equipment(slot='Hands',strength_bonus=2, accuracy_bonus=5)
                gun_component=Gun(20,laserburst,60,6)
                item = Object(x,y,'l','Ray Gun',libtcod.red,equipment=equipment_component,gun=gun_component)

            elif dice == 'plasmacannon':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=-10, agility_bonus=-10, strength_bonus=5,accuracy_bonus=-5)
                gun_component=Gun(30,cast_plasma, 70, 6)
                item = Object(x,y,'l','Plasma Cannon',libtcod.grey,equipment=equipment_component,gun=gun_component)

            elif dice == 'energysabre':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=3, agility_bonus=4, strength_bonus=16)
                item = Object(x,y,'/','Energy Sabre',libtcod.orange,equipment=equipment_component)

            elif dice == 'powerfist':
                equipment_component=Equipment(slot='Hands',strength_bonus=9)
                item = Object(x,y,'/','Power Fist',libtcod.grey,equipment=equipment_component)

            elif dice == 'mithrilhelm':
                equipment_component=Equipment(slot='Head', armour_bonus=12)
                item_component=Item()
                item = Object(x,y,'^','Mithril Helmet',libtcod.light_grey,equipment=equipment_component)

            elif dice == 'adamantiumplate':
                equipment_component=Equipment(slot='Upper Body', armour_bonus=24, agility_bonus=-9,dexterity_bonus=-7)
                item_component=Item()
                item = Object(x,y,'#','Adamantium Chest Plate',libtcod.dark_grey,equipment=equipment_component)

            elif dice == 'adamantiumhelm':
                equipment_component=Equipment(slot='Head', armour_bonus=16, agility_bonus=-3,dexterity_bonus=-2)
                item_component=Item()
                item = Object(x,y,'^','Adamantium Helmet',libtcod.dark_grey,equipment=equipment_component)

            elif dice == 'combatjack':
                equipment_component=Equipment(slot='Upper Body', armour_bonus=10, agility_bonus=-1,dexterity_bonus=3,accuracy_bonus=4)
                item_component=Item()
                item = Object(x,y,'#','Combat Jacket',libtcod.dark_sepia,equipment=equipment_component)

            elif dice == 'combathelm':
                equipment_component=Equipment(slot='Head', armour_bonus=7,accuracy_bonus=3)
                item_component=Item()
                item = Object(x,y,'^','Combat Helmet',libtcod.dark_sepia,equipment=equipment_component)

            elif dice == 'grenade':
                item_component=Item(use_function=grenade_toss)
                item = Object(x,y,'!','Grenade',libtcod.dark_green,item=item_component)

            elif dice == 'spacejeans':
                equipment_component=Equipment(slot='Lower Body', armour_bonus=2)
                item_component=Item()
                item = Object(x,y,'n','Space Jeans',libtcod.dark_blue,equipment=equipment_component)

            elif dice == 'combattrous':
                equipment_component=Equipment(slot='Lower Body', armour_bonus=7,agility_bonus=5)
                item_component=Item()
                item = Object(x,y,'n','Combat Trousers',libtcod.dark_sepia,equipment=equipment_component)

            elif dice == 'laserpist':
                equipment_component=Equipment(slot='Hands',strength_bonus=2, accuracy_bonus=6)
                gun_component=Gun(90,laserburst,10,12)
                item = Object(x,y,'l','Laser Pistol',libtcod.red,equipment=equipment_component,gun=gun_component)

            elif dice == 'laserrifle':
                equipment_component=Equipment(slot='Hands',strength_bonus=4, accuracy_bonus=8, dexterity_bonus=-5, agility_bonus=-7)
                gun_component=Gun(100,laserburst,80,6)
                item = Object(x,y,'l','Laser Rifle',libtcod.red,equipment=equipment_component,gun=gun_component)

            elif dice == 'bfcannon':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=-10, agility_bonus=-10, strength_bonus=5,accuracy_bonus=-5)
                gun_component=Gun(50,cast_plasma, 90, 3)
                item = Object(x,y,'l','BF Cannon',libtcod.grey,equipment=equipment_component,gun=gun_component)

            elif dice == 'paddedtrous':
                equipment_component=Equipment(slot='Lower Body', armour_bonus=6,agility_bonus=-3)
                item_component=Item()
                item = Object(x,y,'n','Combat Trousers',libtcod.dark_sepia,equipment=equipment_component)

            elif dice == 'metalshorts':
                equipment_component=Equipment(slot='Lower Body', armour_bonus=7,agility_bonus=-7)
                item_component=Item()
                item = Object(x,y,'n','Metal Shorts',libtcod.grey,equipment=equipment_component)

            elif dice == 'gumshield':
                equipment_component=Equipment(slot='Gums', armour_bonus=1)
                item_component=Item()
                item = Object(x,y,'^','Gum Shield',libtcod.green,equipment=equipment_component)

            elif dice == 'diamondcrown':
                equipment_component=Equipment(slot='Head', armour_bonus=13)
                item_component=Item()
                item = Object(x,y,'^','Diamond Crown',libtcod.dark_sky,equipment=equipment_component)

            elif dice == 'projpist':
                gun_component=Gun(20,bullet,16,12)
                equipment_component = Equipment(slot='Hands', accuracy_bonus=1,strength_bonus=3)
                item = Object(x,y,'l', 'Projectile Pistol', libtcod.black, equipment=equipment_component, gun=gun_component)

            elif dice == 'spaceaxe':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=-2, agility_bonus=-7, strength_bonus=20)
                item = Object(x,y,'/','Space Axe',libtcod.grey,equipment=equipment_component)

            elif dice == 'techstaff':
                equipment_component=Equipment(slot='Hands',dexterity_bonus=3, agility_bonus=4, strength_bonus=16)
                item = Object(x,y,'/','Tech Staff',libtcod.dark_blue,equipment=equipment_component)

            objects.append(item);
            item.send_to_back()

################################################################################
def progression_table(table): #table with spawn probabilities for each level
    for (value, level) in reversed(table):
        if ship_level >= level:
            return value
    return 0
################################################################################
def rnd_index(chances): #function for getting probabilities from sum of values

    dice = libtcod.random_get_int( 0 , 1, sum(chances))

    running_tot = 0
    choice = 0
    for w in chances:
        running_tot += w

        if dice <= running_tot:
            return choice #return outcome
        choice += 1
################################################################################
def rnd_dict(chances_dict): #get probability test outcomes using string references from table

    chances = chances_dict.values()
    strings = chances_dict.keys()

    return strings[rnd_index(chances)]

################################################################################
def is_blocked(x, y): #check if a certain map tile is blocked
    if map[x][y].blocked:
        return True

    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False
################################################################################
def player_death(player): #function for player death
    global game_state
    message('You were killed.', libtcod.red)
    game_state = 'dead'

    player.char = '%'
    player.color = libtcod.dark_red
################################################################################
def monster_death(monster): #function for typical monster death
    message('The ' + monster.name.capitalize() + ' is killed.', libtcod.sea)
    monster.char = '%'
    monster.color = monster.fighter.blood_colour1
    monster.blocks = False #this shouldn't block
    monster.fighter = None
    monster.ai = None
    monster.name = 'Remains of ' + monster.name
    monster.send_to_back()
################################################################################
def pod_death(monster): #death function for a pod spawner
    message('The ' + monster.name.capitalize() + ' explodes!', libtcod.sea)

    #create debris objects

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat', monster.fighter.blood_colour2, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat',monster.fighter.blood_colour1, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat', monster.fighter.blood_colour3, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat', monster.fighter.blood_colour1, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat', monster.fighter.blood_colour2, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4),monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat',monster.fighter.blood_colour1, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    splat = Object(monster.x + libtcod.random_get_int(0,-4,4), monster.y + libtcod.random_get_int(0,-4,4), '.', monster.name + ' splat', monster.fighter.blood_colour1, blocks=False, fighter=None, ai=None)
    objects.append(splat)
    splat.send_to_back()

    monster.char = '%'
    monster.color = monster.fighter.blood_colour1
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'Remains of ' + monster.name
    monster.send_to_back()

################################################################################
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #Render a status bar
    bar_width = int(float(value) / maximum * total_width)

    #Initiate the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    #Draw the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    #Centre value for the text
    libtcod.console_set_default_foreground(panel, libtcod.cyan)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ': ' + str(value) + '/' + str(maximum))
################################################################################
def message(new_msg, color = libtcod.white): #generic function for printing messages
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        #remove the first line if the buffer is full
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        #add new line
        game_msgs.append( (line, color) )
################################################################################
def new_game(player_type, player_accuracy, player_agility, player_dexterity, player_strength, player_name): #function for starting a new game
    global player, inventory, game_msgs, game_state, ship_level, max_rooms
    #create the player object
    fighter_component = Fighter(hp=player_strength+50, agility=player_agility, strength=player_strength, dexterity=player_dexterity, accuracy=player_accuracy, xp=0, death_function = player_death)
    player = Object(0, 0, '@', player_name, libtcod.darker_grey, blocks=True, fighter=fighter_component)

    player.level = 1

    game_state = 'playing'

    inventory = [] #intilialise inventory

    max_rooms = 4

    ship_level = 1

    #call functions to begin game

    make_map()

    initialize_fov()

    message ('You step aboard the ship and begin your mission. From here onwards it is success or death!')

    #set player stats depending on class

    if player_type == 'Culture Human':
        #give the player starting items:
        equipment_component = Equipment(slot='Hands', strength_bonus=2, dexterity_bonus=-5, accuracy_bonus=10)
        gun_component = Gun(30,laserburst,10, 10)
        obj = Object(0,0,'l', 'Laser Pistol', libtcod.grey, equipment=equipment_component, gun=gun_component)
        inventory.append(obj)
        equipment_component.equip()


        equipment_component = Equipment(slot='Upper Body', armour_bonus=7)
        obj = Object(0,0,'#', 'Trench Coat', libtcod.black, equipment=equipment_component)
        inventory.append(obj)
        equipment_component.equip()

        item_component = Item(use_function=cast_confuse)
        item = Object(0, 0, '*', 'Synaptic Inhibitor', libtcod.black, item=item_component)
        inventory.append(item)

        msgbox('As an agent of the Cultures notorious Special Circumstances division you are tasked with investigating the remains of an ancient ship. Left dormant in space for countless millennia, the relic resembles a huge chrome sphere 3 kilometers across. It is the whisper of a long forgotten race, rumoured to have been as technologically advanced as the Culture, obliterated by some unknown cosmic terror. Located somewhere on the ship is the last known sentient entity which belonged to this race - a hyperintelligent AI mind. If the Culture can retrieve the Mind, it may explain the civilisations mysterious demise and prevent the same happening to the Culture as well as aid in the war against the Idirans. You must locate the Mind and negotiate with it. You will encounter many dangers on the way and the Idirans may have already infiltrated the vessel. Good luck.')

    elif player_type == 'Rogue':
        item_component = Item(use_function=cast_confuse)
        item = Object(0, 0, '*', 'Synaptic Inhibitor', libtcod.black, item=item_component)
        inventory.append(item)

        equipment_component = Equipment(slot='Hands', strength_bonus=4, dexterity_bonus=3, agility_bonus=3)
        obj = Object(0,0,'l', 'Nano-Blade', libtcod.grey, equipment=equipment_component)
        inventory.append(obj)
        equipment_component.equip()

        item_component = Item(use_function=cast_teleport)
        item = Object(0, 0, '*', 'Teleporter', libtcod.black, item=item_component)
        inventory.append(item)

        item_component = Item(use_function=cast_heal)
        item = Object(0, 0, '+', 'Medisphere', libtcod.black, item=item_component)
        inventory.append(item)

        msgbox('You are a rogue. You have no employer; you fight for you own principles and motives. You are a master thief, and are motivated mainly by money and personal gain - you have little interest in galactic politics. When you were tipped off about this huge ancient shift drifting, dead, in space you were quick to see its opportunity. Aboard the giant sphere is a sentient Mind, as ancient as the ship itself. If you could get your hands on it, you could sell it and make an absolute fortune.The heist will be dangerous however, since rumour has it that there are already pirates and mercenaries aboard the ship. It is also possible that the Culture or the mighty Idirans have caught wind and are looking for the same thing as you.')

    elif player_type == 'Mercenary':
        equipment_component = Equipment(slot='Hands', strength_bonus=2, dexterity_bonus=-5, accuracy_bonus=20)
        gun_component = Gun(30,bullet,50, 30)
        obj = Object(0,0,'l', 'Rifle', libtcod.grey, equipment=equipment_component, gun=gun_component)
        inventory.append(obj)
        equipment_component.equip()

        msgbox('You are a mercenary, a hired gun and a good one at that. You were sent to this ship by a shady client, willing to pay you the biggest sum of money you have ever laid eyes on. To recieve the rest of your payment, you must venture into the depths of an ancient monolithic ship, resembling a huge chrome sphere 3 kilometers across. Aboard the ship is some kind of old AI which you must find. When it is located, you must capture it and meet with your client. It will be difficult - it is likely that the Idiran-Culture war will have a role of interference on this one. Just make sure you use your brain as well as braun. Good luck.')

################################################################################
def win_game():
    img = libtcod.image_load('menu2.png')

    libtcod.image_blit_2x(img, 0, 0, 0)

    libtcod.console_set_default_foreground(0 , libtcod.cyan)
    libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, libtcod.CENTER, 'CULTUREHACK')
    libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.CENTER, 'BY GABRIEL HADDON-HILL')

    msgbox('You approach the large, metallic ellipsoid. You have found it! This is where your fortune awaits! You reach out to touch it. Suddenly there is a ear-popping crack, and you feel as though you are being ripped from existence. You lose your awareness of the situation for a while and when you regain it, all is very different. You seem to be viewing the ship`s interior from an almost spherical perspective. You can see much more clearly than before, and feel as though there are extra senses you did not previously possess. Below you there is a gelatinous looking red lump. There appear to be similar lumps spread around it as though something was squashed with considerable force. You suddenly realise that the central lump is at the very spot you were standing on, and you are now where the Mind was! What has happened?! You start to feel like your thoughts are being invaded. Impossible geometry and highly complex logic fill your mind and you start to feel like you are being invaded by something much greater than you. With a sudden flash of panic, you realise what is happening. Your consciousness is being assimilated by the Mind! The stream of relentless thought reaches a peak, and you desperately try to pull away. It is hopeless however, as you are already inside. Slowly, you begin to lose your mental ability and after several minutes, you cannot even remember your name. It does not take long until your own consciousness is completely reconstituted into the Mind`s, and you are nothing more than a pile of dead tissue. You journey ends here.')
################################################################################
def initialize_fov(): #function for field of view initiation
    global fov_recompute, fov_map

    libtcod.console_clear(con) #removes previous FOV

    fov_recompute = True

    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
################################################################################
def save_game(): #save game to file

    #create new shelve
    print 'Saving game...'
    print 'Opening shelve...'
    file = shelve.open('savegame.gab', 'n')
    file['map']=map
    file['objects']=objects
    file['player_index']=objects.index(player)
    file['inventory']=inventory
    file['game_msgs']=game_msgs
    file['game_state']=game_state
    file['stairs_index'] = objects.index(stairs)
    file['ship_level'] = ship_level
    file['max_rooms'] = max_rooms

    file.close()

    print 'Done...'
################################################################################
def load_game(): #load game from file
    global map, objects, player, inventory, game_msgs, game_state, stairs, ship_level, max_rooms

    print 'Loading game...'
    file = shelve.open('savegame.gab', 'r')
    print 'Opening shelve...'
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    stairs = objects[file['stairs_index']]
    ship_level = file['ship_level']
    max_rooms = file['max_rooms']

    file.close()

    print 'Done...'

    initialize_fov()
################################################################################
def play_game(): #main game loop
    global key, mouse

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()

    while not libtcod.console_is_window_closed():

        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)

        #draw everything
        render_all()

        #show changes on screen
        libtcod.console_flush()

        level_check()

        #removing objects from previous positions
        for object in objects:
            object.clear()

        #handle keys and exit function
        player_action = handle_keys()

        if player_action == 'exit':
            save_game() #save game and exit
            main_menu()

        #let NPCs take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()
################################################################################
def msgbox(text, width=50): #generic message box
    menu(text, [], width)
################################################################################
def text_entry(): #function for text entry

    command = ""
    x = (SCREEN_WIDTH/2) - 8
    y = SCREEN_HEIGHT/2
    finished = False
    while finished == False: #check for press until entry is finished

        key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)

        libtcod.console_set_char(0, x,  y, "_")
        libtcod.console_set_char_foreground(0, x, y, libtcod.white)

        if key.vk == libtcod.KEY_BACKSPACE and x > 42:
            libtcod.console_set_char(0, x,  y, " ")
            libtcod.console_set_char_foreground(0, x, y, libtcod.white)
            command = command[:-1]
            x -= 1

        elif key.vk == libtcod.KEY_ENTER:
            if command != "" and command != " " and command != "  " and command != "   " and command != "    " and command != "     " and command != "      ":
                finished = True
                return command
        elif key.vk == libtcod.KEY_ESCAPE:
            command = ""
            char_gen1()
        elif key.c > 0 and x < 58 and key.c != 8: #it cant equal 8 because 8 is backspace
            letter = chr(key.c)
            libtcod.console_set_char(0, x, y, letter)  #print new character at appropriate position on screen
            libtcod.console_set_char_foreground(0, x, y, libtcod.white)
            command += letter  #add to the string
            x += 1

        libtcod.console_flush()


################################################################################
def char_gen2(player_type, player_accuracy, player_agility, player_dexterity, player_strength): #second stage of character creation

    img = libtcod.image_load('menu2.png')
    player_name = None
    named = False
    while not libtcod.console_is_window_closed():

        libtcod.image_blit_2x(img, 0, 0, 0)

        libtcod.console_set_default_foreground(0 , libtcod.cyan)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, libtcod.CENTER, 'Enter a name for your character')
        player_name = text_entry()

        #initialise new game
        new_game(player_type, player_accuracy, player_agility, player_dexterity, player_strength, player_name)
        play_game()

################################################################################
def char_gen1(): #first screen of character generation

    img = libtcod.image_load('menu2.png')
    timer = 0
    choice = None

    while timer < 10000: #timer is needed to stop user accidentally pressing input straight away
        timer += 0.01

    while not libtcod.console_is_window_closed():

        libtcod.image_blit_2x(img, 0, 0, 0)

        libtcod.console_set_default_foreground(0 , libtcod.cyan)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, libtcod.CENTER, 'Choose your character class')

        #show options and wait for choice
        chartype = menu('', ['Culture Human', 'Rogue', 'Mercenary'], 24)

        if chartype == 0:
            player_type = 'Culture Human'
            player_strength = libtcod.random_get_int(0, 45, 70)
            player_agility = libtcod.random_get_int(0, 45, 70)
            player_dexterity = libtcod.random_get_int(0, 45, 70)
            player_accuracy = libtcod.random_get_int(0, 45, 70)
            char_gen2(player_type, player_accuracy, player_agility, player_dexterity, player_strength)
        elif chartype == 1:
            player_type = 'Rogue'
            player_strength = libtcod.random_get_int(0, 35, 65)
            player_agility = libtcod.random_get_int(0, 55, 75)
            player_dexterity = libtcod.random_get_int(0, 50, 75)
            player_accuracy = libtcod.random_get_int(0, 55, 60)
            char_gen2(player_type, player_accuracy, player_agility, player_dexterity, player_strength)
        elif chartype == 2:
            player_type = 'Mercenary'
            player_strength = libtcod.random_get_int(0, 55, 75)
            player_agility = libtcod.random_get_int(0, 35, 55)
            player_dexterity = libtcod.random_get_int(0, 45, 60)
            player_accuracy = libtcod.random_get_int(0, 55, 70)
            char_gen2(player_type, player_accuracy, player_agility, player_dexterity, player_strength)

################################################################################
def main_menu():
    img = libtcod.image_load('menu2.png')

    while not libtcod.console_is_window_closed():



        libtcod.image_blit_2x(img, 0, 0, 0)

        libtcod.console_set_default_foreground(0 , libtcod.cyan)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 4, libtcod.BKGND_NONE, libtcod.CENTER, 'CULTUREHACK')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.CENTER, 'BY GABRIEL HADDON-HILL')

        #show options and wait for choice
        choice = menu('', ['New Game', 'Load Game', 'Quit', 'Help'], 24)

        if choice == 0:
            char_gen1()

        elif choice == 1:
            try:
                load_game()
            except:
                msgbox('\n No save file found. \n', 24)
                continue
            play_game()

        elif choice == 2:
            exit()

        elif choice == 3:
            show_help()

################################################################################
def show_help():

    timer = 0

    while timer < 10000: #timer is needed to stop user accidentally pressing input straight away
        timer += 0.01

    msgbox('Welcome to Culturehack! \n\nThe aim of the game is simple: find the Mind on the 20th level. \nIt will be far from easy though, and if your character is killed you will have to start again. \nTo descend a level, find the stairs on each map. Along the way you will have to fight many enemies. \nList of commands: \n8,7,8,9,4,6,1,2,3 - move/attack directions \n5 - do nothing for a turn \nr - initiate ranged attack \ng - get an item \n< - descend a level \nd - drop an item \ni - show the inventory \n\nMouse over an object to show its name. The mouse is also used to select targets in ranged attacks.')

################################################################################
#-----------------------------GAME INITIALISATION------------------------------#
################################################################################

#initialising the font that the console will use
libtcod.console_set_custom_font('courier10x10_aa_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

print 'Initilaising Root...'
#initialising the console window with parameters
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'CultureHack', False)

print 'Initilaising Off-screen...'
#initialising an off-screen console used for gui elementss
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

libtcod.sys_set_fps(LIMIT_FPS)

print 'Welcome to CultureHack ver 0.9!'

main_menu()

################################################################################
#------------------------------------------------------------------------------#
#-----------------------------------END----------------------------------------#
#------------------------------------------------------------------------------#
################################################################################