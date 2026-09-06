# main.py

from board import Board
from solver import CSWDictionary, ScrabbleSolver


# ------------------------------------------------------------
# LOAD CSW
# ------------------------------------------------------------

dictionary = CSWDictionary(r"C:\Ome_Bharath_J\8thsem_to_Job_higherstudies\Scrabble_Solver\Scrabble-Solver\Vision\CSW24.txt")

solver = ScrabbleSolver(dictionary)


# ------------------------------------------------------------
# ENTER BOARD
# ------------------------------------------------------------

# '.' = empty square
# 'A'-'Z' = existing tile

board = Board.from_rows([
    "...............",
    "...............",
    "...............",
    "...............",
    "...............",
    "...............",
    "...............",
    ".......V.......",
    ".......IF......",
    ".......AA......",
    ".......LANES...",
    "...........U...",
    "........TOMMY..",
    ".........RIYALS",
    ".......AXE....T",
])


# ------------------------------------------------------------
# ENTER YOUR RACK
# ------------------------------------------------------------

# '?' represents a blank tile.

rack = "NGFERTO"


# ------------------------------------------------------------
# SOLVE
# ------------------------------------------------------------

print("\nCurrent board:")
board.print()

print("\nRack:", rack)

print("\nBest move:")

best = solver.best_move(
    board,
    rack,
)

if best is None:
    print("No legal move found.")

else:
    print(best)


print("\nTop 20 moves:")

moves = solver.find_moves(
    board,
    rack,
    top_n=20,
)

for i, move in enumerate(moves, start=1):
    print(f"{i:2}. {move}")