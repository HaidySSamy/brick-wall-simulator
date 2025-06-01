from typing import List, Tuple
import os

# =========================
# ======= Constants =======
# =========================
BRICK_FULL    = 210    # mm
BRICK_HALF    = 100    # mm
BRICK_HEADER  = 100    # mm  (same as half in our ASCII scheme)
HEAD_JOINT    = 10     # mm between bricks in the same row
BED_JOINT     = 12.5   # mm between courses (not directly used for ASCII)
COURSE_HEIGHT = 62.5   # mm (brick height + bed joint)

WALL_WIDTH    = 2300   # mm total wall width
WALL_HEIGHT   = 2000   # mm total wall height

BUILD_WIDTH   = 800    # mm robot stride width
BUILD_HEIGHT  = 1300   # mm robot stride height

# Visuals
UNBUILT = '░'
BUILT   = '▓'


# =========================
# ===== Brick Class =======
# =========================

class Brick:
    def __init__(
        self,
        is_half: bool = False,
        is_header: bool = False,
        back_to_back: bool = False,
        is_quarter: bool = False
    ):
        """
        Initialize a Brick.

        :param is_half:    True if this is a half stretcher (100 mm).
        :param is_header:  True if this is a header brick in an English bond (100 mm).
        :param back_to_back: Only used for full stretchers (210 mm) to indicate second pass.
        :param is_quarter: True if this is a queen‐closer (¼‐brick, ~52.5 mm) in English bond.
        """
        if is_quarter:
            # Queen‐closer: one‐fourth of a full stretcher, ~52.5 mm
            self.length = BRICK_FULL // 4
        elif is_header:
            # Header course bricks are always 100 mm
            self.length = BRICK_HEADER
        elif is_half:
            # Half stretcher: 100 mm
            self.length = BRICK_HALF
        else:
            # Full stretcher: 210 mm
            self.length = BRICK_FULL

        self.is_half      = is_half
        self.is_header    = is_header
        self.back_to_back = back_to_back
        self.is_quarter   = is_quarter
        self.stride       = -1    # Will be assigned later in assign_strides()
        self.built        = False # Set to True on the first pass; if full stretcher, second pass sets back_to_back

    def __repr__(self):
        """
        Return a single‐character representation based on build state:
         - ░ if unbuilt
         - ▒ if built quarter‐brick (queen‐closer)
         - ▓ if built first pass
         - █ if built second pass (only for full stretcher)
        """
        if not self.built:
            return UNBUILT
        if self.is_quarter:
            return '▒'
        return '█' if self.back_to_back else BUILT


# =========================
# ====== Wall Class =======
# =========================

