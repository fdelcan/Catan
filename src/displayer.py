import sys, os, math, random
import pygame, pygame.gfxdraw
import structure

# ─────────────────────────────────────────────────────────────────────────────
# Constants and Options
SIZE = 70
NODE_RADIUS = SIZE * 0.10
PRINT_NODES = False  # Toggle printing and drawing of node names

# Mapping for resources
RESOURCE_NAMES = {
    structure.DESERT:   'desert',
    structure.MOUNTAIN: 'rock',
    structure.FOREST:   'wood',
    structure.PASTURE:  'sheep',
    structure.FIELD:    'wheat',
    structure.BRICK:    'clay',
}
COLOR_MAP = {
    'sheep':  (200,255,200),
    'wheat':  (255,240,150),
    'clay':   (205, 92, 92),
    'wood':   (139, 69, 19),
    'rock':   (160,160,160),
    'desert': (238,214,175),
}
PLAYER_COLOR = {
    structure.player_Red:   'red',
    structure.player_Blue:  'blue',
    structure.player_Yellow:'yellow',
    structure.player_White: 'white'
}

# Pygame init
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
pygame.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Catan Viewer")
font = pygame.font.SysFont("Arial", 20)

# Camera
class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0,0)
        self.scale = 1.0
    def world_to_screen(self, x, y):
        return (
            int(x*self.scale + WIDTH/2 + self.offset.x),
            int(y*self.scale + HEIGHT/2 + self.offset.y)
        )
    def screen_to_world(self, sx, sy):
        return (
            (sx - WIDTH/2 - self.offset.x)/self.scale,
            (sy - HEIGHT/2 - self.offset.y)/self.scale
        )

# Board layout
def board_positions(size):
    rows = [3,4,5,4,3]
    v = size*1.5; h = size*math.sqrt(3)
    y0 = -2*v
    pts=[]
    for r,cnt in enumerate(rows):
        y=y0+r*v; x0=-h*(cnt-1)/2
        for i in range(cnt): pts.append((x0+i*h,y))
    return pts, rows

def hexagon_vertices(cx, cy, size):
    return [
        (
            cx + size*math.cos(math.radians(60*i - 30)),
            cy + size*math.sin(math.radians(60*i - 30))
        ) for i in range(6)
    ]

# Precompute tile geometry
tile_pts, tile_rows = board_positions(SIZE)
flat_to_rc = {}
centers = []
idx=0
for r,cnt in enumerate(tile_rows):
    row=[]
    for c in range(cnt):
        row.append(tile_pts[idx])
        flat_to_rc[idx]=(r,c)
        idx+=1
    centers.append(row)
# tile_vertices[flat_index] = list of 6 world coords
tile_vertices = [hexagon_vertices(cx,cy,SIZE) for r in range(len(tile_rows)) for cx,cy in [centers[r][c] for c in range(len(centers[r]))]]

# Build world pos for each node (r,c) in gamestate using tile_to_nodes
def build_node_worlds(gs):
    node_world = {}
    for flat, corners in gs.tile_to_nodes.items():
        verts = tile_vertices[flat]
        for i,(nr,nc) in enumerate(corners):
            if (nr,nc) not in node_world:
                node_world[(nr,nc)] = verts[i]
    return node_world

# Draw functions

def draw_hex(flat_idx, gs, camera):
    enum, num = map(int, gs.tiles[flat_idx])
    name = RESOURCE_NAMES[enum]
    col = COLOR_MAP[name]
    cx,cy = centers[flat_to_rc[flat_idx][0]][flat_to_rc[flat_idx][1]]
    pts = hexagon_vertices(cx,cy,SIZE*0.95)
    spts=[camera.world_to_screen(x,y) for x,y in pts]
    pygame.gfxdraw.filled_polygon(screen,spts,col)
    pygame.gfxdraw.aapolygon(screen,spts,(0,0,0))
    if num>0:
        sx,sy = camera.world_to_screen(cx,cy)
        txt=font.render(str(num),True,(0,0,0))
        screen.blit(txt,(sx-txt.get_width()//2, sy-txt.get_height()//2))

# Plot GameState
def draw_gs(gs, screen, camera):
    # draw tiles
    for flat in range(len(tile_vertices)):
        draw_hex(flat, gs, camera)
    # build node positions
    node_world = build_node_worlds(gs)
    # draw nodes labels
    if PRINT_NODES:
        for (nr,nc),pos in node_world.items():
            sx,sy = camera.world_to_screen(*pos)
            lbl = f"{nr},{nc}"
            txt=font.render(lbl,True,(255,255,255))
            screen.blit(txt,(sx-txt.get_width()//2, sy-txt.get_height()//2))
    # draw houses/cities
    for (nr,nc), (player,count) in {(nr,nc):tuple(gs.nodes[nr][nc]) for nr in range(len(gs.nodes)) for nc in range(gs.nodes[nr].shape[0])}.items():
        if player>0:
            x,y = node_world[(nr,nc)]
            sx,sy = camera.world_to_screen(x,y)
            color = pygame.Color(PLAYER_COLOR[player])
            size = int(NODE_RADIUS*camera.scale* (2 if count>1 else 1))
            pygame.draw.rect(screen,color,(sx-size,sy-size,2*size,2*size))
    # draw roads
    for (pa,pb),player in gs.edges.items():
        if player>0:
            x1,y1 = node_world[pa]; x2,y2 = node_world[pb]
            sx1,sy1 = camera.world_to_screen(x1,y1)
            sx2,sy2 = camera.world_to_screen(x2,y2)
            pygame.draw.line(screen,pygame.Color(PLAYER_COLOR[player]),(sx1,sy1),(sx2,sy2), int(NODE_RADIUS*camera.scale))

# Main loop
if __name__=='__main__':
    clock=pygame.time.Clock()
    camera=Camera()
    gs=structure.generate_game()
    while True:
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type==pygame.MOUSEBUTTONDOWN:
                if ev.button==1: last=pygame.Vector2(ev.pos)
                elif ev.button==2: camera=Camera()
                elif ev.button==4: camera.scale*=1.1
                elif ev.button==5: camera.scale/=1.1
            if ev.type==pygame.MOUSEMOTION and ev.buttons[0]:
                m=pygame.Vector2(ev.pos); camera.offset+=m-last; last=m
        screen.fill((30,30,30))
        draw_gs(gs,screen,camera)
        pygame.display.flip(); clock.tick(60)