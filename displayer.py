import sys
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import pygame.gfxdraw
import math
import warnings
import random as rd

# Constants
SIZE = 70
HOUSE_SIZE = SIZE // 8
ROAD_LENGTH = SIZE * 0.55
ROAD_WIDTH = SIZE * 0.15
NODE_RADIUS = SIZE * 0.10
NODE_DETECTION_RADIUS = NODE_RADIUS * 1.1
ROAD_DELAY = 0.2

# Environment setup
last_build_time = 0
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Catan Board")
font = pygame.font.SysFont(None, 24)

# Colors and player info
COLOR_MAP = {
    "sheep":  (200, 255, 200),
    "wheat":  (255, 240, 150),
    "clay":   (205, 92,  92),
    "wood":   (139, 69,  19),
    "rock":   (160, 160, 160),
    "desert": (238, 214, 175),
}
players = ["red", "blue", "green", "orange"]
player_colors = {
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "orange": (255, 165, 0),
}

# Game state
zoom = 1.0
offset_x, offset_y = 0.0, 0.0
panning = False
pan_start_mouse = (0, 0)
pan_start_offset = (0, 0)
current_player = 0
villages = []
roads = []

# Utility functions
def world_to_screen(wx, wy):
    return wx * zoom + offset_x + width / 2, wy * zoom + offset_y + height / 2

def screen_to_world(sx, sy):
    return (sx - width / 2 - offset_x) / zoom, (sy - height / 2 - offset_y) / zoom

def hexagon_vertices(x, y, size):
    return [(x + size * math.cos(math.radians(60*i - 30)),
             y + size * math.sin(math.radians(60*i - 30))) for i in range(6)]

def draw_hexagon(tile_type, x, y, size):
    color = COLOR_MAP.get(tile_type, (100, 100, 100))
    pts = hexagon_vertices(x, y, size)
    spts = [world_to_screen(px, py) for px, py in pts]
    pygame.gfxdraw.filled_polygon(screen, spts, color)
    pygame.gfxdraw.aapolygon(screen, spts, (0, 0, 0))
    label = font.render(tile_type, True, (0, 0, 0))
    lw, lh = label.get_size()
    sx, sy = world_to_screen(x, y)
    screen.blit(label, (sx - lw/2, sy - lh/2))

def draw_village(vx, vy, color, level):
    sx, sy = world_to_screen(vx, vy)
    size = HOUSE_SIZE * zoom
    pygame.draw.rect(screen, player_colors[color], pygame.Rect(sx - size, sy - size, 2*size, 2*size))
    if level == 2:
        pygame.draw.circle(screen, (255, 255, 0), (int(sx), int(sy)), int(3 * zoom))

