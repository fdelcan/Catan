# Catan Board Game Simulator
import sys
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import pygame.gfxdraw
import math
import warnings
import random as rd
from collections import defaultdict

# Constants
SIZE = 70
HOUSE_SIZE = SIZE // 8
ROAD_LENGTH = SIZE * 0.55
ROAD_WIDTH = SIZE * 0.15
NODE_RADIUS = SIZE * 0.10
NODE_DETECTION_RADIUS = NODE_RADIUS * 1.1
BUTTON_WIDTH, BUTTON_HEIGHT = 120, 40
RESOURCE_TYPES = ["sheep", "wheat", "rock", "clay", "wood"]
COLOR_MAP = {
    "sheep": (200, 255, 200),
    "wheat": (255, 240, 150),
    "clay": (205, 92, 92),
    "wood": (139, 69, 19),
    "rock": (160, 160, 160),
    "desert": (238, 214, 175),
}

# Environment setup
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Catan Board")
font = pygame.font.SysFont("Arial", 24)
player_colors = {
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "orange": (255, 165, 0),
}

class Player:
    def __init__(self, color):
        self.color = color
        self.resources = defaultdict(int)
        self.villages = []  # (x, y, level)
        self.roads = []
        self.placed_settlement = False
        self.placed_road = False

    def add_resources(self, resources):
        for res, count in resources.items():
            self.resources[res] += count
            
    def remove_resources(self, resources):
        for res, count in resources.items():
            if self.resources[res] < count:
                return False
        for res, count in resources.items():
            self.resources[res] -= count
        return True

class GameState:
    def __init__(self, players):
        self.players = [Player(color) for color in players]
        self.current_player_idx = 0
        self.phase = "setup"
        self.setup_phase = "forward"
        self.dice_rolled = False
        self.tiles = []
        self.valid_nodes = []
        self.valid_edges = []
        self.initialize_board()
        self.dice_result = None

    @property
    def current_player(self):
        return self.players[self.current_player_idx]
    
    def initialize_board(self):
        resources = ["wood"]*4 + ["sheep"]*4 + ["wheat"]*4 + ["clay"]*3 + ["rock"]*3 + ["desert"]
        rd.shuffle(resources)
        
        numbers = [2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12]
        rd.shuffle(numbers)
        
        # Correct spiral order including all 19 tiles
        spiral_order = [0,1,2,7,12,17,18,13,8,3,4,9,14,16,15,10,5,6,11]
        centers = board_positions(SIZE)
        
        self.tiles = []
        number_idx = 0
        for idx in spiral_order:
            res = resources.pop()
            pos = centers[idx]
            if res == "desert":
                self.tiles.append((res, None, pos))
                numbers.insert(6, None)  # Insert desert at position 6
            else:
                self.tiles.append((res, numbers[number_idx], pos))
                number_idx += 1
        
        # Generate valid nodes and edges
        self.valid_nodes = []
        self.valid_edges = []
        for tile in self.tiles:
            x, y = tile[2]
            vertices = hexagon_vertices(x, y, SIZE)
            for vx, vy in vertices:
                if (vx, vy) not in self.valid_nodes:
                    self.valid_nodes.append((vx, vy))
            for i in range(6):
                v1 = vertices[i]
                v2 = vertices[(i+1)%6]
                edge = tuple(sorted([v1, v2]))
                if edge not in self.valid_edges:
                    self.valid_edges.append(edge)

    def next_player(self):
        if self.phase == "setup":
            if self.setup_phase == "forward":
                self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
                if self.current_player_idx == 0:
                    self.setup_phase = "reverse"
                    self.current_player_idx = len(self.players) - 1
            else:
                self.current_player_idx -= 1
                if self.current_player_idx < 0:
                    self.phase = "regular"
                    self.current_player_idx = 0
                    self.distribute_initial_resources()
            # Reset placement flags
            self.current_player.placed_settlement = False
            self.current_player.placed_road = False
        else:
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.dice_rolled = False

    def distribute_initial_resources(self):
        for player in self.players:
            for (x, y, _) in player.villages:
                adjacent_tiles = self.get_adjacent_tiles(x, y)
                for tile in adjacent_tiles:
                    res, num, _ = tile
                    if res != "desert":
                        player.add_resources({res: 1})

    def get_adjacent_tiles(self, x, y):
        adjacent = []
        for tile in self.tiles:
            tx, ty = tile[2]
            distance = math.hypot(tx - x, ty - y)
            if distance < SIZE * 1.1:
                adjacent.append(tile)
        return adjacent

