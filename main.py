from typing import List, Tuple
import os

# =========================
# ======= Constants =======
# =========================
BRICK_FULL = 210
BRICK_HALF = 100
BRICK_HEADER = 100
HEAD_JOINT = 10
BED_JOINT = 12.5
COURSE_HEIGHT = 62.5

WALL_WIDTH = 2300
WALL_HEIGHT = 2000

BUILD_WIDTH = 800     # Robot stride width
BUILD_HEIGHT = 1300    # Robot stride height

# Visuals
UNBUILT = '░'
BUILT = '▓'

# =========================
# ===== Brick Class =======
# =========================

class Brick:
    def __init__(self, is_half: bool = False, is_header: bool = False, back_to_back=False):
        """
        Initialize a Brick.
        :param is_half: Boolean flag indicating if the brick is a half brick.
        """
        self.length = BRICK_HEADER if is_header else (BRICK_HALF if is_half else BRICK_FULL)

        # self.length = BRICK_HALF if is_half else BRICK_FULL
        self.is_half = is_half
        self.is_header = is_header
        self.back_to_back = back_to_back
        self.stride = -1
        self.built = False               

    def __repr__(self):
        """
        Return visual character based on build state.
        :return: ▓ if built, ░ if not built.
        """
        if not self.built:
            return '░'
        return '█' if self.back_to_back else '▓'  # darker if doubled
        # return BUILT if self.built else UNBUILT   
    
# =========================
# ====== Wall Class =======
# =========================