def draw_road(p1, p2, color):
    x1, y1 = world_to_screen(*p1)
    x2, y2 = world_to_screen(*p2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    angle = math.atan2(y2 - y1, x2 - x1)
    length = math.hypot(x2 - x1, y2 - y1) * 0.65
    rect = pygame.Surface((length, ROAD_WIDTH * zoom), pygame.SRCALPHA).convert_alpha()
    rect.fill(player_colors[color])
    rot = pygame.transform.rotate(rect, -math.degrees(angle))
    screen.blit(rot, rot.get_rect(center=(mx, my)))

def board_positions(size):
    pos = []
    v_dist = size * 1.5
    h_dist = size * math.sqrt(3)
    row_counts = [3, 4, 5, 4, 3]
    y_start = -v_dist * 2
    for row_idx, count in enumerate(row_counts):
        wy = y_start + row_idx * v_dist
        x_start = -((count - 1) * h_dist) / 2
        for i in range(count):
            wx = x_start + i * h_dist
            pos.append((wx, wy))
    return pos

def draw_road_detection(p1, p2):
    x1, y1 = world_to_screen(*p1)
    x2, y2 = world_to_screen(*p2)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    angle = math.atan2(y2 - y1, x2 - x1)
    ellipse = pygame.Surface((ROAD_LENGTH * zoom, ROAD_WIDTH * zoom), pygame.SRCALPHA).convert_alpha()
    pygame.draw.ellipse(ellipse, (180, 180, 180, 100), ellipse.get_rect())
    ellipse_rotated = pygame.transform.rotate(ellipse, -math.degrees(angle))
    screen.blit(ellipse_rotated, ellipse_rotated.get_rect(center=(mx, my)))

def find_nearest_edge(wx, wy, threshold=ROAD_LENGTH * 0.6):
    for tx, ty in centers:
        pts = hexagon_vertices(tx, ty, SIZE)
        for i in range(6):
            v1, v2 = pts[i], pts[(i + 1) % 6]
            mx, my = (v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2
            if (wx - mx)**2 + (wy - my)**2 < threshold**2:
                return v1, v2
    return None, None

def random_start():
    resources = ["wood"]*4 + ["sheep"]*4 + ["wheat"]*4 + ["clay"]*3 + ["rock"]*3 + ["desert"]
    rd.shuffle(resources)
    return resources

def draw_ui():
    pygame.draw.rect(screen, (100, 100, 100), (10, 10, 220, 30))
    text = font.render(f"Player's turn: {players[current_player]}", True, (255,255,255))
    screen.blit(text, (15, 15))

def main():
    global zoom, offset_x, offset_y, panning, pan_start_mouse, pan_start_offset, current_player, last_build_time

    resource_sequence = random_start()
    global centers
    centers = board_positions(SIZE)
    tiles = list(zip(resource_sequence, centers))

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000
        last_build_time += dt

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                running = False
            elif ev.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                wx, wy = screen_to_world(mx, my)
                factor = 1.1 if ev.y > 0 else 1 / 1.1
                zoom *= factor
                offset_x = mx - width / 2 - wx * zoom
                offset_y = my - height / 2 - wy * zoom
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    panning = True
                    pan_start_mouse = ev.pos
                    pan_start_offset = (offset_x, offset_y)
                elif ev.button == 3 and last_build_time > ROAD_DELAY:
                    mx, my = ev.pos
                    wx, wy = screen_to_world(mx, my)
                    for tx, ty in centers:
                        for vx, vy in hexagon_vertices(tx, ty, SIZE):
                            if (wx - vx)**2 + (wy - vy)**2 < NODE_DETECTION_RADIUS**2:
                                for v in villages:
                                    if (vx, vy) == (v[0], v[1]):
                                        if v[2] == players[current_player] and v[3] == 1:
                                            villages.remove(v)
                                            villages.append((vx, vy, v[2], 2))
                                        break
                                else:
                                    villages.append((vx, vy, players[current_player], 1))
                                    last_build_time = 0
                    v1, v2 = find_nearest_edge(wx, wy)
                    if v1 and v2 and not any((v1, v2) == (r[0], r[1]) or (v2, v1) == (r[0], r[1]) for r in roads):
                        roads.append((v1, v2, players[current_player]))
                        last_build_time = 0
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                panning = False
            elif ev.type == pygame.MOUSEMOTION and panning:
                dx, dy = ev.pos[0] - pan_start_mouse[0], ev.pos[1] - pan_start_mouse[1]
                offset_x = pan_start_offset[0] + dx
                offset_y = pan_start_offset[1] + dy
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    current_player = (current_player - 1) % len(players)
                elif ev.key == pygame.K_RIGHT:
                    current_player = (current_player + 1) % len(players)

        screen.fill((30, 30, 30))
        for tile, (wx, wy) in tiles:
            draw_hexagon(tile, wx, wy, SIZE * 0.95)

        mx, my = pygame.mouse.get_pos()
        wx, wy = screen_to_world(mx, my)

        for tx, ty in centers:
            for vx, vy in hexagon_vertices(tx, ty, SIZE):
                if (wx - vx)**2 + (wy - vy)**2 < NODE_DETECTION_RADIUS**2:
                    sx, sy = world_to_screen(vx, vy)
                    pygame.draw.circle(screen, (180, 180, 180), (int(sx), int(sy)), int(NODE_RADIUS * zoom))

        v1, v2 = find_nearest_edge(wx, wy)
        if v1 and v2:
            draw_road_detection(v1, v2)

        for vx, vy, color, level in villages:
            draw_village(vx, vy, color, level)

        for r1, r2, color in roads:
            draw_road(r1, r2, color)

        draw_ui()
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
