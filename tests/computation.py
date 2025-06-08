# tests/test_main.py

import sys, os
this_dir    = os.path.dirname(__file__)                   # .../tests
project_root = os.path.abspath(os.path.join(this_dir, '..'))
sys.path.insert(0, project_root)

from src.structure import *
from src.displayer import *

if __name__ == "__main__":
    game = generate_game()
    print("Initial Game State:")
    print("Tiles:", game.tiles)
    print("Current Player:", game.current_player)
    draw_gs(game)