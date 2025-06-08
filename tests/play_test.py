# catan.py — Fully Functional Catan Simulator
import sys, os, math, random
from collections import Counter
import pygame, pygame.gfxdraw

# ─────────────────────────────────────────────────────────────────────────────
# Constants
SIZE         = 70
HOUSE_SIZE   = SIZE // 8
ROAD_WIDTH   = int(SIZE * 0.15)
NODE_RADIUS  = SIZE * 0.10
NODE_DETECT  = NODE_RADIUS * 1.2
RESOURCE_TYPES = ["sheep", "wheat", "rock", "clay", "wood"]
COLOR_MAP = {
    "sheep":  (200,255,200),
    "wheat":  (255,240,150),
    "clay":   (205, 92, 92),
    "wood":   (139, 69, 19),
    "rock":   (160,160,160),
    "desert": (238,214,175),
}
PORT_TYPES   = RESOURCE_TYPES + ["generic"]*4
PLAYER_COLORS= ["red","blue","green","orange"]

# Pygame init
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
pygame.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Catan")
font = pygame.font.SysFont("Arial", 20)

# ─────────────────────────────────────────────────────────────────────────────
# Utility transforms
def world_to_screen(x,y):
    return int(WIDTH/2 + x), int(HEIGHT/2 + y)
def screen_to_world(sx,sy):
    return sx - WIDTH/2, sy - HEIGHT/2

# Board layout (3-4-5-4-3)
def board_positions(size):
    rows = [3,4,5,4,3]
    v = size * 1.5
    h = size * math.sqrt(3)
    y0= -2*v
    pts=[]
    for r,cnt in enumerate(rows):
        y=y0 + r*v
        x0=-h*(cnt-1)/2
        for i in range(cnt):
            pts.append((x0 + i*h, y))
    return pts, rows

def hexagon_vertices(cx,cy,size):
    return [
        (cx + size*math.cos(math.radians(60*i - 30)),
         cy + size*math.sin(math.radians(60*i - 30)))
        for i in range(6)
    ]

# ─────────────────────────────────────────────────────────────────────────────
# Player state
class Player:
    def __init__(self, color):
        self.color     = color
        self.resources = Counter()
        self.houses    = []   # global house IDs
        self.roads     = []   # global road IDs