# Helper functions
def world_to_screen(wx, wy):
    return wx * zoom + offset_x + width/2, wy * zoom + offset_y + height/2

def screen_to_world(sx, sy):
    return (sx - width/2 - offset_x)/zoom, (sy - height/2 - offset_y)/zoom

def hexagon_vertices(x, y, size):
    return [(x + size * math.cos(math.radians(60*i - 30)),
             y + size * math.sin(math.radians(60*i - 30))) for i in range(6)]

def draw_hexagon(tile_type, x, y, size, number=None):
    color = COLOR_MAP.get(tile_type, (100, 100, 100))
    pts = hexagon_vertices(x, y, size)
    spts = [world_to_screen(px, py) for px, py in pts]
    pygame.gfxdraw.filled_polygon(screen, spts, color)
    pygame.gfxdraw.aapolygon(screen, spts, (0, 0, 0))
    if number is not None:
        label = font.render(str(number), True, (0,0,0))
        sx, sy = world_to_screen(x, y)
        screen.blit(label, (sx - 10, sy - 10))

def draw_village(vx, vy, color, level):
    sx, sy = world_to_screen(vx, vy)
    size = HOUSE_SIZE * zoom
    pygame.draw.rect(screen, player_colors[color], 
                    (sx - size, sy - size, 2*size, 2*size))
    if level == 2:
        pygame.draw.circle(screen, (255,255,0), (int(sx), int(sy)), int(size/2))

def draw_road(p1, p2, color):
    x1, y1 = world_to_screen(*p1)
    x2, y2 = world_to_screen(*p2)
    mx, my = (x1 + x2)/2, (y1 + y2)/2
    angle = math.atan2(y2 - y1, x2 - x1)
    length = math.hypot(x2 - x1, y2 - y1) * 0.65
    road_surf = pygame.Surface((length, ROAD_WIDTH * zoom), pygame.SRCALPHA)
    road_surf.fill(player_colors[color])
    rotated = pygame.transform.rotate(road_surf, -math.degrees(angle))
    screen.blit(rotated, rotated.get_rect(center=(mx, my)))

def board_positions(size):
    pos = []
    v_dist = size * 1.5
    h_dist = size * math.sqrt(3)
    row_counts = [3,4,5,4,3]
    y_start = -v_dist * 2
    for row_idx, count in enumerate(row_counts):
        wy = y_start + row_idx * v_dist
        x_start = -((count-1)*h_dist)/2
        for i in range(count):
            wx = x_start + i * h_dist
            pos.append((wx, wy))
    return pos

def draw_ui(game):
    # Turn indicator
    pygame.draw.rect(screen, (100,100,100), (10, 10, 220, 30))
    text = font.render(f"Player's turn: {game.players[game.current_player_idx].color}", True, (255,255,255))
    screen.blit(text, (15, 15))
    
    # Resource panel
    player = game.current_player
    resources = f"Sheep: {player.resources['sheep']} | Wheat: {player.resources['wheat']} | "
    resources += f"Rock: {player.resources['rock']} | Clay: {player.resources['clay']} | Wood: {player.resources['wood']}"
    pygame.draw.rect(screen, (200,200,200), (10, height-60, width-20, 50))
    text = font.render(resources, True, (0,0,0))
    screen.blit(text, (20, height-50))

def handle_dice_roll(game):
    if game.phase != "regular":
        return
    dice = (rd.randint(1,6), rd.randint(1,6))
    total = sum(dice)
    game.dice_result = dice
    
    if total == 7:
        return  # Robber handling omitted
    
    for tile in game.tiles:
        res, num, (x,y) = tile
        if num == total and res != "desert":
            for player in game.players:
                for (vx, vy, level) in player.villages:
                    distance = math.hypot(vx - x, vy - y)
                    if distance < SIZE * 1.1:
                        player.add_resources({res: 2 if level == 2 else 1})

