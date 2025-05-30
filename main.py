from typing import List, Tuple
import os

# =========================
# ======= Constants =======
# =========================
BRICK_FULL = 210
BRICK_HALF = 100
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
    def __init__(self, is_half: bool = False):
        """
        Initialize a Brick.
        :param is_half: Boolean flag indicating if the brick is a half brick.
        """
        self.length = BRICK_HALF if is_half else BRICK_FULL
        self.is_half = is_half
        self.stride = -1
        self.built = False               

    def __repr__(self):
        """
        Return visual character based on build state.
        :return: ▓ if built, ░ if not built.
        """
        return BUILT if self.built else UNBUILT   
    
# =========================
# ====== Wall Class =======
# =========================

class Wall:
    def __init__(self):
        """
        Initialize the wall with stretcher bond, stride assignments, and build plan.
        """
        self.rows: List[List[Brick]] = self.generate_stretcher_bond()
        self.assign_strides()
        self.brick_order: List[Tuple[int, int]] = self.optimized_order()
        self.build_index = 0
        # self.rows.reverse()

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
        Print the current state of the wall to the console.
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nWall Build State (Stride ID shown as subscript):\n")
        for row in reversed(self.rows):
            line = ""
            for brick in row:
                char = repr(brick)
                stride_label = str(brick.stride % 10)
                line += char * (4 if not brick.is_half else 2) + stride_label
            print(line)

    def build_next(self):
        """
        Mark the next brick in the build order as built.
        :return: True if a brick was built, False if all are built.
        """
        if self.build_index < len(self.brick_order):
            i, j = self.brick_order[self.build_index]
            self.rows[i][j].built = True
            self.build_index += 1
            return True
        return False

# ==================================
# ======== Run the Simulator =======
# ==================================

if __name__ == "__main__":

    wall = Wall()
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

  
