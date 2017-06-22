import libtcodpy as libtcod
import math

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

MAP_WIDTH = 80
MAP_HEIGHT = 45

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

MAX_ROOM_MONSTERS = 3

# game speeds
PLAYER_SPEED = 2
DEFAULT_SPEED = 8
DEFAULT_ATTACK_SPEED = 20

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)



class Object:
	# Generic object used for various game features
	# always represented by a character in console
	def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, speed=DEFAULT_SPEED):
		self.name = name
		self.blocks = blocks
		self.x = x
		self.y = y
		self.char = char
		self.color = color
		self.speed = speed
		self.wait = 0

		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self

		self.ai = ai
		if self.ai:
			self.ai.owner = self

	def move(self, dx, dy):
		# move object by (dx, dy) unless blocked
		if not is_blocked(self.x + dx, self.y + dy):
			self.x += dx
			self.y += dy
		
		self.wait = self.speed

	def draw(self):
		# if an object is in player's FOV
		if libtcod.map_is_in_fov(fov_map, self.x, self.y):
			# set object color and draw the appropriate
			# character at the appropriate location
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		# clear the object's character from console
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

	def move_towards(self, target_x, target_y):
		# vector from this object to the target
		dx = target_x - self.x
		dy = target_y - self.y
		distance = math.sqrt(dx ** 2 + dy ** 2)

		# normalize vector, round x and y values to integers
		dx = int(round(dx / distance))
		dy = int(round(dy / distance))
		self.move(dx, dy)

	def distance_to(self, other):
		# return distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)

	def send_to_back(self):
		# this object will now be drawn first, so other objects will be drawn on top
		global objects
		objects.remove(self)
		objects.insert(0, self)


class Tile:
	# A map tile and its properties
	def __init__(self, blocked, block_sight = None):
		self.explored = False

		self.blocked = blocked

		# by default, if a tile is blocked, it also blocks sight
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight


class Rect:
	# Rectangle, used to represent a room
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)

	def intersect(self, other):
		# returns true if this rect intersects with other rect
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and
				self.y1 <= other.y2 and self.y2 >= other.y1)


class Fighter:
	# combat-related properties and methods (monster, player, npc)
	def __init__(self, hp, defense, power, death_function=None, attack_speed=DEFAULT_ATTACK_SPEED):
		self.max_hp = hp
		self.hp = hp
		self.defense = defense
		self.power = power
		self.death_function = death_function
		self.attack_speed = attack_speed

	def take_damage(self, damage):
		if damage > 0:
			self.hp -= damage

		# check for death and call death function, if extant
		if self.hp <= 0:
			function = self.death_function
			if function is not None:
				function(self.owner)

	def attack(self, target):
		damage = self.power - target.fighter.defense

		if damage > 0:
			print self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.'
			target.fighter.take_damage(damage)
		else:
			print self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!'


class BasicMonster:
	# AI for a basic monster
	def take_turn(self):
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			# if not close enough to attack, move closer
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)
			# if it's close enough and the player is alive, attack
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)



def handle_keys():
	global fov_recompute

	key = libtcod.console_check_for_keypress()
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		# Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'		# exit game

	if game_state == 'playing':
		if player.wait > 1: # still waiting, don't take turn
			player.wait -= 1
			return
		
		#movement keys
		if libtcod.console_is_key_pressed(libtcod.KEY_UP):
			player_move_or_attack(0, -1)
			fov_recompute = True

		elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
			player_move_or_attack(0, 1)
			fov_recompute = True

		elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
			player_move_or_attack(-1, 0)
			fov_recompute = True

		elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
			player_move_or_attack(1, 0)
			fov_recompute = True
		else:
			return 'didnt-take-turn'