class Wall:
    def __init__(self, bond_type: str = "stretcher"):
        """
        Initialize a Wall object:
         1) Generate the 2D grid of bricks (self.rows) for the chosen bond.
         2) Compute self.positions_mm[i][j] = left‐edge of rows[i][j] in millimeters.
         3) Compute self.positions_ascii[i][j] = left‐column index in the ASCII rendering.
         4) assign_strides() to give each brick a “stride zone” (0,1,2,…) based on 800×1300 mm cells.
         5) Build self.brick_order = a list of (row, col) sorted by ascending stride, then by (row, col).
         6) Set build_index = 0 to track how many build‐actions we’ve executed so far.
        """
        self.bond_type = bond_type.lower()
        self.rows: List[List[Brick]] = self.generate_bond()

        # Compute each brick’s left‐edge in millimeters (for reference).
        self.positions_mm: List[List[int]] = []
        for row in self.rows:
            x_cursor = 0
            row_positions = []
            for brick in row:
                row_positions.append(x_cursor)
                x_cursor += (brick.length + HEAD_JOINT)
            self.positions_mm.append(row_positions)

        # Compute each brick’s left‐column in the ASCII rendering
        self.positions_ascii: List[List[int]] = []
        for row in self.rows:
            xpos = 0
            row_ascii_positions = []
            for brick in row:
                row_ascii_positions.append(xpos)
                if brick.is_quarter:
                    w = 1
                elif (not brick.is_half) and (not brick.is_header):
                    w = 4
                else:
                    w = 2
                xpos += (w + 1)  # +1 for the single‐space mortar gap
            self.positions_ascii.append(row_ascii_positions)

        self.assign_strides()
        self.brick_order: List[Tuple[int, int]] = self.optimized_order()
        self.build_index = 0

    def generate_bond(self) -> List[List[Brick]]:
        """
        Dispatch to the correct bond generator.
        """
        if self.bond_type == "stretcher":
            return self.generate_stretcher_bond()
        elif self.bond_type == "flemish":
            return self.generate_flemish_bond()
        elif self.bond_type == "english":
            return self.generate_english_bond()
        else:
            raise ValueError(f"Unsupported bond type: {self.bond_type}")

    def generate_stretcher_bond(self) -> List[List[Brick]]:
        """
        Generate rows of bricks in stretcher bond pattern.
        :return: A list of brick rows.
        """
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT) 

        for row_index in range(num_courses):
            row: List[Brick] = []
            offset = (BRICK_FULL + HEAD_JOINT)//2 if row_index % 2 else 0
            length = 0

            if offset: 
                row.append(Brick(is_half=True))
                length += BRICK_HALF + HEAD_JOINT

            while length + (BRICK_FULL  + HEAD_JOINT) <= WALL_WIDTH:
                row.append(Brick())
                length += (BRICK_FULL + HEAD_JOINT)

            if length < WALL_WIDTH:
                row.append(Brick(is_half=True))

            rows.append(row)

        return rows
    
    def generate_flemish_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)
        for row_index in range(num_courses):
            row: List[Brick] = []
            length = 0
            even_row = (row_index % 2 == 0)

            # Offset for odd rows to shift visual mortar joints
            if not even_row:
                row.append(Brick(is_half=True))
                length += (BRICK_HALF // 2) + HEAD_JOINT  # Quarter brick offset

            toggle = even_row  # Start with full or half depending on row
            while length < WALL_WIDTH:
                brick = Brick() if toggle else Brick(is_half=True)
                brick_len = brick.length + HEAD_JOINT
                if length + brick_len <= WALL_WIDTH:
                    row.append(brick)
                    length += brick_len
                    toggle = not toggle
                else:
                    break

            if length < WALL_WIDTH:
                row.append(Brick(is_half=True))
            rows.append(row)
        return rows

    def generate_english_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            is_header_course = row_index % 2 == 1
            length = 0

            if is_header_course:
                # Add queen closer (¼-brick) to break vertical alignment
                row.append(Brick(is_header=True, is_quarter=True))
                length += (BRICK_FULL // 4) + HEAD_JOINT
                # Add half header for staggering
                if length + (BRICK_HEADER // 2) + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_half=True))
                    length += (BRICK_HEADER // 2) + HEAD_JOINT

                while (length + BRICK_HEADER + HEAD_JOINT) <= WALL_WIDTH:
                    row.append(Brick(is_header=True))
                    length += BRICK_HEADER + HEAD_JOINT

                remaining = WALL_WIDTH - length
                if remaining >= (BRICK_HEADER // 2):
                    row.append(Brick(is_header=True, is_half=True))

            else:  # Stretcher course

                while length + (BRICK_FULL + HEAD_JOINT) <= WALL_WIDTH:
                    row.append(Brick())  # full stretcher
                    length += (BRICK_FULL + HEAD_JOINT)
                if length < WALL_WIDTH:
                    row.append(Brick(is_half=True))

            rows.append(row)

        return rows
    
    def assign_strides(self):
        """
        Assign each brick.stride based on which BUILD_WIDTH×BUILD_HEIGHT “zone” it overlaps.
        Then, if English bond, force each header’s stride to match the stretcher below.
        """
        stride_id = 0
        for stride_top in range(0, WALL_HEIGHT, BUILD_HEIGHT):
            for stride_left in range(0, WALL_WIDTH, BUILD_WIDTH):
                h_start = int(stride_top // COURSE_HEIGHT)
                h_end = min(int((stride_top + BUILD_HEIGHT) // COURSE_HEIGHT), len(self.rows))

                for i in range(h_start, h_end):
                    row_acc = 0
                    for j, brick in enumerate(self.rows[i]):
                        left_edge  = row_acc
                        right_edge = row_acc + brick.length

                        if (
                            (left_edge >= stride_left and left_edge < stride_left + BUILD_WIDTH)
                            or (right_edge > stride_left and right_edge <= stride_left + BUILD_WIDTH)
                        ):
                            brick.stride = stride_id

                        row_acc += (brick.length + HEAD_JOINT)

                stride_id += 1

        if self.bond_type == "english":
            # Force each header’s stride to match the stretcher directly below it
            for i in range(1, len(self.rows), 2):
                for j, header in enumerate(self.rows[i]):
                    if not header.is_header:
                        continue
                    left_h = self.positions_mm[i][j]
                    right_h = left_h + header.length
                    for k, below in enumerate(self.rows[i - 1]):
                        left_b = self.positions_mm[i - 1][k]
                        right_b = left_b + below.length
                        if not (right_b <= left_h or left_b >= right_h):
                            header.stride = below.stride
                            break

    def optimized_order(self) -> List[Tuple[int, int]]:
        """
        Return a list of (row, col) positions grouped by ascending stride ID,
        then within each stride sorted by (row, col). This is the baseline
        “zone‐by‐zone” build order.
        """
        stride_map = {}
        for i, row in enumerate(self.rows):
            for j, brick in enumerate(row):
                stride_map.setdefault(brick.stride, []).append((i, j))

        ordered: List[Tuple[int, int]] = []
        for sid in sorted(stride_map):
            group = stride_map[sid]
            group.sort(key=lambda pos: (pos[0], pos[1]))
            ordered.extend(group)
        return ordered

    # ====================================
    # === RENDER: ASCII + “zone‐cap”  ===
    # ====================================
    def render(self):
        """
        Print the current state of the wall in ASCII, including mortar gaps.

        Key additions:
         1) We compute `wall_ascii_limit` from the bottom stretcher row (row 0),
            guaranteeing that it represents the full wall width in characters.
         2) Before drawing a header, we check if (left_h_ascii + w) > wall_ascii_limit.
            If so, we clip that header (do not draw it at all).
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\nWall Build State [{self.bond_type.title()} Bond] with Mortar:\n")
        print("Legend: ░ = unbuilt, ▓ = built, ' ' = mortar, █ = double stretcher\n")

        widths_per_row: List[int] = []
        for i, row in enumerate(self.rows):
            total_chars = 0
            for j, brick in enumerate(row):
                if brick.is_quarter:
                    w = 1
                elif (not brick.is_half) and (not brick.is_header):
                    w = 4
                else:
                    w = 2
                total_chars += w
                if j < len(row) - 1:
                    total_chars += 1  # one char for mortar gap
            widths_per_row.append(total_chars)

        bottom_row = self.rows[0]
        limit = 0
        for idx, brick in enumerate(bottom_row):
            if brick.is_quarter:
                w = 1
            elif (not brick.is_half) and (not brick.is_header):
                w = 4
            else:
                w = 2
            limit += w
            if idx < len(bottom_row) - 1:
                limit += 1  # mortar gap
        wall_ascii_limit = limit

        for rev_i, row in enumerate(reversed(self.rows)):
            actual_i = len(self.rows) - 1 - rev_i
            is_header_row = (self.bond_type == "english" and (actual_i % 2 == 1))
            flemish_offset = (self.bond_type == "flemish" and (actual_i % 2 == 0))

            # Flemish bond: indent every even row by 2 spaces
            line = "  " if flemish_offset else ""
            visual_len = len(line)

            if is_header_row:
                # We’ll need to inspect the course directly below
                below_row = self.rows[actual_i - 1]
                below_ascii_positions = self.positions_ascii[actual_i - 1]

            for j, brick in enumerate(row):
                char = repr(brick)
                if brick.is_quarter:
                    w = 1
                elif (not brick.is_half) and (not brick.is_header):
                    w = 4
                else:
                    w = 2

                if is_header_row and brick.is_header:
                    left_h_ascii = self.positions_ascii[actual_i][j]
                    right_h_ascii = left_h_ascii + w

                    # CLIP CHECK: Does this header exceed the right edge of the wall?
                    if right_h_ascii > wall_ascii_limit:
                        # Skip it entirely (clipped)
                        continue

                    #Check support by scanning each brick in the course below:
                    fully_supported = True
                    for k, below in enumerate(below_row):
                        left_b_ascii = below_ascii_positions[k]
                        if below.is_quarter:
                            w_b = 1
                        elif (not below.is_half) and (not below.is_header):
                            w_b = 4
                        else:
                            w_b = 2
                        right_b_ascii = left_b_ascii + w_b

                        # If any below‐brick overlaps [left_h_ascii, right_h_ascii):
                        if not (right_b_ascii <= left_h_ascii or left_b_ascii >= right_h_ascii):
                            # That below brick must be fully built
                            if not below.built:
                                fully_supported = False
                                break
                            # If it’s a full stretcher (210 mm), require back_to_back=True
                            if below.length == BRICK_FULL and not below.back_to_back:
                                fully_supported = False
                                break

                    if not fully_supported:
                        line += UNBUILT * w
                        visual_len += w
                        if j < len(row) - 1:
                            line += " "
                            visual_len += 1
                        continue

                line += char * w
                visual_len += w

                # Mortar gap (space) between bricks
                if j < len(row) - 1:
                    line += " "
                    visual_len += 1

            print(line)
            print()

    # ===============================================
    # ===== End of render() – all else same =====
    # ===============================================

    def build_next(self) -> bool:
        """
        Mark the next action in self.brick_order as built (or second pass).
        Returns True if we placed something, False if all bricks are done.

        - English bond:
            * Header row (odd): single‐pass (built=True → ▓).
            * Stretcher row (even): two passes:
               1) built=True  → ▓
               2) back_to_back=True → █
        - Other bonds:
            Every brick is single‐pass (built=True → ▓).
        """
        if self.build_index < len(self.brick_order):
            i, j = self.brick_order[self.build_index]
            brick = self.rows[i][j]
            is_english = (self.bond_type == "english")
            is_stretcher_row = (is_english and (i % 2 == 0))
            is_header_row    = (is_english and (i % 2 == 1))

            if not brick.built:
                brick.built = True
                if (not is_english) or is_header_row:
                    # Single‐pass for non‐stretcher or header course
                    self.build_index += 1
            elif is_stretcher_row and not brick.back_to_back:
                # Second pass for a full stretcher:
                brick.back_to_back = True
                self.build_index += 1
            else:
                # Already fully built – skip
                self.build_index += 1
            return True

        return False


# ==================================
# ======== Run the Simulator =======
# ==================================

if __name__ == "__main__":
    print("Choose bond type (stretcher, flemish, english):")
    bond = input("> ").strip().lower()
    wall = Wall(bond_type=bond)
    wall.render()
    print("\nPress ENTER to build each brick (Ctrl+C to exit).\n")
    while True:
        try:
            input()
            if not wall.build_next():
                print("Wall complete!")
                break
            wall.render()
        except KeyboardInterrupt:
            break