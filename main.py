from typing import List, Tuple
import random
import math 

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

# MAX_ATTEMPTS = 50
MAX_STAGGER_CHAIN = 6
BRICK_HEIGHT = 50

def calculate_max_chunk_rows() -> int:
    half_width = BUILD_WIDTH / 2
    vertical_reach = math.sqrt(BUILD_HEIGHT ** 2 - half_width ** 2)
    return max(1, int(vertical_reach // COURSE_HEIGHT))

class Brick:
    def __init__(
        self,
        is_half=False,
        is_header=False,
        back_to_back=False,
        is_quarter=False
    ):
        if is_quarter:
            self.length = BRICK_FULL // 4
        elif is_header:
            self.length = BRICK_HEADER
        elif is_half:
            self.length = BRICK_HALF
        else:
            self.length = BRICK_FULL

        self.is_half = is_half
        self.is_header = is_header
        self.back_to_back = back_to_back
        self.is_quarter = is_quarter
        self.stride = -1
        self.built = False

class Wall:
    def __init__(self, bond_type="stretcher"):
        self.bond_type = bond_type
        self.rows: List[List[Brick]] = self.generate_bond()
        self.positions_mm: List[List[int]] = []

        for row in self.rows:
            x = 0
            row_positions = []
            for brick in row:
                row_positions.append(x)
                x += brick.length + HEAD_JOINT
            self.positions_mm.append(row_positions)

        self.assign_strides()
        self.brick_order: List[Tuple[int, int]] = self.optimized_order()
        self.build_index = 0

        for row in self.rows:
            for brick in row:
                brick.bond_type = self.bond_type


    def generate_bond(self) -> List[List[Brick]]:
        if self.bond_type == "stretcher":
            return self.generate_stretcher_bond()
        elif self.bond_type == "flemish":
            return self.generate_flemish_bond()
        elif self.bond_type == "english":
            return self.generate_english_bond()
        elif self.bond_type == "wild":
            return self.generate_wild_bond()
        else:
            raise ValueError(f"Unsupported bond type: {self.bond_type}")

    
    def generate_stretcher_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            length = 0

            if row_index % 2 == 1:
                if BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_half=True))
                    length += BRICK_HALF + HEAD_JOINT

            while length + BRICK_FULL + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick())
                length += BRICK_FULL + HEAD_JOINT

            # ✅ Only add final half-brick if it + joint fits
            if length + BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick(is_half=True))

            rows.append(row)

        return rows

    
    def generate_flemish_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            length = 0
            toggle = True  # start with full brick
            is_odd = row_index % 2 == 1

            if is_odd:
                # Apply quarter-brick offset visually (half brick in logic)
                if BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_half=True))
                    length += BRICK_HALF + HEAD_JOINT

            while True:
                if toggle:
                    if length + BRICK_FULL + HEAD_JOINT > WALL_WIDTH:
                        break
                    row.append(Brick())
                    length += BRICK_FULL + HEAD_JOINT
                else:
                    if length + BRICK_HALF + HEAD_JOINT > WALL_WIDTH:
                        break
                    row.append(Brick(is_half=True))
                    length += BRICK_HALF + HEAD_JOINT
                toggle = not toggle

            rows.append(row)

        return rows


    def generate_english_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            length = 0
            is_header_row = row_index % 2 == 1

            if is_header_row:
                # Try queen closer
                qlen = BRICK_FULL // 4 + HEAD_JOINT
                if length + qlen <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_quarter=True))
                    length += qlen

                # Try half header
                hhalf_len = BRICK_HEADER // 2 + HEAD_JOINT
                if length + hhalf_len <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_half=True))
                    length += hhalf_len

                # Add full headers
                while length + BRICK_HEADER + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_header=True))
                    length += BRICK_HEADER + HEAD_JOINT

            else:
                # Full stretchers
                while length + BRICK_FULL + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick())
                    length += BRICK_FULL + HEAD_JOINT

                # Final half stretcher if fits
                if length + BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_half=True))

            rows.append(row)

        return rows
    
    def generate_wild_bond(self) -> List[List[Brick]]:
        def has_stagger_chain(curr: set, prev: set) -> bool:
            chain = 0
            for x in sorted(curr):
                if any(abs(x - y) in {BRICK_FULL, BRICK_HALF} for y in prev):
                    chain += 1
                    if chain > 6:
                        return True
                else:
                    chain = 0
            return False

        def has_adjacent_halves(row) -> bool:
            for i in range(len(row) - 1):
                if row[i].is_half and row[i + 1].is_half:
                    return True
            return False

        rows = []
        prev_joints = set()
        y = 0
        row_num = 0

        while y + COURSE_HEIGHT <= WALL_HEIGHT:
            print(f"--- Building row {row_num} at height y={y} ---")
            for attempt in range(1000):
                print(f"Attempt #{attempt + 1} to build row {row_num}")
                x = 0
                row = []
                joints = set()
                last_half = False

                retry_strategy = attempt % 3
                if retry_strategy == 1:
                    x += BRICK_HALF // 2
                    print("→ Shifted start by quarter brick")
                elif retry_strategy == 2:
                    print("→ Flipping brick bias toward full bricks")

                while x + BRICK_HALF <= WALL_WIDTH:
                    remaining = WALL_WIDTH - x
                    if retry_strategy == 2:
                        is_half = random.choices([True, False], weights=[1, 3])[0]
                    else:
                        is_half = random.choice([True, False])

                    if last_half:
                        is_half = False

                    brick_len = BRICK_HALF if is_half else BRICK_FULL
                    if x + brick_len > WALL_WIDTH:
                        break

                    row.append(Brick(is_half=is_half))
                    x += brick_len + HEAD_JOINT
                    joints.add(x)
                    last_half = is_half

                if joints & prev_joints:
                    print("❌ Overlapping vertical joints")
                    continue
                if has_stagger_chain(joints, prev_joints):
                    print("❌ Exceeded stagger chain")
                    continue
                if has_adjacent_halves(row):
                    print("❌ Adjacent half bricks")
                    continue

                print(f"✅ Row {row_num} accepted with {len(row)} bricks.\n")
                rows.append(row)
                prev_joints = joints
                break

            y += COURSE_HEIGHT
            row_num += 1

        return rows



    def assign_strides(self):
        stride_id = 0
        for top in range(0, WALL_HEIGHT, BUILD_HEIGHT):
            for left in range(0, WALL_WIDTH, BUILD_WIDTH):
                h_start = int(top // COURSE_HEIGHT)
                h_end = min(int((top + BUILD_HEIGHT) // COURSE_HEIGHT), len(self.rows))
                for i in range(h_start, h_end):
                    row_x = 0
                    for j, brick in enumerate(self.rows[i]):
                        if left <= row_x < left + BUILD_WIDTH or left < row_x + brick.length <= left + BUILD_WIDTH:
                            brick.stride = stride_id
                        row_x += brick.length + HEAD_JOINT
                stride_id += 1

        if self.bond_type == "english":
            for i in range(1, len(self.rows), 2):
                for j, header in enumerate(self.rows[i]):
                    if not header.is_header:
                        continue
                    l1 = self.positions_mm[i][j]
                    r1 = l1 + header.length
                    for k, below in enumerate(self.rows[i - 1]):
                        l2 = self.positions_mm[i - 1][k]
                        r2 = l2 + below.length
                        if not (r2 <= l1 or l2 >= r1):
                            header.stride = below.stride
                            break

    def optimized_order(self) -> List[Tuple[int, int]]:
        from collections import defaultdict

        stride_map = defaultdict(list)
        for i, row in enumerate(self.rows):
            for j, brick in enumerate(row):
                stride_map[brick.stride].append((i, j))

        new_order = []
        direction = 1  # 1 = left-to-right, -1 = right-to-left
        x_step = int(BUILD_WIDTH)
        x_max = WALL_WIDTH
        y_max = len(self.rows)

        max_chunk_rows = 6  # max rows per chunk to build before shifting horizontally
        x_zones = list(range(0, x_max, x_step))

        # Process from bottom to top
        chunk_ranges = list(range(0, y_max, max_chunk_rows))

        for chunk_start in chunk_ranges:
            chunk_end = min(chunk_start + max_chunk_rows, y_max)

            x_dir_zones = x_zones if direction == 1 else list(reversed(x_zones))

            for x_start in x_dir_zones:
                diagonal_groups = defaultdict(list)

                for i in range(chunk_start, chunk_end):
                    for j, brick in enumerate(self.rows[i]):
                        x = self.positions_mm[i][j]
                        if x_start <= x < x_start + x_step:
                            diag_key = i + (x // 100) if direction == 1 else i - (x // 100)
                            diagonal_groups[diag_key].append((i, j))

                # sort diagonals from bottom to top
                for level in sorted(diagonal_groups):
                    layer = diagonal_groups[level]
                    sorted_layer = sorted(layer, key=lambda t: t[0], reverse=False)
                    new_order.extend(sorted_layer)

            direction *= -1

        # Post-process: filter out bricks that float
        final_order = []
        built_set = set()

        for i, j in new_order:
            brick = self.rows[i][j]
            x_left = self.positions_mm[i][j]
            x_right = x_left + brick.length

            if i == 0:
                final_order.append((i, j))
                built_set.add((i, j))
                continue

            supported = False
            for k, below_brick in enumerate(self.rows[i - 1]):
                bx = self.positions_mm[i - 1][k]
                br = bx + below_brick.length
                if max(bx, x_left) < min(br, x_right):
                    if (i - 1, k) in built_set:
                        supported = True
                        break

            if supported:
                final_order.append((i, j))
                built_set.add((i, j))

        return final_order



    def build_next(self) -> bool:
        if self.build_index >= len(self.brick_order):
            return False

        i, j = self.brick_order[self.build_index]
        brick = self.rows[i][j]
        is_english = self.bond_type == "english"
        is_stretcher = (i % 2 == 0)

        if not brick.built:
            brick.built = True
            if not is_english or not is_stretcher:
                self.build_index += 1
        elif is_english and is_stretcher and not brick.back_to_back:
            brick.back_to_back = True
            self.build_index += 1
        else:
            self.build_index += 1
        return True