def main():
    global zoom, offset_x, offset_y
    zoom = 1.0
    offset_x, offset_y = 0.0, 0.0
    panning = False
    pan_start_mouse = (0, 0)
    pan_start_offset = (0, 0)
    
    game = GameState(["red", "blue", "green", "orange"])
    clock = pygame.time.Clock()
    
    # UI elements
    roll_btn = pygame.Rect(width-140, height-50, 120, 40)
    end_turn_btn = pygame.Rect(width-140, height-100, 120, 40)
    hover_node = None
    hover_edge = None
    
    while True:
        mx, my = pygame.mouse.get_pos()
        wx, wy = screen_to_world(mx, my)
        
        # Find hover targets
        hover_node = None
        min_dist = NODE_DETECTION_RADIUS
        for node in game.valid_nodes:
            dist = math.hypot(node[0]-wx, node[1]-wy)
            if dist < min_dist:
                hover_node = node
                min_dist = dist
                
        hover_edge = None
        min_edge_dist = ROAD_LENGTH*0.6
        for edge in game.valid_edges:
            p1, p2 = edge
            mx_edge = (p1[0]+p2[0])/2
            my_edge = (p1[1]+p2[1])/2
            dist = math.hypot(mx_edge-wx, my_edge-wy)
            if dist < min_edge_dist:
                hover_edge = edge
                min_edge_dist = dist

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            # Panning controls
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    panning = True
                    pan_start_mouse = event.pos
                    pan_start_offset = (offset_x, offset_y)
                    
                # Setup phase placements
                elif game.phase == "setup" and event.button in (1, 3):
                    current_player = game.current_player
                    
                    # Place settlement
                    if hover_node and not current_player.placed_settlement:
                        valid = True
                        # Check distance from other settlements
                        for p in game.players:
                            for (vx, vy, _) in p.villages:
                                if math.hypot(vx - hover_node[0], vy - hover_node[1]) < SIZE:
                                    valid = False
                                    break
                        if valid:
                            current_player.villages.append((hover_node[0], hover_node[1], 1))
                            current_player.placed_settlement = True
                            
                    # Place road
                    elif hover_edge and current_player.placed_settlement and not current_player.placed_road:
                        # Check road connects to settlement
                        road_valid = False
                        (vx, vy) = current_player.villages[-1][:2]
                        for point in hover_edge:
                            if math.hypot(vx - point[0], vy - point[1]) < SIZE*0.1:
                                road_valid = True
                                break
                        if road_valid:
                            current_player.roads.append(hover_edge)
                            current_player.placed_road = True
                            
                    # Advance turn when both placed
                    if current_player.placed_settlement and current_player.placed_road:
                        game.next_player()
                        
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                panning = False
                
            elif event.type == pygame.MOUSEMOTION and panning:
                dx = event.pos[0] - pan_start_mouse[0]
                dy = event.pos[1] - pan_start_mouse[1]
                offset_x = pan_start_offset[0] + dx
                offset_y = pan_start_offset[1] + dy
                
            elif event.type == pygame.MOUSEWHEEL:
                zoom *= 1.1 if event.y > 0 else 0.9
                zoom = max(0.5, min(zoom, 3.0))
                
            # Dice roll and end turn
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if game.phase == "regular":
                    if roll_btn.collidepoint(event.pos) and not game.dice_rolled:
                        handle_dice_roll(game)
                        game.dice_rolled = True
                    elif end_turn_btn.collidepoint(event.pos) and game.dice_rolled:
                        game.next_player()

        # Drawing
        screen.fill((30,30,30))
        
        # Draw tiles
        for res, num, pos in game.tiles:
            draw_hexagon(res, pos[0], pos[1], SIZE*0.95, num)
        
        # Highlight hover targets
        if hover_node:
            sx, sy = world_to_screen(*hover_node)
            pygame.draw.circle(screen, (255,255,255,100), (int(sx), int(sy)), int(NODE_RADIUS*zoom))
        if hover_edge:
            draw_road(hover_edge[0], hover_edge[1], "white")
        
        # Draw villages and roads
        for player in game.players:
            for village in player.villages:
                draw_village(*village)
            for road in player.roads:
                draw_road(*road, player.color)
        
        # Draw UI
        draw_ui(game)
        
        # Draw buttons
        if game.phase == "regular":
            if not game.dice_rolled:
                # Roll dice button
                pygame.draw.rect(screen, (0,150,0) if roll_btn.collidepoint(mx,my) else (0,100,0), roll_btn)
                text = font.render("Roll Dice", True, (255,255,255))
                screen.blit(text, (roll_btn.x+10, roll_btn.y+10))
            else:
                # End turn button
                pygame.draw.rect(screen, (150,0,0) if end_turn_btn.collidepoint(mx,my) else (100,0,0), end_turn_btn)
                text = font.render("End Turn", True, (255,255,255))
                screen.blit(text, (end_turn_btn.x+10, end_turn_btn.y+10))
                
                # Dice result
                if game.dice_result:
                    dice_text = font.render(f"{game.dice_result[0]} + {game.dice_result[1]} = {sum(game.dice_result)}", True, (255,255,255))
                    screen.blit(dice_text, (width-140, height-150))

        pygame.display.flip()

if __name__ == "__main__":
    main()