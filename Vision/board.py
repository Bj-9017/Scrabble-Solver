# board.py

from dataclasses import dataclass


SIZE = 15
CENTER = (7, 7)


# Premium layout from the board in your screenshot.
#
# TW = Triple Word
# DW = Double Word
# TL = Triple Letter
# DL = Double Letter
# "" = normal square

PREMIUM = [
    ["TW", "",   "",   "DL", "",   "",   "",   "TW", "",   "",   "",   "DL", "",   "",   "TW"],
    ["",   "DW", "",   "",   "",   "TL", "",   "",   "",   "TL", "",   "",   "",   "DW", ""],
    ["",   "",   "DW", "",   "",   "",   "DL", "",   "DL", "",   "",   "",   "DW", "",   ""],
    ["DL", "",   "",   "DW", "",   "",   "",   "DL", "",   "",   "",   "DW", "",   "",   "DL"],
    ["",   "",   "",   "",   "DW", "",   "",   "",   "",   "",   "DW", "",   "",   "",   ""],
    ["",   "TL", "",   "TL", "",   "TL", "",   "",   "",   "TL", "",   "TL", "",   "TL", ""],
    ["",   "",   "DL", "",   "",   "",   "DL", "",   "DL", "",   "",   "",   "DL", "",   ""],
    ["TW", "",   "",   "DL", "",   "",   "",   "DW", "",   "",   "",   "DL", "",   "",   "TW"],
    ["",   "",   "DL", "",   "",   "",   "DL", "",   "DL", "",   "",   "",   "DL", "",   ""],
    ["",   "TL", "",   "TL", "",   "TL", "",   "",   "",   "TL", "",   "TL", "",   "TL", ""],
    ["",   "",   "",   "",   "DW", "",   "",   "",   "",   "",   "DW", "",   "",   "",   ""],
    ["DL", "",   "",   "DW", "",   "",   "",   "DL", "",   "",   "",   "DW", "",   "",   "DL"],
    ["",   "",   "DW", "",   "",   "",   "DL", "",   "DL", "",   "",   "",   "DW", "",   ""],
    ["",   "DW", "",   "",   "",   "TL", "",   "",   "",   "TL", "",   "",   "",   "DW", ""],
    ["TW", "",   "",   "DL", "",   "",   "",   "TW", "",   "",   "",   "DL", "",   "",   "TW"],
]


# Standard English Scrabble letter values.
LETTER_VALUES = {
    "A": 1,
    "B": 3,
    "C": 3,
    "D": 2,
    "E": 1,
    "F": 4,
    "G": 2,
    "H": 4,
    "I": 1,
    "J": 8,
    "K": 5,
    "L": 1,
    "M": 3,
    "N": 1,
    "O": 1,
    "P": 3,
    "Q": 10,
    "R": 1,
    "S": 1,
    "T": 1,
    "U": 1,
    "V": 4,
    "W": 4,
    "X": 8,
    "Y": 4,
    "Z": 10,
}


@dataclass
class Move:
    word: str
    row: int
    col: int
    direction: str
    score: int
    tiles_used: int
    blanks: tuple = ()

    def __str__(self):
        # Convert internal 0-based coordinates to human-friendly coordinates.
        board_row = self.row + 1
        board_col = self.col + 1

        arrow = "→" if self.direction == "H" else "↓"

        blank_text = ""
        if self.blanks:
            positions = ", ".join(
                f"({r + 1},{c + 1})" for r, c in self.blanks
            )
            blank_text = f", blanks: {positions}"

        return (
            f"{self.word}  "
            f"at ({board_row},{board_col}) {arrow}  "
            f"Score: {self.score}"
            f"{blank_text}"
        )


class Board:

    def __init__(self, rows=None):
        if rows is None:
            rows = ["." * SIZE for _ in range(SIZE)]

        if len(rows) != SIZE:
            raise ValueError("Board must have exactly 15 rows.")

        rows = [row.upper() for row in rows]

        for row in rows:
            if len(row) != SIZE:
                raise ValueError("Every board row must contain exactly 15 cells.")

            for char in row:
                if char != "." and not ("A" <= char <= "Z"):
                    raise ValueError(
                        "Board cells must be '.' or letters A-Z."
                    )

        self.grid = [list(row) for row in rows]

    @classmethod
    def empty(cls):
        return cls()

    @classmethod
    def from_rows(cls, rows):
        return cls(rows)

    def is_empty(self):
        return all(
            self.grid[r][c] == "."
            for r in range(SIZE)
            for c in range(SIZE)
        )

    def inside(self, row, col):
        return 0 <= row < SIZE and 0 <= col < SIZE

    def get(self, row, col):
        if not self.inside(row, col):
            return None
        return self.grid[row][col]

    def premium(self, row, col):
        return PREMIUM[row][col]

    def print(self):
        print("    " + " ".join(f"{i + 1:2}" for i in range(SIZE)))

        for r in range(SIZE):
            print(
                f"{r + 1:2}  "
                + " ".join(f"{x:2}" for x in self.grid[r])
            )

    def letter_count(self):
        counts = {}

        for row in self.grid:
            for char in row:
                if char != ".":
                    counts[char] = counts.get(char, 0) + 1

        return counts