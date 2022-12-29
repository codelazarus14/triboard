from vpython import *

ROWS = 8
PLAYER_SIZE = 0.4
PLAYER_COLORS = [color.red, color.magenta, color.orange]
BOARD_COLOR = color.blue
SPACE_COLOR = color.green


# -- Math Helpers --

def tri_height(length):
    return sqrt(pow(length, 2) - pow(length / 2, 2))


def radians(deg):
    return deg * pi / 180


# small camera fixes
scene.width = 700
scene.height = 700
scene.camera.pos = vec(0, ROWS - tri_height(ROWS / 2), -30)
scene.fov = pi / 15

# height of each triangle, != 1
h1 = tri_height(1)

# map [x][y] to board pos
# in C# should be a dict of tuples to vectors - glowscript won't let me
spaces: list[list[vector]] = [[None for i in range(ROWS * 2)] for j in range(ROWS)]
# another glowscript limitation - mirrored array of cylinder references
cylinders: list[list[cylinder]] = [[None for h in range(ROWS * 2)] for k in range(ROWS)]
# add our players to this to keep track of them
# stored as vpython obj, coord position
players = []
# spaces being targeted by the queen every turn
qb_spaces = []
qb_lines = []


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
# place players
p1_space = (0, 0)
p1 = arrow(pos=spaces[p1_space[0]][p1_space[1]], axis=vec(0, PLAYER_SIZE, 0),
           color=PLAYER_COLORS[0], make_trail=True, trail_radius=PLAYER_SIZE / 20,
           retain=5, pickable=False)
players.append((p1, p1_space))

p2_space = (0, 14)
p2 = arrow(pos=spaces[p2_space[0]][p2_space[1]], axis=vec(0, PLAYER_SIZE, 0),
           color=PLAYER_COLORS[1], make_trail=True, trail_radius=PLAYER_SIZE / 20,
           retain=5, pickable=False)
players.append((p2, p2_space))

queen_space = (4, 6)
queen = box(pos=spaces[queen_space[0]][queen_space[1]], axis=vec(0, 0, PLAYER_SIZE),
            height=PLAYER_SIZE / 3, width=PLAYER_SIZE / 3, up=vec(1, 1, 0), color=PLAYER_COLORS[2],
            make_trail=True, trail_radius=PLAYER_SIZE / 20, retain=5, pickable=False)
players.append((queen, queen_space))

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
def mouse_to_space(piece, piece_space):
    obj = scene.mouse.pick
    # only allow cylinders to be selected
    if obj is not None and isinstance(obj, cylinder):
        if obj.pos.x == piece.pos.x and obj.pos.y == piece.pos.y:
            return piece_space
        else:
            return clicked_to_space(obj.pos)
    else:
        return None


# top-level mouse event handler for selecting pieces
def click_piece(piece, piece_space):
    m_pos = mouse_to_space(piece, piece_space)
    print(m_pos)
    # matches player? we're good
    if m_pos == piece_space:
        light_purple = vec(0.6, 0.4, 0.8)
        cyl = cylinders[piece_space[0]][piece_space[1]]
        cyl.color = light_purple
        return adj_spaces(piece_space[0], piece_space[1])
    # else, wait for next attempt
    print(f"Error selecting piece {piece}")
    return None


# top-level mouse event handler for moving pieces
def click_space(piece, piece_space):
    m_pos = mouse_to_space(piece, piece_space)
    # we clicked something and it's not a player?
    if m_pos is not None and m_pos != piece_space:
        # check highlighted spaces for match
        for h in highlighted_spaces:
            if h[1] == m_pos:
                # reset colors
                cylinders[piece_space[0]][piece_space[1]].color = color.green
                for c in highlighted_spaces:
                    c[0].color = color.green
                highlighted_spaces.clear()

                return move_to_space(piece, piece_space, m_pos)

    # not one of our highlighted spaces
    print(f"Error moving piece {piece}")
    return None


# -- Game Logic --

# map [x][y] to B/W space
# even,even or odd,odd = W (ie: [0][2]), else B
def is_white(x, y):
    return (x + y) % 2 == 0


# helper for checking board boundaries
def check_bounds(x, y):
    if 0 <= x < ROWS and x <= y <= 2 * ROWS - (x + 2):
        return x, y
    return None


