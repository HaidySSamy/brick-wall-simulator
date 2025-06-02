import pygame
import sys
from main import Wall as LogicWall, WALL_WIDTH, WALL_HEIGHT, COURSE_HEIGHT

# Constants
SCALE = 0.2
BRICK_HEIGHT = 50
HEAD_JOINT = 10
BOTTOM_BAR_HEIGHT = 60
BRICK_FULL = 210

SCREEN_WIDTH = int(WALL_WIDTH * SCALE)
SCREEN_HEIGHT = int(WALL_HEIGHT * SCALE + BOTTOM_BAR_HEIGHT)

# Colors
BACKGROUND = (240, 240, 240)
BOTTOM_BAR_COLOR = (220, 220, 220)
GRID = (180, 180, 180)
DESIGN_COLOR = (200, 200, 200)
BUILT_COLOR = (80, 80, 80)
STRIDE_COLORS = [
    (255, 0, 0), (0, 128, 0), (0, 0, 255), (255, 165, 0),
    (128, 0, 128), (0, 206, 209), (210, 105, 30), (189, 183, 107)
]

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Wall Visualizer")
font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 24)
clock = pygame.time.Clock()

class BrickVisual:
    def __init__(self, x, y, w, stride, brick_ref):
        self.x = x
        self.y = y
        self.w = w
        self.stride = stride
        self.ref = brick_ref

    def draw(self, surface):
        h = BRICK_HEIGHT
        y = WALL_HEIGHT - self.y - h
        rect = pygame.Rect(self.x * SCALE, y * SCALE, self.w * SCALE, h * SCALE)

        color = DESIGN_COLOR
        if self.ref.built:
            stride_color = STRIDE_COLORS[self.stride % len(STRIDE_COLORS)]
            is_full_stretcher = self.ref.length == 210 and not self.ref.is_half and not self.ref.is_header
            is_english = getattr(self.ref, "bond_type", "") == "english"
            needs_pale = is_english and is_full_stretcher and not self.ref.back_to_back
            color = tuple((c + 255) // 2 for c in stride_color) if needs_pale else stride_color

        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, GRID, rect, 1)

def convert_logic_wall_to_visual(wall: LogicWall):
    visuals = []
    for i, row in enumerate(wall.rows):
        y = i * COURSE_HEIGHT

        x_offset = 0
        if wall.bond_type == "flemish" and i % 2 == 1:
            x_offset = BRICK_FULL // 4
        elif wall.bond_type == "wild":
            x_offset = (BRICK_FULL // 4) * (i % 4)  # subtle stepping

        for j, brick in enumerate(row):
            x = wall.positions_mm[i][j] + x_offset
            w = brick.length
            visuals.append(BrickVisual(x, y, w, brick.stride, brick))
    return visuals

def draw_bottom_bar(surface, wall):
    pygame.draw.rect(surface, BOTTOM_BAR_COLOR, pygame.Rect(0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH, BOTTOM_BAR_HEIGHT))
    if wall.build_index == len(wall.brick_order):
        bond_text = f"Wall complete: {wall.build_index} bricks in {wall.bond_type.title()} bond"
    else:
        bond_text = f"Bond: {wall.bond_type.title()} | Built: {wall.build_index}/{len(wall.brick_order)}"
    ctrl_text = "Enter: Build next | Space: Change bond"
    surface.blit(font.render(bond_text, True, (0, 0, 0)), (10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 8))
    surface.blit(small_font.render(ctrl_text, True, (50, 50, 50)), (10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 35))

def bond_selection_screen():
    bonds = ["stretcher", "flemish", "english", "wild"]
    buttons = []
    margin = 20
    btn_width = 200
    btn_height = 50
    total_height = len(bonds) * (btn_height + margin) - margin
    start_y = (SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT - total_height) // 2

    for i, bond in enumerate(bonds):
        rect = pygame.Rect((SCREEN_WIDTH - btn_width) // 2, start_y + i * (btn_height + margin), btn_width, btn_height)
        buttons.append((rect, bond))

    while True:
        screen.fill(BACKGROUND)
        title_surf = font.render("Select Bond Type", True, (0, 0, 0))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, start_y - 60))
        screen.blit(title_surf, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, bond in buttons:
                    if rect.collidepoint(event.pos):
                        return bond

        for i, (rect, bond) in enumerate(buttons):
            label = f"{i+1}. {bond.capitalize()}"
            pygame.draw.rect(screen, (180, 180, 180), rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)
            label_surf = small_font.render(label, True, (0, 0, 0))
            label_rect = label_surf.get_rect(center=rect.center)
            screen.blit(label_surf, label_rect)

        pygame.display.flip()
        clock.tick(30)

def main():
    bond = bond_selection_screen()

    # Draw loading screen
    screen.fill(BACKGROUND)
    wait_text = f"Generating {bond.title()} Bond... Please wait"
    loading_surf = font.render(wait_text, True, (0, 0, 0))
    loading_rect = loading_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(loading_surf, loading_rect)
    pygame.display.flip()

    # Actually generate wall (can be slow for wild)
    logic_wall = LogicWall(bond_type=bond)
    brick_visuals = convert_logic_wall_to_visual(logic_wall)

    while True:
        screen.fill(BACKGROUND)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    logic_wall.build_next()
                elif event.key == pygame.K_SPACE:
                    bond = bond_selection_screen()

                    # Loading again
                    screen.fill(BACKGROUND)
                    wait_text = f"Generating {bond.title()} Bond... Please wait"
                    loading_surf = font.render(wait_text, True, (0, 0, 0))
                    loading_rect = loading_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                    screen.blit(loading_surf, loading_rect)
                    pygame.display.flip()

                    logic_wall = LogicWall(bond_type=bond)
                    brick_visuals = convert_logic_wall_to_visual(logic_wall)

        # Draw bricks
        for bv in brick_visuals:
            bv.draw(screen)

        draw_bottom_bar(screen, logic_wall)
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