class Wall:
    def __init__(self,bond_type: str = "stretcher"):
        """
        Initialize the wall with stretcher bond, stride assignments, and build plan.
        """
        self.bond_type = bond_type.lower()
        self.rows: List[List[Brick]] = self.generate_bond()
        self.assign_strides()
        self.brick_order: List[Tuple[int, int]] = self.optimized_order()
        self.build_index = 0
        # self.rows.reverse()

    def generate_bond(self) -> List[List[Brick]]:
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
        rows= []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT) 

        for row_index in range(num_courses):
            row = []
            offset = (BRICK_FULL+HEAD_JOINT)//2 if row_index % 2 else 0
            length = 0

            if offset: 
                row.append(Brick(is_half=True))
                length += BRICK_HALF + HEAD_JOINT

            while length + BRICK_FULL <= WALL_WIDTH:
                row.append(Brick())
                length += BRICK_FULL + HEAD_JOINT

            if length < WALL_WIDTH:
                row.append(Brick(is_half=True))

            rows.append(row)

        return rows
    def generate_flemish_bond(self) -> List[List[Brick]]:
        rows = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)
        for row_index in range(num_courses):
            row = []
            length = 0
            even_row = row_index % 2 == 0

            # Offset for odd rows to shift visual mortar joints
            if not even_row:
                row.append(Brick(is_half=True))
                length += BRICK_HALF // 2 + HEAD_JOINT  # Quarter brick offset

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
        rows = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row = []
            is_header_course = row_index % 2 == 1
            length = 0

            if is_header_course:
                # Add half header for staggering
                row.append(Brick(is_header=True, is_half=True))
                length += BRICK_HEADER // 2 + HEAD_JOINT

                while length + BRICK_HEADER + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_header=True))
                    length += BRICK_HEADER + HEAD_JOINT

                remaining = WALL_WIDTH - length
                if remaining >= BRICK_HEADER // 2:
                    row.append(Brick(is_header=True, is_half=True))

            else:  # Stretcher course
                row.append(Brick(is_half=True))  # half stretcher for staggering
                length += BRICK_HALF + HEAD_JOINT

                while length + BRICK_FULL + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick())  # full stretcher
                    length += BRICK_FULL + HEAD_JOINT

                if length < WALL_WIDTH:
                    row.append(Brick(is_half=True))

            rows.append(row)
        return rows


    
    def assign_strides(self):
        """
        Assign each brick a stride ID based on its position in the wall.
        """
        stride_w = BUILD_WIDTH
        stride_h = BUILD_HEIGHT

        stride_id = 0
        for stride_top in range(0, WALL_HEIGHT, stride_h):
            for stride_left in range(0, WALL_WIDTH, stride_w):
                h_start = int(stride_top // COURSE_HEIGHT)
                h_end = min(int((stride_top + stride_h) // COURSE_HEIGHT), len(self.rows))

                for i in range(h_start, h_end):
                    row_len = 0
                    for j, brick in enumerate(self.rows[i]):
                        brick_left = row_len
                        brick_right = row_len + brick.length

                        # Check if this brick overlaps current stride
                        if (brick_left >= stride_left and brick_left < stride_left + stride_w) or \
                           (brick_right > stride_left and brick_right <= stride_left + stride_w):
                            brick.stride = stride_id

                        row_len += brick.length + HEAD_JOINT

                stride_id += 1

    def optimized_order(self) -> List[Tuple[int, int]]:
        """
        Return build order optimized to group bricks by stride.
        :return: A list of (row, col) indices in build order.
        """
        stride_map = {}
        for i, row in enumerate(self.rows):
            for j, brick in enumerate(row):
                if brick.stride not in stride_map:
                    stride_map[brick.stride] = []
                stride_map[brick.stride].append((i, j))

        ordered = []
        for stride_id in sorted(stride_map):
            bricks = stride_map[stride_id]
            bricks.sort(key=lambda pos: (pos[0], pos[1]))
            ordered.extend(bricks)
        return ordered
    
    def render(self):
        """
        Print the current state of the wall to the console, including mortar gaps.
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\nWall Build State [{self.bond_type.title()} Bond] with Mortar:\n")
        print("Legend: ░ = unbuilt, ▓ = built, ' ' = mortar, █ = double stretcher\n")
        max_visual_width = 0
        if self.bond_type == "english":
            for i, row in enumerate(self.rows):
                if i % 2 == 0:  # stretcher row
                    line = ""
                    for j, brick in enumerate(row):
                        if brick is None:
                            line += "  "
                            continue
                        width = 4 if not brick.is_half and not brick.is_header else 2
                        line += "▓" * width
                        if j < len(row) - 1:
                            line += " "
                    max_visual_width = max(max_visual_width, len(line))

        for i, row in enumerate(reversed(self.rows)):
            actual_row_idx = len(self.rows) - 1 - i
            is_header_row = self.bond_type == "english" and actual_row_idx % 2 == 1
            flemish_offset = self.bond_type == "flemish" and actual_row_idx % 2 == 0
            line = "  " if is_header_row or flemish_offset else ""
            visual_len = len(line)  # start from offset


            # if is_header_row or flemish_offset:
            #     line += " " * 2  

            for index, brick in enumerate(row):
                if brick is None:
                    line += "  "
                    visual_len += 2
                    continue

                char = repr(brick)
                width = 4 if not brick.is_half and not brick.is_header else 2
                # line += char * width 
                # line += char * (4 if not brick.is_half else 2) + stride_label
                if is_header_row and self.bond_type == "english":
                    if visual_len + width > max_visual_width:
                        break  # skip bricks that would overflow
                line += char * width
                visual_len += width
                
                # else:
                #     line += char * width

                if index < len(row) - 1:
                    # Add mortar only if brick edge doesn't align with the one above
                    # next_brick = row[index + 1]
                    # if not (brick.length == next_brick.length and brick.is_half == next_brick.is_half and brick.is_header == next_brick.is_header):
                    if is_header_row and self.bond_type == "english" and visual_len + 1 > max_visual_width:
                        break                        
                    line += " " 
                    visual_len += 1

            print(line)
            print()

    def build_next(self):
        """
        Mark the next brick in the build order as built.
        :return: True if a brick was built, False if all are built.
        Builds the next brick in the sequence:
        - English bond: headers build in 1 step, stretchers in 2 steps (▓ → █)
        - Other bonds: all bricks build in 1 step
        """
        if self.build_index < len(self.brick_order):
            i, j = self.brick_order[self.build_index]
            brick = self.rows[i][j]
            # self.build_index += 1
            is_english = self.bond_type == "english"
            is_stretcher_row = is_english and i % 2 == 0
            is_header_row = is_english and i % 2 == 1

            if not brick.built:
                brick.built = True
                if not is_english or is_header_row:
                    self.build_index += 1  # header builds in one step
            elif is_stretcher_row and not brick.back_to_back:
                brick.back_to_back = True
                self.build_index += 1  # now move to next brick
            else:
                self.build_index += 1  # redundant fallback
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

  
