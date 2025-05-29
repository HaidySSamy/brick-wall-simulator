import sys

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

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_dev_tests()
        sys.exit(0)