# ─────────────────────────────────────────────────────────────────────────────
# Main Game State
class GameState:
    def __init__(self, n=4):
        self.n   = n
        # players in fixed colors
        self.players = [Player(PLAYER_COLORS[i]) for i in range(n)]

        # setup turn order: forward settlements & roads, then reverse
        seq = []
        for i in range(n):
            seq.append((i,'settlement'))
            seq.append((i,'road'))
        for i in reversed(range(n)):
            seq.append((i,'settlement'))
            seq.append((i,'road'))
        self.setup_seq = seq
        self.seq_i     = 0
        self.phase     = 'setup'   # or 'regular','discard','robber','rob_choose'
        self.dice_rolled = False
        self.dice_result = None

        # Build hex grid
        pts, self.rows = board_positions(SIZE)
        self.flat_to_rc     = {}
        self.centers   = []
        idx=0
        for r,cnt in enumerate(self.rows):
            row=[]
            for _ in range(cnt):
                row.append(pts[idx])
                self.flat_to_rc[idx] = (r,len(row)-1)
                idx+=1
            self.centers.append(row)

        # Spiral ordering for numbers
        spiral = [0,1,2,7,12,17,18,13,8,3,4,9,14,16,15,10,5,6,11]
        # Resources & token numbers
        pool = ["wood"]*4 + ["sheep"]*4 + ["wheat"]*4 + ["clay"]*3 + ["rock"]*3 + ["desert"]
        random.shuffle(pool)
        nums = [2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12]
        random.shuffle(nums); ni=0; desert_placed=False

        # board[r][c] = [res,num]
        self.board = [[None]*cnt for cnt in self.rows]
        for flat in spiral:
            r,c = self.flat_to_rc[flat]
            res = pool.pop()
            if res=='desert' and not desert_placed:
                num=None
                desert_placed=True
                self.robber = flat
            else:
                num = nums[ni]; ni+=1
            self.board[r][c] = [res,num]

        # Compute nodes & edges per tile
        self.tile_nodes=[]
        self.tile_edges=[]
        edge_count={}
        for flat in range(idx):
            r,c = self.flat_to_rc[flat]
            cx,cy = self.centers[r][c]
            verts = hexagon_vertices(cx,cy,SIZE)
            self.tile_nodes.append(verts)
            es=[]
            for i in range(6):
                e = tuple(sorted([verts[i], verts[(i+1)%6]]))
                es.append(e)
                edge_count[e] = edge_count.get(e,0) + 1
            self.tile_edges.append(es)

        # All valid nodes & edges
        self.valid_nodes = list({v for verts in self.tile_nodes for v in verts})
        self.valid_edges = list(edge_count.keys())

        # Ports: pick coastal edges (count==1), place marker at outer vertex
        coastal = [e for e,cnt in edge_count.items() if cnt==1]
        chosen = random.sample(coastal, min(len(coastal),9))
        random.shuffle(PORT_TYPES)
        self.ports=[]
        for e,ptype in zip(chosen, PORT_TYPES):
            # place at node farther from board center
            v_out = max(e, key=lambda v: math.hypot(v[0],v[1]))
            self.ports.append((v_out,ptype))

        # initialize first turn
        self.current_idx, self.current_act = self.setup_seq[0]

    @property
    def current_player(self):
        return self.players[self.current_idx]

    # Advance through setup
    def next_setup(self):
        self.seq_i+=1
        if self.seq_i < len(self.setup_seq):
            self.current_idx, self.current_act = self.setup_seq[self.seq_i]
        else:
            self.phase = 'regular'
            self.current_idx = 0

    # Build cost checks
    def can_build_settlement(self):
        p=self.current_player
        return all(p.resources[r]>=1 for r in ["sheep","wheat","clay","wood"])
    def can_build_road(self):
        p=self.current_player
        return p.resources["clay"]>=1 and p.resources["wood"]>=1

    # Settlement validity: empty + no adjacent
    def is_valid_settlement(self, node):
        # not occupied
        for p in self.players:
            for hid in p.houses:
                tid,loc = divmod(hid-1,12)
                corner = loc if loc<6 else loc-6
                if self.tile_nodes[tid][corner]==node:
                    return False
        # no adjacent
        for e in self.valid_edges:
            if node in e:
                other = e[1] if e[0]==node else e[0]
                for p in self.players:
                    for hid in p.houses:
                        tid,loc=divmod(hid-1,12)
                        cor = loc if loc<6 else loc-6
                        if self.tile_nodes[tid][cor]==other:
                            return False
        return True

    # Map node→global house ID
    def house_id(self, node):
        for tid,verts in enumerate(self.tile_nodes):
            if node in verts:
                local = verts.index(node)+1
                return tid*12 + local
        return None

    # Map edge→global road ID
    def edge_id(self, edge):
        for tid,edges in enumerate(self.tile_edges):
            for i,e in enumerate(edges):
                if e==edge:
                    return tid*6 + (i+1)
        return None

    # Distribute resources on dice (excluding robber logic here)
    def handle_dice(self):
        d1,d2 = random.randint(1,6),random.randint(1,6)
        self.dice_result=(d1,d2)
        self.dice_rolled=True
        tot = d1+d2
        if tot==7:
            # DISCARD phase
            self.discard_list = [i for i,p in enumerate(self.players)
                                 if sum(p.resources.values())>7]
            self.discard_ptr = 0
            if self.discard_list:
                self.phase="discard"
                self.current_idx=self.discard_list[0]
                self.to_discard = sum(self.current_player.resources.values())//2
                self.discarded=0
            else:
                self.phase="robber"
            return
        # normal resource distribution
        for flat, verts in enumerate(self.tile_nodes):
            r,c = flat//len(self.rows[0]), flat%len(self.rows[0])  # adjust mapping
            res,num = self.board[r][c]
            if num==tot and res!="desert":
                cx,cy = self.centers[r][c]
                for p in self.players:
                    for hid in p.houses:
                        tid,loc=divmod(hid-1,12)
                        lvl = 1 if loc<6 else 2
                        cor = loc if loc<6 else loc-6
                        x,y = self.tile_nodes[tid][cor]
                        if math.hypot(x-cx,y-cy) < SIZE*1.1:
                            p.resources[res] += (2 if lvl==2 else 1)

    # Move robber to a new tile by clicking a node inside it
    def move_robber(self, node):
        for flat, verts in enumerate(self.tile_nodes):
            # find tile center
            r,c = flat//len(self.rows[0]), flat%len(self.rows[0])
            cx,cy = self.centers[r][c]
            if math.hypot(cx-node[0], cy-node[1])<SIZE*0.6 and flat!=self.robber:
                self.robber=flat
                # determine victims
                victims=[]
                for i,p in enumerate(self.players):
                    if i==self.current_idx: continue
                    for hid in p.houses:
                        tid,loc=divmod(hid-1,12)
                        cor = loc if loc<6 else loc-6
                        x,y = self.tile_nodes[tid][cor]
                        if math.hypot(x-cx,y-cy)<SIZE*1.1:
                            victims.append(i); break
                if victims:
                    self.phase="rob_choose"
                    self.rob_victims=victims
                else:
                    self.phase="regular"
                return

    # Transfer one random resource from victim to current player
    def rob_transfer(self, victim_idx):
        victim = self.players[victim_idx]
        pool = []
        for r,cnt in victim.resources.items():
            pool += [r]*cnt
        if pool:
            res = random.choice(pool)
            victim.resources[res]-=1
            self.current_player.resources[res]+=1
        self.phase="regular"

    # Advance to next player (regular turn)
    def next_player(self):
        self.current_idx = (self.current_idx+1)%self.n
        self.dice_rolled=False
        self.dice_result=None
        if self.phase=="regular":
            pass

