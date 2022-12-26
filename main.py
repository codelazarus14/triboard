from vpython import *

ROWS = 8
PLAYER_SIZE = 0.4
PLAYER_COLOR = color.red
BOARD_COLOR = color.blue
SPACE_COLOR = color.green


# -- Math Helpers --

def tri_height(length):
    return sqrt(pow(length, 2) - pow(length / 2, 2))


def radians(deg):
    return deg * pi / 180


# small camera fixes
scene.width = 600
scene.height = 600
scene.camera.pos = vec(0, ROWS - tri_height(ROWS / 2), -30)
scene.fov = pi / 15

# height of each triangle, != 1
h1 = tri_height(1)

# map [x][y] to board pos
# in C# should be a dict of tuples to vectors - glowscript won't let me
spaces: list[list[vector]] = [[None for i in range(ROWS * 2)] for j in range(ROWS)]

# another glowscript limitation - mirrored array of cylinder references
cylinders: list[list[cylinder]] = [[None for h in range(ROWS * 2)] for k in range(ROWS)]


def make_board():
    for i in range(ROWS, 0, -1):
        idx = ROWS - i
        msg = f"row {ROWS - i} (i={i}): "
        offset = -i / 2
        for j in range(i):
            a = vertex(pos=vec(j + offset, ROWS - h1 * i, 0))
            b = vertex(pos=vec(j + offset + 0.5, ROWS - h1 * (i - 1), 0))
            c = vertex(pos=vec(j + offset + 1, ROWS - h1 * i, 0))
            triangle(vs=[a, b, c])
            # add white space to map (average 3 vertices)
            w_center = (a.pos + b.pos + c.pos) / 3
            cyl = cylinder(pos=w_center, axis=vec(0, 0, PLAYER_SIZE / 2),
                           radius=PLAYER_SIZE / 2, color=SPACE_COLOR)
            spaces[ROWS - i][idx] = cyl.pos + vec(0, 0, PLAYER_SIZE)
            cylinders[ROWS - i][idx] = cyl
            msg += f"W({ROWS - i},{idx}) "
            # add black space to map up to 1 space away from end
            if j < i - 1:
                b_center = (b.pos + c.pos + vec(b.pos.x + 1, b.pos.y, 0)) / 3
                cyl = cylinder(pos=b_center, axis=vec(0, 0, PLAYER_SIZE / 2),
                               radius=PLAYER_SIZE / 2, color=SPACE_COLOR)
                spaces[ROWS - i][idx + 1] = cyl.pos + vec(0, 0, PLAYER_SIZE)
                cylinders[ROWS - i][idx + 1] = cyl
                msg += f"B({ROWS - i},{idx + 1}) "
            idx += 2
        print(msg)
    # add contrast color behind triangles - B triangles
    v1 = vertex(pos=vec(-(ROWS / 2), ROWS - ROWS * h1, -.001), color=BOARD_COLOR)
    v2 = vertex(pos=vec(0, ROWS, -.001), color=BOARD_COLOR)
    v3 = vertex(pos=vec(ROWS / 2, ROWS - ROWS * h1, -.001), color=BOARD_COLOR)
    triangle(vs=[v1, v2, v3])


# create board
make_board()
# place player
player_space = (0, 0)
player = arrow(pos=spaces[player_space[0]][player_space[1]], axis=vec(0, PLAYER_SIZE, 0),
               color=PLAYER_COLOR, make_trail=True, trail_radius=PLAYER_SIZE / 20,
               retain=5, pickable=False)

# -- Input/Mouse Events --

highlighted_spaces: list[(cylinder, tuple[int, int])] = []


# map clicked object (cylinder) to [x,y] space
def clicked_to_space(clicked):
    n = len(spaces)
    for i in range(0, n):
        m = len(spaces[i])
        for j in range(0, m):
            if isinstance(spaces[i][j], vec) and spaces[i][j].x == clicked.x and spaces[i][j].y == clicked.y:
                return i, j
    print(f"couldn't find pos {clicked} in spaces!")
    return


# map mouse position to clicked space
def mouse_to_space():
    obj = scene.mouse.pick
    # only allow cylinders to be selected
    if obj is not None and isinstance(obj, cylinder):
        if obj.pos.x == player.pos.x and obj.pos.y == player.pos.y:
            return player_space
        else:
            return clicked_to_space(obj.pos)
    else:
        return None


# top-level mouse event handler for selecting pieces
def click_piece():
    m_pos = mouse_to_space()
    print(m_pos)
    # matches player? we're good
    if m_pos == player_space:
        cyl = cylinders[player_space[0]][player_space[1]]
        cyl.color = color.purple
        return adj_spaces(player_space[0], player_space[1])
    # else, wait for next attempt
    print("Error selecting player")
    return None


# top-level mouse event handler for moving pieces
def click_space():
    m_pos = mouse_to_space()
    # we clicked something and it's not a player?
    if m_pos is not None and m_pos != player_space:
        # check highlighted spaces for match
        for h in highlighted_spaces:
            if h[1] == m_pos:
                # reset colors
                cylinders[player_space[0]][player_space[1]].color = color.green
                for c in highlighted_spaces:
                    c[0].color = color.green
                highlighted_spaces.clear()

                move_to_space(player, m_pos)
                return m_pos

    # not one of our highlighted spaces
    print("Error moving player")
    return None


# -- Game Logic --

# map [x][y] to B/W space
# even,even or odd,odd = W (ie: [0][2]), else B
def is_white(x, y):
    return (x + y) % 2 == 0


def adj_spaces(x, y):
    adj = []
    # add left space
    # ignore if on left side
    if y > x:
        adj.append((x, y - 1))
    # add right space
    # ignore if on right side
    if y < 2 * ROWS - (x + 2):
        adj.append((x, y + 1))
    # add up/down space
    if is_white(x, y):
        if x > 0:
            adj.append((x - 1, y))
    elif x < ROWS - 1:
        adj.append((x + 1, y))

    # (later) blocked by other pieces
    print(f"adj: {adj}")
    return adj


def move_to_space(piece, dest):
    global player_space

    v_diff = spaces[dest[0]][dest[1]] - spaces[player_space[0]][player_space[1]]
    # move and rotate player
    player_space = dest
    piece.pos = spaces[dest[0]][dest[1]]
    piece.axis = norm(v_diff) * PLAYER_SIZE
    return


def player_turn():
    adj = None
    # wait for player to pick starting piece
    piece_selected = False
    print(f"player space = {player_space}")
    while not piece_selected:
        scene.pause('click the player\'s space')
        adj = click_piece()
        if adj is not None:
            piece_selected = True

    # highlight adjacents
    for c_pos in adj:
        c: cylinder = cylinders[c_pos[0]][c_pos[1]]
        c.color = color.yellow
        highlighted_spaces.append((c, c_pos))

    # wait for them to click valid space
    space_selected = False
    while not space_selected:
        scene.pause('click the dest space')
        move = click_space()
        if move is not None:
            space_selected = True
    print("turn over")
    return


t_count = 0
while True:
    # run player moves forever for now
    scene.caption = f"Turn {t_count}"
    player_turn()
    t_count += 1
