# solver.py

from collections import Counter

from board import (
    Board,
    Move,
    SIZE,
    CENTER,
    LETTER_VALUES,
)


DIRECTIONS = {
    "H": (0, 1),
    "V": (1, 0),
}


class CSWDictionary:

    def __init__(self, path):
        self.words = set()

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().upper()

                # CSW words should contain only A-Z.
                if word.isalpha():
                    self.words.add(word)

        # We cannot play one-letter words in standard Scrabble.
        self.words = {
            word for word in self.words
            if len(word) >= 2
        }

        # Basic hash-map index used by the simple word-finder search.  Keeping
        # words in length buckets avoids examining words that cannot fit in a
        # requested placement.
        self.words_by_length = {}

        for word in self.words:
            self.words_by_length.setdefault(len(word), []).append(word)

        # A trie lets the solver discard a partial placement as soon as it
        # cannot form a dictionary word.  This is substantially cheaper than
        # trying every word in the lexicon at every board position.
        self.trie = {}

        for word in self.words:
            node = self.trie

            for letter in word:
                node = node.setdefault(letter, {})

            node[None] = True

        print(f"Loaded {len(self.words):,} CSW words.")

    def __contains__(self, word):
        return word in self.words


class ScrabbleSolver:

    def __init__(self, dictionary):
        self.dictionary = dictionary

    # ------------------------------------------------------------
    # BASIC BOARD HELPERS
    # ------------------------------------------------------------

    def _placement_cells(self, word, row, col, direction):
        """
        Return the board coordinates occupied by a word.
        """
        dr, dc = DIRECTIONS[direction]

        cells = []

        for i in range(len(word)):
            r = row + i * dr
            c = col + i * dc

            if not (0 <= r < SIZE and 0 <= c < SIZE):
                return None

            cells.append((r, c))

        return cells

    def _before_after_are_empty(
        self,
        board,
        row,
        col,
        direction,
        word_length,
    ):
        """
        A placed word cannot be part of a longer existing word.
        """

        dr, dc = DIRECTIONS[direction]

        before_r = row - dr
        before_c = col - dc

        after_r = row + word_length * dr
        after_c = col + word_length * dc

        if board.inside(before_r, before_c):
            if board.get(before_r, before_c) != ".":
                return False

        if board.inside(after_r, after_c):
            if board.get(after_r, after_c) != ".":
                return False

        return True

    def _neighbors(self, row, col):
        return [
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ]

    # ------------------------------------------------------------
    # RACK HANDLING
    # ------------------------------------------------------------

    def _use_rack(self, word, new_positions, rack):
        """
        Determine whether the new letters can be supplied by the rack.

        '?' represents a blank tile.

        Returns:
            (possible, blank_positions)
        """

        counts = Counter(rack)
        blank_positions = []

        for index, char in enumerate(word):

            row, col = new_positions[index]

            # Existing board tile does not need a rack tile.
            # We represent this with None in new_positions.
            if row is None:
                continue

            if counts[char] > 0:
                counts[char] -= 1

            elif counts["?"] > 0:
                counts["?"] -= 1
                blank_positions.append((row, col))

            else:
                return False, ()

        return True, tuple(blank_positions)

    # ------------------------------------------------------------
    # CROSS WORD GENERATION
    # ------------------------------------------------------------

    def _letter_at(self, board, placed, row, col):
        """
        Return the letter at a position after applying a hypothetical move.
        """

        if (row, col) in placed:
            return placed[(row, col)]

        return board.get(row, col)

    def _get_word_through(
        self,
        board,
        placed,
        row,
        col,
        direction,
    ):
        """
        Get the complete word passing through (row, col).
        """

        dr, dc = DIRECTIONS[direction]

        # Move backwards to the beginning.
        r = row
        c = col

        while True:
            prev_r = r - dr
            prev_c = c - dc

            if not board.inside(prev_r, prev_c):
                break

            if self._letter_at(board, placed, prev_r, prev_c) == ".":
                break

            r = prev_r
            c = prev_c

        # Now move forwards.
        letters = []

        while board.inside(r, c):

            letter = self._letter_at(board, placed, r, c)

            if letter == ".":
                break

            letters.append(letter)

            r += dr
            c += dc

        return "".join(letters)

    # ------------------------------------------------------------
    # LEGALITY
    # ------------------------------------------------------------

    def _check_move(
        self,
        board,
        word,
        row,
        col,
        direction,
        rack,
    ):
        """
        Check whether a word can legally be placed.

        Returns information needed for scoring if legal.
        """

        cells = self._placement_cells(
            word,
            row,
            col,
            direction,
        )

        if cells is None:
            return None

        # --------------------------------------------------------
        # Check board collisions
        # --------------------------------------------------------

        new_positions = []
        placed = {}

        overlaps_existing = False

        for i, (r, c) in enumerate(cells):

            board_letter = board.get(r, c)

            if board_letter == ".":

                new_positions.append((r, c))

                placed[(r, c)] = word[i]

            else:

                # We may overlap an existing identical letter.
                if board_letter != word[i]:
                    return None

                overlaps_existing = True

                # None means this letter doesn't consume a rack tile.
                new_positions.append((None, None))

        # We must actually place at least one tile.
        if not new_positions:
            return None

        tiles_used = len(
            [p for p in new_positions if p != (None, None)]
        )

        if tiles_used == 0:
            return None

        # --------------------------------------------------------
        # Word boundaries
        # --------------------------------------------------------

        if not self._before_after_are_empty(
            board,
            row,
            col,
            direction,
            len(word),
        ):
            return None

        # --------------------------------------------------------
        # Rack check
        # --------------------------------------------------------

        possible, blanks = self._use_rack(
            word,
            new_positions,
            rack,
        )

        if not possible:
            return None

        # --------------------------------------------------------
        # Connectivity
        # --------------------------------------------------------

        if board.is_empty():

            # First word must cover the center square.
            if CENTER not in cells:
                return None

        else:

            connected = overlaps_existing

            # A word can also connect by touching an existing word.
            if not connected:

                for r, c in cells:

                    if board.get(r, c) != ".":
                        connected = True
                        break

                    for nr, nc in self._neighbors(r, c):

                        if board.inside(nr, nc):
                            if board.get(nr, nc) != ".":
                                connected = True
                                break

                    if connected:
                        break

            if not connected:
                return None

        # --------------------------------------------------------
        # Check all cross words.
        # --------------------------------------------------------

        perpendicular = "V" if direction == "H" else "H"

        cross_words = []

        for i, (r, c) in enumerate(cells):

            # Existing tile does not create a new cross word.
            if (r, c) not in placed:
                continue

            cross_word = self._get_word_through(
                board,
                placed,
                r,
                c,
                perpendicular,
            )

            if len(cross_word) > 1:

                if cross_word not in self.dictionary:
                    return None

                cross_words.append(
                    ((r, c), cross_word)
                )

        return {
            "placed": placed,
            "blanks": blanks,
            "tiles_used": tiles_used,
            "cross_words": cross_words,
        }

    # ------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------

    def _letter_score(self, letter, is_blank=False):
        if is_blank:
            return 0

        return LETTER_VALUES[letter]

    def _score_main_word(
        self,
        board,
        word,
        cells,
        placed,
        blank_positions,
    ):
        score = 0
        word_multiplier = 1

        blank_positions = set(blank_positions)

        for i, (r, c) in enumerate(cells):

            letter = word[i]

            is_new = (r, c) in placed

            is_blank = (r, c) in blank_positions

            value = self._letter_score(
                letter,
                is_blank,
            )

            if is_new:

                premium = board.premium(r, c)

                if premium == "DL":
                    value *= 2

                elif premium == "TL":
                    value *= 3

                elif premium == "DW":
                    word_multiplier *= 2

                elif premium == "TW":
                    word_multiplier *= 3

            score += value

        return score * word_multiplier

    def _score_cross_word(
        self,
        board,
        cross_word,
        start,
        direction,
        placed,
        blank_positions,
    ):
        """
        Score a cross-word.

        Premium squares only apply to newly placed tiles.
        """

        dr, dc = DIRECTIONS[direction]

        r, c = start

        # Find beginning of cross-word.
        while True:

            nr = r - dr
            nc = c - dc

            if not board.inside(nr, nc):
                break

            if self._letter_at(
                board,
                placed,
                nr,
                nc,
            ) == ".":
                break

            r, c = nr, nc

        score = 0
        word_multiplier = 1

        blank_positions = set(blank_positions)

        for letter in cross_word:

            is_new = (r, c) in placed

            is_blank = (r, c) in blank_positions

            value = self._letter_score(
                letter,
                is_blank,
            )

            if is_new:

                premium = board.premium(r, c)

                if premium == "DL":
                    value *= 2

                elif premium == "TL":
                    value *= 3

                elif premium == "DW":
                    word_multiplier *= 2

                elif premium == "TW":
                    word_multiplier *= 3

            score += value

            r += dr
            c += dc

        return score * word_multiplier

    def _calculate_score(
        self,
        board,
        word,
        row,
        col,
        direction,
        move_info,
    ):
        cells = self._placement_cells(
            word,
            row,
            col,
            direction,
        )

        placed = move_info["placed"]
        blanks = move_info["blanks"]

        score = self._score_main_word(
            board,
            word,
            cells,
            placed,
            blanks,
        )

        perpendicular = "V" if direction == "H" else "H"

        for position, cross_word in move_info["cross_words"]:

            cross_score = self._score_cross_word(
                board,
                cross_word,
                position,
                perpendicular,
                placed,
                blanks,
            )

            score += cross_score

        # Standard Scrabble bingo.
        if move_info["tiles_used"] == 7:
            score += 50

        return score

    # ------------------------------------------------------------
    # CANDIDATE FILTER
    # ------------------------------------------------------------

    def _word_can_use_available_tiles(
        self,
        word,
        board,
        rack,
    ):
        """
        Fast preliminary filter.

        A word can only contain letters available somewhere
        in the rack or already on the board.

        This does NOT prove that the word is playable.
        It only eliminates impossible words early.
        """

        available = Counter(rack)

        for letter, count in board.letter_count().items():
            available[letter] += count

        blanks = available["?"]

        for letter, required in Counter(word).items():

            available_count = available[letter]

            if required <= available_count:
                continue

            missing = required - available_count

            if missing > blanks:
                return False

            blanks -= missing

        return True

    # ------------------------------------------------------------
    # MOVE GENERATION
    # ------------------------------------------------------------

    def _anchors(self, board):
        """
        Find squares that could connect a new word to the board.

        An anchor is either:
        - an occupied square, or
        - an empty square next to an occupied square.
        """

        anchors = set()

        for r in range(SIZE):
            for c in range(SIZE):

                if board.get(r, c) != ".":
                    anchors.add((r, c))

                    for nr, nc in self._neighbors(r, c):

                        if board.inside(nr, nc):
                            if board.get(nr, nc) == ".":
                                anchors.add((nr, nc))

        return anchors

    def _possible_starts(
        self,
        board,
        word_length,
        direction,
    ):
        """
        Produce possible starting positions.

        This avoids checking impossible locations.
        """

        if board.is_empty():

            # Opening move must cover center.
            if direction == "H":

                min_col = max(
                    0,
                    CENTER[1] - word_length + 1
                )

                max_col = min(
                    CENTER[1],
                    SIZE - word_length
                )

                for col in range(min_col, max_col + 1):
                    yield CENTER[0], col

            else:

                min_row = max(
                    0,
                    CENTER[0] - word_length + 1
                )

                max_row = min(
                    CENTER[0],
                    SIZE - word_length
                )

                for row in range(min_row, max_row + 1):
                    yield row, CENTER[1]

            return

        anchors = self._anchors(board)

        if direction == "H":

            for row in range(SIZE):

                for col in range(
                    0,
                    SIZE - word_length + 1
                ):

                    cells = {
                        (row, col + i)
                        for i in range(word_length)
                    }

                    if cells & anchors:
                        yield row, col

        else:

            for row in range(
                0,
                SIZE - word_length + 1
            ):

                for col in range(SIZE):

                    cells = {
                        (row + i, col)
                        for i in range(word_length)
                    }

                    if cells & anchors:
                        yield row, col

    def _cross_check(self, board, row, col, direction):
        """Return letters that make a legal perpendicular word at a square.

        ``None`` means that the square has no perpendicular neighbours, so
        every letter remains possible.  The result is used during trie
        traversal, before a complete candidate has been constructed.
        """

        dr, dc = DIRECTIONS[direction]
        before = []
        after = []

        r, c = row - dr, col - dc
        while board.inside(r, c) and board.get(r, c) != ".":
            before.append(board.get(r, c))
            r, c = r - dr, c - dc

        r, c = row + dr, col + dc
        while board.inside(r, c) and board.get(r, c) != ".":
            after.append(board.get(r, c))
            r, c = r + dr, c + dc

        if not before and not after:
            return None

        prefix = "".join(reversed(before))
        suffix = "".join(after)

        return {
            letter for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if prefix + letter + suffix in self.dictionary
        }

    def _candidate_starts(self, board, direction):
        """Yield starts whose preceding main-word square is empty.

        A legal word cannot have a tile immediately before it.  Starting only
        at these cells gives each possible placement one canonical traversal.
        """

        dr, dc = DIRECTIONS[direction]

        if board.is_empty():
            if direction == "H":
                for col in range(CENTER[1] + 1):
                    yield CENTER[0], col
            else:
                for row in range(CENTER[0] + 1):
                    yield row, CENTER[1]
            return

        for row in range(SIZE):
            for col in range(SIZE):
                previous_row = row - dr
                previous_col = col - dc

                if (not board.inside(previous_row, previous_col)
                        or board.get(previous_row, previous_col) == "."):
                    yield row, col

    def _trie_candidates(self, board, row, col, direction, rack, anchors,
                         cross_checks):
        """Generate dictionary words that can follow one start position.

        Existing board letters are forced trie edges; new letters must come
        from the rack (or a blank) and satisfy their perpendicular cross-check.
        """

        dr, dc = DIRECTIONS[direction]
        rack_counts = Counter(rack)
        letters = []

        def visit(node, r, c, new_tiles, touches_anchor):
            # A terminal trie node is a potential word end.  _check_move still
            # performs the authoritative legality and scoring checks.
            if (None in node and new_tiles and touches_anchor
                    and len(letters) >= 2):
                yield "".join(letters)

            if not board.inside(r, c) or len(letters) == SIZE:
                return

            board_letter = board.get(r, c)

            if board_letter != ".":
                child = node.get(board_letter)
                if child is None:
                    return

                letters.append(board_letter)
                yield from visit(child, r + dr, c + dc, new_tiles,
                                 touches_anchor or (r, c) in anchors)
                letters.pop()
                return

            allowed = cross_checks.get((r, c))

            for letter, child in node.items():
                if letter is None or (allowed is not None and letter not in allowed):
                    continue

                if rack_counts[letter] > 0:
                    rack_counts[letter] -= 1
                    letters.append(letter)
                    yield from visit(child, r + dr, c + dc, new_tiles + 1,
                                     touches_anchor or (r, c) in anchors)
                    letters.pop()
                    rack_counts[letter] += 1
                elif rack_counts["?"] > 0:
                    rack_counts["?"] -= 1
                    letters.append(letter)
                    yield from visit(child, r + dr, c + dc, new_tiles + 1,
                                     touches_anchor or (r, c) in anchors)
                    letters.pop()
                    rack_counts["?"] += 1

        yield from visit(self.dictionary.trie, row, col, 0, False)

    # ------------------------------------------------------------
    # PUBLIC SOLVER
    # ------------------------------------------------------------

    def _hash_map_moves(self, board, rack):
        """Find moves using the basic length-to-words hash-map index.

        This is deliberately straightforward: get a word bucket in O(1),
        apply the inexpensive tile filter, then use the normal placement and
        scoring code.  ``find_moves`` defaults to the trie strategy, which is
        faster for a full CSW dictionary.
        """

        moves = []

        for word_length, words in self.dictionary.words_by_length.items():
            if word_length > SIZE:
                continue

            for word in words:
                if not self._word_can_use_available_tiles(word, board, rack):
                    continue

                for direction in ("H", "V"):
                    for row, col in self._possible_starts(
                        board, word_length, direction
                    ):
                        info = self._check_move(
                            board, word, row, col, direction, rack
                        )

                        if info is None:
                            continue

                        score = self._calculate_score(
                            board, word, row, col, direction, info
                        )

                        moves.append(Move(
                            word=word,
                            row=row,
                            col=col,
                            direction=direction,
                            score=score,
                            tiles_used=info["tiles_used"],
                            blanks=info["blanks"],
                        ))

        return moves

    def find_moves(
        self,
        board,
        rack,
        top_n=20,
        algorithm="trie",
    ):
        """
        Find the highest-scoring legal moves.

        ``algorithm`` can be ``"trie"`` (the default) or ``"hash_map"``.
        """

        rack = rack.upper().replace(" ", "")

        if len(rack) > 7:
            raise ValueError("Rack cannot contain more than 7 tiles.")

        if algorithm == "hash_map":
            moves = self._hash_map_moves(board, rack)
        elif algorithm == "trie":
            moves = []
            anchors = self._anchors(board) if not board.is_empty() else {CENTER}

            # Cache cross-checks once per direction.  A cross-check turns a
            # potentially expensive completed-move rejection into a single
            # trie branch decision.
            cross_checks = {}

            for direction in ("H", "V"):
                perpendicular = "V" if direction == "H" else "H"

                for row in range(SIZE):
                    for col in range(SIZE):
                        if board.get(row, col) == ".":
                            cross_checks[(row, col)] = self._cross_check(
                                board, row, col, perpendicular
                            )

                for row, col in self._candidate_starts(board, direction):
                    for word in self._trie_candidates(
                        board, row, col, direction, rack, anchors, cross_checks
                    ):
                        info = self._check_move(
                            board, word, row, col, direction, rack
                        )

                        if info is None:
                            continue

                        score = self._calculate_score(
                            board, word, row, col, direction, info
                        )

                        moves.append(Move(
                            word=word,
                            row=row,
                            col=col,
                            direction=direction,
                            score=score,
                            tiles_used=info["tiles_used"],
                            blanks=info["blanks"],
                        ))
        else:
            raise ValueError("algorithm must be 'trie' or 'hash_map'.")

        # Sort highest score first.
        moves.sort(
            key=lambda move: (
                -move.score,
                -move.tiles_used,
                move.word,
            )
        )

        return moves[:top_n]

    def best_move(self, board, rack, algorithm="trie"):
        moves = self.find_moves(
            board,
            rack,
            top_n=1,
            algorithm=algorithm,
        )

        if not moves:
            return None

        return moves[0]