# ─────────────────────────────────────────────────────────────────────────────
# Drawing helpers
def draw_hex(res_num, center, highlight=False):
    res,num = res_num
    col = COLOR_MAP[res]
    pts = hexagon_vertices(center[0], center[1], SIZE*0.95)
    spts= [world_to_screen(x,y) for x,y in pts]
    pygame.gfxdraw.filled_polygon(screen, spts, col)
    pygame.gfxdraw.aapolygon(screen, spts, (0,0,0))
    if num:
        txt = font.render(str(num), True, (255,0,0) if highlight else (0,0,0))
        sx,sy = world_to_screen(*center)
        screen.blit(txt, (sx-txt.get_width()/2, sy-txt.get_height()/2))

def draw_settlement(node, level, color):
    sx,sy=world_to_screen(*node)
    sz = HOUSE_SIZE
    pygame.draw.rect(screen, pygame.Color(color), (sx-sz, sy-sz, 2*sz, 2*sz))
    if level==2:
        pygame.draw.circle(screen,(255,255,0),(sx,sy),sz//2)

def draw_road(edge, color):
    (x1,y1),(x2,y2)=edge
    sx1,sy1=world_to_screen(x1,y1)
    sx2,sy2=world_to_screen(x2,y2)
    pygame.draw.line(screen, pygame.Color(color), (sx1,sy1),(sx2,sy2), ROAD_WIDTH)

def draw_robber(center):
    sx,sy=world_to_screen(*center)
    surf=pygame.Surface((SIZE,SIZE),pygame.SRCALPHA)
    pygame.draw.circle(surf, (0,0,0,100), (SIZE//2,SIZE//2), SIZE//2)
    screen.blit(surf,(sx-SIZE//2, sy-SIZE//2))

def draw_ports(ports):
    for node,ptype in ports:
        sx,sy=world_to_screen(*node)
        pygame.gfxdraw.filled_circle(screen, sx,sy, int(SIZE*0.2), (255,255,255,200))
        lbl=font.render(ptype[0].upper(), True, (0,0,0))
        screen.blit(lbl,(sx-lbl.get_width()/2, sy-lbl.get_height()/2))

# Hit-box overlays
def draw_hitbox_node(node):
    sx,sy=world_to_screen(*node)
    pygame.gfxdraw.filled_circle(screen, sx,sy, int(NODE_RADIUS*1.5), (255,255,255,80))

def draw_hitbox_edge(edge):
    mx = (edge[0][0]+edge[1][0])/2
    my = (edge[0][1]+edge[1][1])/2
    sx,sy=world_to_screen(mx,my)
    pygame.gfxdraw.filled_circle(screen, sx,sy, int(NODE_RADIUS*1.2), (255,255,255,80))

# UI bar
def draw_ui(game):
    # turn display
    txt=font.render(f"Turn: {game.current_player.color}", True, (255,255,255))
    screen.blit(txt, (10,10))
    # resources with colored background
    x,y = 10, HEIGHT-40
    for res in RESOURCE_TYPES:
        cnt = game.current_player.resources[res]
        lbl = font.render(f"{res}: {cnt}", True, (0,0,0))
        w,h = lbl.get_width()+6, lbl.get_height()+4
        bg = pygame.Surface((w,h))
        bg.fill(COLOR_MAP[res])
        screen.blit(bg,(x,y))
        screen.blit(lbl,(x+3,y+2))
        x += w+6
    # Roll / End buttons
    if game.phase=="regular":
        if not game.dice_rolled:
            br = pygame.Rect(WIDTH-150, HEIGHT-70, 140,50)
            pygame.draw.rect(screen,(0,120,0),br)
            screen.blit(font.render("Roll Dice", True, (255,255,255)), (WIDTH-140, HEIGHT-60))
            game.btn_roll = br
        else:
            be = pygame.Rect(WIDTH-150, HEIGHT-70, 140,50)
            pygame.draw.rect(screen,(120,0,0),be)
            screen.blit(font.render("End Turn", True, (255,255,255)), (WIDTH-140, HEIGHT-60))
            game.btn_end = be
            d=game.dice_result
            screen.blit(font.render(f"{d[0]} + {d[1]} = {sum(d)}", True, (255,255,255)),
                        (WIDTH-150, HEIGHT-140))
    # Discard menu
    if game.phase=="discard":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,150)); screen.blit(overlay,(0,0))
        req = game.to_discard - game.discarded
        txt=font.render(f"Discard {req} cards", True, (255,255,255))
        screen.blit(txt,(WIDTH//2-txt.get_width()//2,50))
        game.disc_buttons=[]
        y0=120
        for res,cnt in game.current_player.resources.items():
            if cnt>0:
                lbl=font.render(f"{res}: {cnt}",True,(0,0,0))
                w,h=lbl.get_width()+10, lbl.get_height()+6
                rct=pygame.Rect(WIDTH//2-w//2, y0, w,h)
                pygame.draw.rect(screen,(200,200,200),rct)
                screen.blit(lbl,(rct.x+5, rct.y+3))
                game.disc_buttons.append((res,rct))
                y0 += h+10
    # Place robber prompt
    if game.phase=="robber":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,100)); screen.blit(overlay,(0,0))
        txt=font.render("Place Robber",True,(255,255,255))
        screen.blit(txt,(WIDTH//2-txt.get_width()//2,20))
    # Rob victim choice
    if game.phase=="rob_choose":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,150)); screen.blit(overlay,(0,0))
        txt=font.render("Choose victim",True,(255,255,255))
        screen.blit(txt,(WIDTH//2-txt.get_width()//2,20))
        game.rob_buttons=[]
        y0=80
        for vid in game.rob_victims:
            col = game.players[vid].color
            lbl=font.render(col,True,(0,0,0))
            w,h=lbl.get_width()+10, lbl.get_height()+6
            rct=pygame.Rect(WIDTH//2-w//2, y0, w,h)
            pygame.draw.rect(screen,pygame.Color(col),rct)
            screen.blit(lbl,(rct.x+5,rct.y+3))
            game.rob_buttons.append((vid,rct))
            y0+=h+10

# ─────────────────────────────────────────────────────────────────────────────
# Main loop
def main():
    clock=pygame.time.Clock()
    game = GameState(4)

    while True:
        mx,my = pygame.mouse.get_pos()
        wx,wy = screen_to_world(mx,my)

        # hover detection
        hover_node=None
        for v in game.valid_nodes:
            if math.hypot(v[0]-wx, v[1]-wy) < NODE_DETECT:
                hover_node=v; break
        hover_edge=None
        for e in game.valid_edges:
            midx = (e[0][0]+e[1][0])/2
            midy = (e[0][1]+e[1][1])/2
            if math.hypot(midx-wx, midy-wy) < SIZE*0.6:
                hover_edge=e; break

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                pygame.quit(); sys.exit()

            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                # SETUP PHASE
                if game.phase=="setup":
                    if game.current_act=="settlement" and hover_node and game.is_valid_settlement(hover_node):
                        hid = game.house_id(hover_node)
                        game.current_player.houses.append(hid)
                        # second placement grants resource
                        if game.seq_i >= game.n:
                            # distribute 1 from each adjacent tile
                            for flat,verts in enumerate(game.tile_nodes):
                                r,c = divmod(flat, len(game.rows))
                                cx,cy = game.centers[r][c]
                                if math.hypot(game.centers[r][c][0]-hover_node[0],
                                              game.centers[r][c][1]-hover_node[1])<SIZE*1.1:
                                    res,_ = game.board[r][c]
                                    if res!="desert":
                                        game.current_player.resources[res]+=1
                        game.next_setup()

                    elif game.current_act=="road" and hover_edge:
                        rid = game.edge_id(hover_edge)
                        game.current_player.roads.append(rid)
                        game.next_setup()

                # REGULAR PHASE
                elif game.phase=="regular":
                    # Roll
                    if hasattr(game,"btn_roll") and game.btn_roll.collidepoint(mx,my) \
                       and not game.dice_rolled:
                        game.handle_dice()

                    # End turn
                    elif hasattr(game,"btn_end") and game.btn_end.collidepoint(mx,my) \
                         and game.dice_rolled:
                        game.next_player()

                    # Build settlement
                    elif hover_node and game.can_build_settlement() and game.is_valid_settlement(hover_node):
                        # pay
                        for r in ["sheep","wheat","clay","wood"]:
                            game.current_player.resources[r]-=1
                        hid=game.house_id(hover_node)
                        game.current_player.houses.append(hid)

                    # Build road (right-click)
                    # handled in BUTTONDOWN 3 below

                # DISCARD PHASE
                elif game.phase=="discard":
                    for res,rct in game.disc_buttons:
                        if rct.collidepoint(mx,my):
                            game.current_player.resources[res]-=1
                            game.discarded+=1
                            if game.discarded>=game.to_discard:
                                game.discard_ptr+=1
                                if game.discard_ptr<len(game.discard_list):
                                    next_idx = game.discard_list[game.discard_ptr]
                                    game.current_idx = next_idx
                                    game.to_discard = sum(game.current_player.resources.values())//2
                                    game.discarded=0
                                else:
                                    game.phase="robber"
                            break

                # ROBBER PLACEMENT
                elif game.phase=="robber":
                    if hover_node:
                        game.move_robber(hover_node)

                # ROBBER CHOOSE VICTIM
                elif game.phase=="rob_choose":
                    for vid,rct in game.rob_buttons:
                        if rct.collidepoint(mx,my):
                            game.rob_transfer(vid)
                            break

            # build roads on right-click
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==3 and game.phase=="regular":
                if hover_edge and game.can_build_road():
                    rid = game.edge_id(hover_edge)
                    # must connect to your network
                    valid=False
                    # adjacent to your houses:
                    for hid in game.current_player.houses:
                        tid,loc=divmod(hid-1,12)
                        cor = loc if loc<6 else loc-6
                        if game.tile_nodes[tid][cor] in hover_edge:
                            valid=True
                    # or adjacent to your roads
                    if not valid:
                        for orid in game.current_player.roads:
                            otid,oi = divmod(orid-1,6)
                            if game.tile_edges[otid][oi] == hover_edge:
                                valid=True
                    if valid:
                        # pay
                        game.current_player.resources["clay"]-=1
                        game.current_player.resources["wood"]-=1
                        game.current_player.roads.append(rid)

        # ─────────────────────────────────────────────────────────────────────
        # DRAWING
        screen.fill((30,30,30))

        # draw hexes
        dice_tot = sum(game.dice_result) if game.dice_result else None
        for r,row in enumerate(game.board):
            for c,tile in enumerate(row):
                hl = (tile[1]==dice_tot and tile[0]!="desert")
                draw_hex(tile, game.centers[r][c], hl)

        # draw ports on nodes
        draw_ports(game.ports)

        # draw hit-boxes
        if game.phase=="setup":
            if game.current_act=="settlement":
                for node in game.valid_nodes:
                    if game.is_valid_settlement(node):
                        draw_hitbox_node(node)
            elif game.current_act=="road":
                # only edges adjacent to last settlement
                last_hid = game.current_player.houses[-1]
                tid,loc=divmod(last_hid-1,12); cor=loc if loc<6 else loc-6
                base_node = game.tile_nodes[tid][cor]
                for e in game.valid_edges:
                    if base_node in e:
                        draw_hitbox_edge(e)

        elif game.phase=="regular":
            # settlement spots
            if game.can_build_settlement():
                for node in game.valid_nodes:
                    if game.is_valid_settlement(node):
                        draw_hitbox_node(node)
            # road spots
            if game.can_build_road():
                for e in game.valid_edges:
                    # connected to your network
                    mid_valid=False
                    for hid in game.current_player.houses:
                        tid,loc=divmod(hid-1,12); cor=loc if loc<6 else loc-6
                        if game.tile_nodes[tid][cor] in e:
                            mid_valid=True
                    for orid in game.current_player.roads:
                        otid,oi = divmod(orid-1,6)
                        if game.tile_edges[otid][oi] in e:
                            mid_valid=True
                    if mid_valid:
                        draw_hitbox_edge(e)

        # draw existing roads
        for p in game.players:
            for rid in p.roads:
                tid,i = divmod(rid-1,6)
                draw_road(game.tile_edges[tid][i], p.color)

        # draw settlements & cities
        for p in game.players:
            for hid in p.houses:
                tid,loc=divmod(hid-1,12)
                lvl = 1 if loc<6 else 2
                cor = loc if loc<6 else loc-6
                draw_settlement(game.tile_nodes[tid][cor], lvl, p.color)

        # draw robber
        rb_flat = game.robber
        rr, rc = game.flat_to_rc[rb_flat]
        center = game.centers[rr][rc]
        draw_robber(center)

        # draw UI overlays
        draw_ui(game)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()