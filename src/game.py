import libtcodpy as libtcod

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

MAP_WIDTH = 80
MAP_HEIGHT = 45

color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)



class Object:
	# Generic object used for various game features
	# always represented by a character in console
	def __init__(self, x, y, char, color):
		self.x = x
		self.y = y
		self.char = char
		self.color = color

	def move(self, dx, dy):
		# move object by (dx, dy) unless blocked
		if not map[self.x + dx][self.y + dy].blocked:
			self.x += dx
			self.y += dy

	def draw(self):
		# set object color and draw the appropriate
		# character at the appropriate location
		libtcod.console_set_default_foreground(con, self.color)
		libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def clear(self):
		# clear the object's character from console
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)


class Tile:
	# A map tile and its properties
	def __init__(self, blocked, block_sight = None):
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


def handle_keys():
	global playerx, playery

	key = libtcod.console_check_for_keypress()
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		# Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

	elif key.vk == libtcod.KEY_ESCAPE:
		return True		# exit game

	#movement keys
	if libtcod.console_is_key_pressed(libtcod.KEY_UP):
		player.move(0, -1)

	elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
		player.move(0, 1)

	elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
		player.move(-1, 0)

	elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
		player.move(1, 0)


def make_map():
	global map

	# fill map with blocked tiles
	map = [[ Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	# create two rooms
	room1 = Rect(20, 15, 10, 15)
	room2 = Rect(50, 15, 10, 15)
	create_room(room1)
	create_room(room2)

	create_h_tunnel(25, 55, 23)


def render_all():
	# draw all objects in object list
	for object in objects:
		object.draw()

	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			wall = map[x][y].block_sight
			if wall:
				libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
			else:
				libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)

	# blit contents of "con" to the root console
	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)


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


########################################################
# Window setup and main game loop
########################################################

libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'ARTIFICE', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)
npc	   = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow)
objects = [npc, player]

make_map()
player.x = 25
player.y = 23

while not libtcod.console_is_window_closed():

	render_all()

	libtcod.console_flush()

	# clear objects at their previous location
	for object in objects:
		object.clear()

	# handle keys and exit game if esc is pressed
	exit = handle_keys()
	if exit:
		break
