import sys
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import pygame.gfxdraw
import math
import warnings

# Position the window and suppress warnings
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Catan Board (Zoom & Pan)")

# Font for labels
base_font_size = 18
font = pygame.font.SysFont(None, base_font_size)

# Color map for Catan resources
COLOR_MAP = {
    "sheep":  (200, 255, 200),
    "wheat":  (255, 240, 150),
    "clay":   (205, 92,  92),
    "wood":   (139, 69,  19),
    "rock":   (160, 160, 160),
    "desert": (238, 214, 175),
}

# Initial view transform
zoom = 1.0
offset_x, offset_y = 0.0, 0.0

# Panning state
panning = False
pan_start_mouse = (0, 0)
pan_start_offset = (0, 0)

def world_to_screen(wx, wy):
    """Convert world coords → screen coords."""
    sx = wx * zoom + offset_x + width / 2
    sy = wy * zoom + offset_y + height / 2
    return sx, sy

def hexagon_vertices(x, y, size):
    """Return 6 world-space points for a hexagon centered at (x,y)."""
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((
            x + size * math.cos(angle),
            y + size * math.sin(angle)
        ))
    return pts

def draw_hexagon(tile_type, x, y, size):
    """Draw one hex at world coords (x,y)."""
    color = COLOR_MAP.get(tile_type, (100,100,100))
    border = (0,0,0)
    # Compute world verts and map to screen
    wpts = hexagon_vertices(x, y, size)
    spts = [world_to_screen(wx, wy) for wx, wy in wpts]

    # Draw filled + antialiased outline
    pygame.gfxdraw.filled_polygon(screen, spts, color)
    pygame.gfxdraw.aapolygon(screen, spts, border)

    # Draw label (not scaled)
    label = font.render(tile_type.capitalize(), True, border)
    lw, lh = label.get_size()
    sx, sy = world_to_screen(x, y)
    screen.blit(label, (sx - lw/2, sy - lh/2))


def board_positions(size):
    """Return list of (wx,wy) for the 3-4-5-4-3 layout."""
    positions = []
    v_dist = size * 1.5
    h_dist = size * math.sqrt(3)
    row_counts = [3,4,5,4,3]
    # center the grid around (0,0)
    y_start = -v_dist * 2
    for row_idx, count in enumerate(row_counts):
        wy = y_start + row_idx * v_dist
        total_w = (count - 1) * h_dist
        x_start = - total_w / 2
        for i in range(count):
            wx = x_start + i * h_dist
            positions.append((wx, wy))
    return positions

# Define your tile order
resource_sequence = [
    "wood","wood","wood","wood",
    "sheep","sheep","sheep","sheep",
    "wheat","wheat","wheat","wheat",
    "clay","clay","clay",
    "rock","rock","rock",
    "desert"
]
world_centers = board_positions(50)
tiles = list(zip(resource_sequence, world_centers))

# Main loop
running = True
while running:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

        # Mouse-wheel zoom
        elif ev.type == pygame.MOUSEWHEEL:
            # Zoom about cursor
            mx, my = pygame.mouse.get_pos()
            # convert to world coords
            wx = (mx - width/2 - offset_x) / zoom
            wy = (my - height/2 - offset_y) / zoom
            # adjust zoom
            factor = 1.1 if ev.y > 0 else 1/1.1
            zoom *= factor
            # re-center so world point under cursor stays put
            offset_x = mx - width/2 - wx * zoom
            offset_y = my - height/2 - wy * zoom

        # Start panning
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            panning = True
            pan_start_mouse = ev.pos
            pan_start_offset = (offset_x, offset_y)

        # End panning
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            panning = False

        # Middle click = reset view
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 2:
            zoom = 1.0
            offset_x, offset_y = 0.0, 0.0

        # Handle drag
        elif ev.type == pygame.MOUSEMOTION and panning:
            dx = ev.pos[0] - pan_start_mouse[0]
            dy = ev.pos[1] - pan_start_mouse[1]
            offset_x = pan_start_offset[0] + dx
            offset_y = pan_start_offset[1] + dy

        # Escape quits
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            running = False

    screen.fill((30, 30, 30))

    # Draw all tiles
    for tile_type, (wx, wy) in tiles:
        draw_hexagon(tile_type, wx, wy, 50)

    pygame.display.flip()

pygame.quit()
sys.exit()