def make_map():
	global map

	# fill map with blocked tiles
	map = [[ Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	rooms = []
	num_rooms = 0

	for r in range(MAX_ROOMS):
		# random width and height
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		# random positions without going out of bounds
		x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
		y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

		new_room = Rect(x, y, w, h)

		# see if new room intersects with previously created rooms
		failed = False
		for other_room in rooms:
			if new_room.intersect(other_room):
				failed = True
				break

		if not failed:
			# room is valid, so create it
			create_room(new_room)

			(new_x, new_y) = new_room.center()

			if num_rooms == 0:
				# center player in first room
				player.x = new_x
				player.y = new_y

			else: # connect new room to previously created room
				# center of previous room
				(prev_x, prev_y) = rooms[num_rooms - 1].center()

				# flip a coin to start with horizontal or vertical tunnel
				if libtcod.random_get_int(0, 0, 1) == 1:
					# first horizontal, then vertical
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				else:
					# first vertical, then horizontal
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)

			# add objects to the new room
			place_objects(new_room)

			# append new room to list
			rooms.append(new_room)
			num_rooms += 1



def render_all():
	global fov_map, color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute

	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

		# set tile colors according to FOV
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				visible = libtcod.map_is_in_fov(fov_map, x, y)
				wall = map[x][y].block_sight
				if not visible: # out of FOV
					# if not visible right now, player can only see it if it's been explored
					if map[x][y].explored:
						if wall:
							libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
						else:
							libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
				else:
					if wall:
						libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
					else:
						libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
					map[x][y].explored = True


	# draw all objects in object list
	for object in objects:
		if object != player:
			object.draw()
	player.draw()

	# blit contents of "con" to the root console
	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

	# show the player's stats
	libtcod.console_set_default_foreground(con, libtcod.white)
	libtcod.console_print_ex(con, 1, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.LEFT,
		'HP: ' + str(player.fighter.hp) + '/' + str(player.fighter.max_hp))


def create_room(room):
	global map
	# make tiles within rectangle able to be traversed
	for x in range(room.x1 + 1, room.x2):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False


def create_h_tunnel(x1, x2, y):
	global map
	for x in range(min(x1, x2), max(x1, x2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
	global map
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False


def place_objects(room):
	# choose random number of monsters
	num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

	for i in range(num_monsters):
		# choose random spot for this monster
		x = libtcod.random_get_int(0, room.x1, room.x2)
		y = libtcod.random_get_int(0, room.y1, room.y2)

		# place if tile is not blocked
		if not is_blocked(x, y):
			if libtcod.random_get_int(0, 0, 100) < 80: # 80% chance of getting an orc
				# create orc
				fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
				ai_component = BasicMonster()
				monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
					blocks=True, fighter=fighter_component, ai=ai_component)
			else:
				# create a troll
				fighter_component = Fighter(hp=16, defense=1, power=4, death_function=monster_death)
				ai_component = BasicMonster()
				monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
					blocks=True, fighter=fighter_component, ai=ai_component)

			objects.append(monster)


def is_blocked(x, y):
	# test the tile map
	if map[x][y].blocked:
		return True

	# check for blocking objects
	for obj in objects:
		if obj.blocks and obj.x == x and obj.y == y:
			return True

	return False


def player_move_or_attack(dx, dy):
	global fov_recompute

	# direction player is moving or attacking
	x = player.x + dx
	y = player.y + dy

	# look for attackable object
	target = None
	for obj in objects:
		if obj.fighter and obj.x == x and obj.y == y:
			target = obj
			break

	# attack if target found, move otherwise
	if target is not None:
		player.fighter.attack(target)
	else:
		player.move(dx, dy)
		fov_recompute = True


def player_death(player):
	# Game Over!
	global game_state

	print 'You died!'
	game_state = 'dead'

	player.char = '%'
	player.color = libtcod.dark_red


def monster_death(monster):
	# gets transformed into a corpse
	print monster.name.capitalize() + ' is dead!'
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name

	monster.send_to_back()


########################################################
# Window setup and main game loop
########################################################

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'ARTIFICE', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# create player object
fighter_component = Fighter(hp=30, defense=2, power=5, death_function=player_death)
player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component, speed=PLAYER_SPEED)

objects = [player]

make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

fov_recompute = True

game_state = 'playing'
player_action = None

while not libtcod.console_is_window_closed():

	render_all()

	libtcod.console_flush()

	# clear objects at their previous location
	for object in objects:
		object.clear()

	# handle keys and exit game if esc is pressed
	player_action = handle_keys()
	if player_action == 'exit':
		break

	# let monsters take their turn
	if game_state == 'playing':
		for obj in objects:
			if obj.ai:
				if obj.wait > 0: # still waiting, don't take turn
					obj.wait -= 1
				else:
					obj.ai.take_turn()