def adj_spaces(x, y):
    adj = []
    # add left space
    left = check_bounds(x, y - 1)
    if left is not None:
        adj.append(left)
    # add right space
    right = check_bounds(x, y + 1)
    if right is not None:
        adj.append(right)
    # add up/down space depending on B/W
    if is_white(x, y):
        up_down = check_bounds(x - 1, y)
    else:
        up_down = check_bounds(x + 1, y)
    if up_down is not None:
        adj.append(up_down)

    # filter out occupied
    for p in players:
        for pos in adj:
            if pos == p[1] and p[2]:
                adj.remove(pos)
    # adj = [pos for pos in adj if pos not in players]
    print(f"adj: {adj}")
    return adj


def move_to_space(piece, piece_space, dst):
    v_diff = spaces[dst[0]][dst[1]] - spaces[piece_space[0]][piece_space[1]]
    # move and rotate player
    piece.pos = spaces[dst[0]][dst[1]]
    # queen's piece should keep facing up
    if isinstance(piece, arrow):
        piece.axis = norm(v_diff) * PLAYER_SIZE
    return dst


def update_queen_beam(piece_space):
    qb_new_spaces = []
    # shorter var names
    x, y = piece_space[0], piece_space[1]
    white = is_white(x, y)

    # find all spaces within LOS (points of center triangle)
    for i in range(1, ROWS):
        if white:
            # check for new spaces in 3 directions from center
            new_spaces = [
                # above
                check_bounds(x + i, y),
                # lower R diagonal
                check_bounds(x - i, y + 3 * i - 1),
                check_bounds(x - i, y + 3 * i),
                # lower L diagonal
                check_bounds(x - i, y - 3 * i + 1),
                check_bounds(x - i, y - 3 * i)
            ]
            # remove out-of-bounds spaces
            new_spaces = [n for n in new_spaces if n is not None]
            qb_new_spaces += new_spaces
        else:
            new_spaces = [
                # below
                check_bounds(x - i, y),
                # upper R diagonal
                check_bounds(x + i, y + 3 * i - 1),
                check_bounds(x + i, y + 3 * i),
                # upper L diagonal
                check_bounds(x + i, y - 3 * i + 1),
                check_bounds(x + i, y - 3 * i)
            ]
            new_spaces = [n for n in new_spaces if n is not None]
            qb_new_spaces += new_spaces

    # remove old lines/spaces
    for j in range(len(qb_spaces)):
        qb_lines[j].visible = False
    qb_spaces.clear()
    qb_lines.clear()
    # draw new lines
    for q in qb_new_spaces:
        print(f"attackable position at: {q}")
        qb_spaces.append(q)
        # this does generate lines on top of each other
        # - ideally should store the farthest pos in a variable
        qb_lines.append(curve(spaces[x][y], spaces[q[0]][q[1]]))
    return


def check_queen_beam():
    for p in players:
        if p[1] in qb_spaces and p[0].visible:
            p[0].visible = False
            print(f"{p[0]} hit by beam at {p[1]}!")
    return


def player_turn(p, p_space):
    adj = None
    # wait for player to pick starting piece
    piece_selected = False
    print(f"player {p} space = {p_space}")
    cyl = cylinders[p_space[0]][p_space[1]]
    cyl.color = color.purple
    while not piece_selected:
        scene.pause('click the player\'s space')
        adj = click_piece(p, p_space)
        if adj is not None:
            piece_selected = True

    # highlight adjacent
    for c_pos in adj:
        c: cylinder = cylinders[c_pos[0]][c_pos[1]]
        c.color = color.yellow
        highlighted_spaces.append((c, c_pos))

    # wait for them to click valid space
    space_selected = False
    while not space_selected:
        scene.pause('click the dest space')
        move = click_space(p, p_space)
        if move is not None:
            p_space = move
            space_selected = True

    # queen updates beam
    if isinstance(p, box):
        update_queen_beam(p_space)
    # every piece checks to see if beam made contact
    print("turn over")
    return p, p_space


t_count = 0
playing = True
# activate on start
update_queen_beam(players[2][1])
while playing:
    t_count += 1
    scene.caption = f"Turn {t_count}"
    for i in range(len(players)):
        plyr = players[i]
        # ignore if invisible - removed from board
        if plyr[0].visible:
            players[i] = player_turn(plyr[0], plyr[1])
            check_queen_beam()
            # check if <2 players remain
            p_count = 0
            for pl in players:
                if pl[0].visible:
                    p_count += 1
            if p_count < 2:
                scene.caption = "Game over!"
                playing = False
                break
