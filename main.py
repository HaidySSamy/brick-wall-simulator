from typing import List, Tuple
import random

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

MAX_ATTEMPTS = 50
MAX_STAGGER_CHAIN = 6
BRICK_HEIGHT = 50

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
        def build_row(y_index: int, prev_row: List[Brick], prev_pos: List[int], left: int, right: int) -> Tuple[List[Brick], List[int], set]:
            row = []
            joints = set()
            positions = []
            x = left + random.randint(0, BRICK_FULL // 2)
            last_half = False

            while x + BRICK_HALF <= right:
                is_half = random.random() < 0.3
                if last_half:
                    is_half = False

                brick_len = BRICK_HALF if is_half else BRICK_FULL
                end_x = x + brick_len

                if y_index > 0:
                    supported = False
                    for k, below in enumerate(prev_row):
                        below_x = prev_pos[k]
                        below_end = below_x + below.length
                        if not (end_x <= below_x or x >= below_end):
                            supported = True
                            break
                    if not supported:
                        x += HEAD_JOINT
                        continue

                row.append(Brick(is_half=is_half))
                positions.append(x)
                joints.add(end_x)
                x = end_x + HEAD_JOINT
                last_half = is_half

            return row, positions, joints

        rows: List[List[Brick]] = [[] for _ in range(int(WALL_HEIGHT // COURSE_HEIGHT))]
        positions_mm: List[List[int]] = [[] for _ in range(int(WALL_HEIGHT // COURSE_HEIGHT))]
        prev_joints: List[set] = [set() for _ in range(int(WALL_HEIGHT // COURSE_HEIGHT))]

        for top in range(0, WALL_HEIGHT, BUILD_HEIGHT):
            for left in range(0, WALL_WIDTH, BUILD_WIDTH):
                h_start = int(top // COURSE_HEIGHT)
                h_end = min(int((top + BUILD_HEIGHT) // COURSE_HEIGHT), len(rows))

                for y_index in range(h_start, h_end):
                    for _ in range(MAX_ATTEMPTS):
                        prev_row = rows[y_index - 1] if y_index > 0 else []
                        prev_pos = positions_mm[y_index - 1] if y_index > 0 else []
                        row, positions, joints = build_row(y_index, prev_row, prev_pos, left, left + BUILD_WIDTH)
                        if joints & prev_joints[y_index]:
                            continue

                        rows[y_index].extend(row)
                        positions_mm[y_index].extend(positions)
                        prev_joints[y_index] |= joints
                        break

        self.positions_mm = positions_mm
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
        zone_map = {}
        for i, row in enumerate(self.rows):
            for j, brick in enumerate(row):
                zone_map.setdefault(brick.stride, []).append((i, j))
        order = []
        for sid in sorted(zone_map):
            order.extend(sorted(zone_map[sid]))
        return order

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
