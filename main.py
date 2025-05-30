import sys
from typing import List
import time

# Constants
BRICK_FULL = 210
BRICK_HALF = 100
HEAD_JOINT = 10
BED_JOINT = 12.5
COURSE_HEIGHT = 62.5

WALL_WIDTH = 2300
WALL_HEIGHT = 2000

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
    
    def render(self):
        for row in self.rows:
            line = ""
            for brick in row:
                line += repr(brick) * (4 if not brick.is_half else 2)
            print(line)

    def build_next(self):
        for i in reversed(range(len(self.rows))):
            row = self.rows[i]
            for j, brick in enumerate(row):
                if not brick.built:
                    brick.built = True
                    return True
        return False

def run_dev_tests():
    print("Running Tests...")

    # Test Brick class
    b = Brick()
    assert b.length == BRICK_FULL
    print(b.is_half)
    assert not b.is_half
    assert repr(b) == UNBUILT
    print(repr(b))
    b.built = True
    assert repr(b) == BUILT
    print(repr(b))

    wall = Wall()
    # assert len(wall.rows) == int(WALL_HEIGHT // COURSE_HEIGHT)
    # print(len(wall.rows))
    # assert all(isinstance(brick, Brick) for row in wall.rows for brick in row)
    # print(wall.generate_stretcher_bond())

    # print(wall.render())

    wall.render()
    print("\nSimulating automatic build without ENTER...\n")
    while wall.build_next():
        time.sleep(0.1)
        wall.render()
    print("✅ Wall fully built!")
    sys.exit(0)

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_dev_tests()
        sys.exit(0)
