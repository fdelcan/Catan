# Displayer.py
import sys, os, math, random
import pygame, pygame.gfxdraw

# ─── Configuration constants ─────────────────────────────────────────────────
BASE_SIZE          = 70     # base hexagon size in world units
HOUSE_SIZE_FACTOR  = 1/8    # house size = BASE_SIZE * this * scale
ROAD_WIDTH_FACTOR  = 0.15   # road width = BASE_SIZE * this * scale
NODE_RADIUS_FACTOR = 0.10   # node radius factor

# Mapping resource codes to names for display colors
RESOURCE_NAMES = {
    0: "desert",
    1: "rock",
    2: "wood",
    3: "sheep",
    4: "wheat",
    5: "clay",
}
RESOURCE_COLORS = {
    "sheep":  (200,255,200),
    "wheat":  (255,240,150),
    "clay":   (220, 92, 92),
    "wood":   (139, 69, 19),
    "rock":   (160,160,160),
    "desert": (238,214,175),
}
PLAYER_COLORS = ["red","blue","green","orange"]

# ─── Pan & Zoom state ─────────────────────────────────────────────────────────
pan_x = 0.0
pan_y = 0.0
scale = 1.0
default_scale = 1.0

# ─── Pygame initialization ────────────────────────────────────────────────────
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
pygame.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Catan")
font = pygame.font.SysFont("Arial", 20)

# ─── Helper transforms ─────────────────────────────────────────────────────────
def world_to_screen(x, y):
    """Convert world coords to screen coords, applying pan & zoom."""
    sx = WIDTH/2  + (x + pan_x) * scale
    sy = HEIGHT/2 + (y + pan_y) * scale
    return int(sx), int(sy)

# Precompute board tile centers in world coords
def board_positions():
    rows = [3,4,5,4,3]
    v = BASE_SIZE * 1.5
    h = BASE_SIZE * math.sqrt(3)
    y0 = -2 * v
    pts = []
    for r, cnt in enumerate(rows):
        y = y0 + r * v
        x0 = -h * (cnt - 1) / 2
        for i in range(cnt):
            pts.append((x0 + i * h, y))
    return pts

# Generate hexagon vertices in world coords
def hexagon_vertices(cx, cy):
    size = BASE_SIZE * 0.95
    return [
        (cx + size * math.cos(math.radians(60*i - 30)),
         cy + size * math.sin(math.radians(60*i - 30)))
        for i in range(6)
    ]

# ─── Drawing primitives ───────────────────────────────────────────────────────
def draw_hex(res_num, center, highlight=False):
    res, num = res_num
    name = RESOURCE_NAMES.get(res, "desert")
    col  = RESOURCE_COLORS[name]
    verts = hexagon_vertices(*center)
    pts = [world_to_screen(x, y) for x, y in verts]
    pygame.gfxdraw.filled_polygon(screen, pts, col)
    pygame.gfxdraw.aapolygon(screen, pts, (0,0,0))
    if num:
        txt = font.render(str(num), True, (255,0,0) if highlight else (0,0,0))
        sx, sy = world_to_screen(*center)
        screen.blit(txt, (sx - txt.get_width()/2,
                          sy - txt.get_height()/2))


def draw_settlement(node_pos, level, color):
    sx, sy = world_to_screen(*node_pos)
    sz = int(BASE_SIZE * HOUSE_SIZE_FACTOR * scale)
    pygame.draw.rect(screen,
                     pygame.Color(color),
                     (sx-sz, sy-sz, 2*sz, 2*sz))
    if level==2:
        pygame.draw.circle(screen,
                           (255,255,0),
                           (sx,sy),
                           sz//2)


def draw_road(edge_pts, color):
    width = max(1, int(BASE_SIZE * ROAD_WIDTH_FACTOR * scale))
    p1 = world_to_screen(*edge_pts[0])
    p2 = world_to_screen(*edge_pts[1])
    pygame.draw.line(screen,
                     pygame.Color(color),
                     p1, p2,
                     width)


def draw_robber(center):
    sx, sy = world_to_screen(*center)
    diameter = int(BASE_SIZE * scale)
    surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    pygame.draw.circle(surf,
                       (0,0,0,90),
                       (diameter//3, diameter//3),
                       diameter//3)
    screen.blit(surf, (sx-diameter//3, sy-diameter//3))


def draw_ui(game):
    # Turn indicator
    col = PLAYER_COLORS[game.current_player]
    txt = font.render(f"Turn: {col}", True, (255,255,255))
    screen.blit(txt, (10,10))
    # Resource counts
    x, y = 10, HEIGHT - 40
    for rcode in range(6):
        name = RESOURCE_NAMES.get(rcode, "desert")
        bgcol = RESOURCE_COLORS[name]
        cnt = game.cards[game.current_player, rcode]
        lbl = font.render(str(cnt), True, (0,0,0))
        w, h = lbl.get_width()+6, lbl.get_height()+4
        bg = pygame.Surface((w,h))
        bg.fill(bgcol)
        screen.blit(bg, (x,y))
        screen.blit(lbl, (x+3, y+2))
        x += w + 6

# ─── Frame drawing ────────────────────────────────────────────────────────────
def draw_frame(game):
    screen.fill((30,30,30))
    centers = board_positions()
    # map node coords
    rc_to_coord = {}
    for tid, center in enumerate(centers):
        verts = hexagon_vertices(*center)
        for i, rc in enumerate(game.tile_to_nodes[tid]):
            rc_to_coord[tuple(rc)] = verts[i]
    # highlight dice
    dice_total = sum(game.dice_result) if getattr(game, 'dice_result', None) else None
    # tiles
    for tid, pair in enumerate(game.tiles):
        draw_hex(pair, centers[tid], highlight=(pair[1]==dice_total))
    # roads
    for (rc1, rc2), col in game.edges.items():
        p1 = rc_to_coord[tuple(rc1)]; p2 = rc_to_coord[tuple(rc2)]
        draw_road((p1,p2), PLAYER_COLORS[col-1])
    # settlements
    for r, row in enumerate(game.nodes):
        for c, (pl, lvl) in enumerate(row):
            if pl>0:
                draw_settlement(rc_to_coord[(r,c)], lvl, PLAYER_COLORS[pl-1])
    # robber
    rob = game.robber
    rows = [3,4,5,4,3]
    if isinstance(rob, tuple): flat = sum(rows[:rob[0]]) + rob[1]
    else: flat = rob
    center = centers[int(flat)]
    draw_robber(center)
    # UI
    draw_ui(game)
    pygame.display.flip()

# ─── Public display function ──────────────────────────────────────────────────
def display(game):
    """
    Opens a window and lets you pan/zoom the Catan board interactively.
    Call this once with your GameState; it will run until you close the window.
    """
    global pan_x, pan_y, scale
    dragging = False
    last_mouse = (0,0)
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    dragging = True; last_mouse = ev.pos
                elif ev.button == 2:
                    pan_x = pan_y = 0.0; scale = default_scale
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    dragging = False
            elif ev.type == pygame.MOUSEMOTION:
                if dragging:
                    dx = ev.pos[0] - last_mouse[0]
                    dy = ev.pos[1] - last_mouse[1]
                    pan_x += dx / scale
                    pan_y += dy / scale
                    last_mouse = ev.pos
            elif ev.type == pygame.MOUSEWHEEL:
                factor = 1.1 ** ev.y
                scale *= factor
        draw_frame(game)
        clock.tick(60)
