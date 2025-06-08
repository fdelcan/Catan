import numpy as np

DESERT = 0
MOUNTAIN = 1
FOREST = 2
PASTURE = 3
FIELD = 4
BRICK = 5

player_Red = 1
player_Blue = 2
player_Yellow = 3
player_White = 4

# Main Game State
class GameState:
    def __init__(self, num_players = 4):
        self.number_players = num_players
        row_sizes = [3, 4, 4, 5, 5, 6, 6, 5, 5, 4, 4, 3]
        self.nodes = [np.zeros((size,2), dtype=int) for size in row_sizes]
        self.edges = {}  # key: ((x1,y1),(x2,y2)), value: color (int)
        self.tiles = np.zeros((19,2), dtype=int)
        self.cards = np.zeros((num_players, 6), dtype=int)  # 6 types of cards in the order Desert, Montain, Forest, Pasture, Field, Brick
        self.bonus_cards = np.zeros((num_players, 7), dtype=int) # Knight, Victory Point, free Roads, Free cards, Monopoly, Longest Road, Largest Army
        self.robber = (0, 0)  # Robber position on the board
        self.current_player = 0  # Index of the current player
        self._map_tiles_to_node_indices()

    def add_edge(self, point_A, point_B, color):
        # Order points unambiguously
        ordered_edge = tuple(sorted([point_A, point_B]))
        self.edges[ordered_edge] = color

    def has_edge(self, point_A, point_B):
        ordered_edge = tuple(sorted([point_A, point_B]))
        return self.edges.get(ordered_edge, False)
    
    def _index_tiles_by_number(self):
        """Builds a dict: dice_number → [tile_idx,…]."""
        self.number_to_tiles = {}
        for idx, (dice, res) in enumerate(self.tiles):
            self.number_to_tiles.setdefault(dice, []).append(idx)
            
    def _map_tiles_to_node_indices(self):
        """
        Build a dict: tile_idx → list of (node_row, node_col) for its 6 corners.
        You must fill this in according to your layout.
        Here’s a *template* using a manually defined mapping:
        """
        self.tile_to_nodes = {}
        manual_map = {
            0:  [(0,0),(1,0),(1,1),(2,0),(2,1),(3,1)],
            1:  [(0,1),(1,1),(1,2),(2,1),(2,2),(3,2)],
            2:  [(0,2),(1,2),(1,3),(2,2),(2,3),(3,3)],
            3:  [(2,0),(3,0),(3,1),(4,0),(4,1),(5,1)],
            4:  [(2,1),(3,1),(3,2),(4,1),(4,2),(5,2)],
            5:  [(2,2),(3,2),(3,3),(4,2),(4,3),(5,3)],
            6:  [(2,3),(3,3),(3,4),(4,3),(4,4),(5,4)],
            7:  [(4,0),(5,0),(5,1),(6,0),(6,1),(7,0)],
            8:  [(4,1),(5,1),(5,2),(6,1),(6,2),(7,1)],
            9:  [(4,2),(5,2),(5,3),(6,2),(6,3),(7,2)],
            10: [(4,3),(5,3),(5,4),(6,3),(6,4),(7,3)],
            11: [(4,4),(5,4),(5,5),(6,4),(6,5),(7,4)],
            12: [(6,1),(7,0),(7,1),(8,0),(8,1),(9,0)],
            13: [(6,2),(7,1),(7,2),(8,1),(8,2),(9,1)],
            14: [(6,3),(7,2),(7,3),(8,2),(8,3),(9,2)],
            15: [(6,4),(7,3),(7,4),(8,3),(8,4),(9,3)],
            16: [(8,1),(9,0),(9,1),(10,0),(10,1),(11,0)],
            17: [(8,2),(9,1),(9,2),(10,1),(10,2),(11,1)],
            18: [(8,3),(9,2),(9,3),(10,2),(10,3),(11,2)],
            }
        self.tile_to_nodes = manual_map

    # ── RESOURCE DISTRIBUTION ─────────────────────────────────────────

    def distribute_resources(self, dice_roll):
        """
        Called when you roll `dice_roll`.  Looks up only the
        tiles with that number, then for each of their 6 nodes
        awards the correct resource in O(1) per node.
        """
        for t in self.number_to_tiles.get(dice_roll, []):
            resource_type = self.tiles[t,1]
            for (r, c) in self.tile_to_nodes[t]:
                player, count = self.nodes[r][c]
                if player:
                    # player indices are 1…N, convert to 0-based
                    self.cards[player-1, resource_type] += count
                    
    def initialize_random_board(self):
        """
        Initialize the tiles with a random configuration.
        Also set the initial player randomly
        """
        resources = [DESERT] + [MOUNTAIN, BRICK] * 3 + [FOREST, PASTURE, FIELD] * 4
        numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        np.random.shuffle(numbers)
        np.random.shuffle(resources)
        desert = 0
        for i in range(19):
            self.tiles[i, 0] = resources[i]  # Resource type
            if resources[i] == DESERT:
                desert = 1
                self.robber = i  
            else:
                self.tiles[i, 1] = numbers[i - desert]
            
        self.current_player = np.random.randint(0, self.number_players)
            

def generate_game():
    """
    Generates a new game state with a random board and initial player.
    """
    game_state = GameState()
    game_state.initialize_random_board()
    return game_state

def possible_moves(game_state: GameState, player = None):
    """
    Check the possible house, road, bonus and city moves for the current player.
    """
    if player is None:
        player = game_state.current_player
    cards = game_state.cards[player]
    
    house_cost = np.array([BRICK, FOREST, PASTURE, FIELD])  # Brick, Forest, Pasture, Field
    for card in house_cost:
        if cards[card] < 1:
            return False

    
    

    return 0