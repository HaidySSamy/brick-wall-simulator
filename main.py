import sys
from typing import List, Tuple
import time
import os

# Constants
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

class Brick:
    def __init__(self, is_half: bool = False):
        self.length = BRICK_HALF if is_half else BRICK_FULL
        self.is_half = is_half
        self.stride = -1
        self.built = False               

    def __repr__(self):
        return BUILT if self.built else UNBUILT   
    

class Wall:
    def __init__(self):
        self.rows: List[List[Brick]] = self.generate_stretcher_bond()
        self.assign_strides()
        self.brick_order: List[Tuple[int, int]] = self.optimized_order()
        self.build_index = 0
        self.rows.reverse()

    def generate_stretcher_bond(self) -> List[List[Brick]]:
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
        # Partition the wall area into stride-sized blocks
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

    
    def render(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nWall Build State (Stride ID shown as subscript):\n")
        for row in self.rows:
            line = ""
            for brick in row:
                char = repr(brick)
                stride_label = str(brick.stride % 10)
                line += char * (4 if not brick.is_half else 2) + stride_label
                # line += repr(brick) * (4 if not brick.is_half else 2)
            print(line)

    def build_next(self):
        if self.build_index < len(self.brick_order):

            for i in reversed(range(len(self.rows))):
                row = self.rows[i]
                for j, brick in enumerate(row):
                    if not brick.built:
                        brick.built = True
                        return True
        return False
    
    def optimized_order(self) -> List[Tuple[int, int]]:
        stride_map = {}
        for i, row in enumerate(self.rows):
            for j, brick in enumerate(row):
                if brick.stride not in stride_map:
                    stride_map[brick.stride] = []
                stride_map[brick.stride].append((i, j))

        ordered = []
        for stride_id in sorted(stride_map):
            bricks = stride_map[stride_id]
            bricks.sort(key=lambda pos: (-pos[0], pos[1]))
            ordered.extend(bricks)
        return ordered


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

  
