from typing import List, Tuple
import random

BRICK_FULL    = 210    # mm
BRICK_HALF    = 100    # mm
BRICK_HEADER  = 100    # mm
HEAD_JOINT    = 10     # mm between bricks in the same row
COURSE_HEIGHT = 62.5   # mm (brick height + bed joint)

WALL_WIDTH    = 2300   # mm total wall width
WALL_HEIGHT   = 2000   # mm total wall height

BUILD_WIDTH   = 800    # mm robot stride width
BUILD_HEIGHT  = 1300   # mm robot stride height

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
        self.stride = -1       # set later in assign_strides()
        self.built = False     # toggled during build order
        self.bond_type = ""
        self.parents: List['Brick'] = []


class Wall:
    def __init__(self, bond_type="stretcher"):
        self.bond_type = bond_type
        self.rows: List[List[Brick]] = self.generate_bond()
        self.positions_mm: List[List[int]] = []

        # record x‐positions of each brick
        for row in self.rows:
            x = 0
            row_positions = []
            for brick in row:
                row_positions.append(x)
                x += brick.length + HEAD_JOINT
            self.positions_mm.append(row_positions)

        self.assign_strides()                     # color zones
        self.brick_order: List[Tuple[int, int]] = []
        self._compute_min_movement_build_order()  # marks .built=True temporarily
        # reset built flags
        for r in self.rows:
            for brick in r:
                brick.built = False
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
            length_acc = 0
            # half‐brick offset on odd rows
            if row_index % 2 == 1 and BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick(is_half=True))
                length_acc += BRICK_HALF + HEAD_JOINT

            while length_acc + BRICK_FULL + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick())
                length_acc += BRICK_FULL + HEAD_JOINT

            if length_acc + BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick(is_half=True))

            rows.append(row)

        return rows

    def generate_flemish_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            length_acc = 0
            toggle = True
            is_odd = (row_index % 2 == 1)

            if is_odd and BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                row.append(Brick(is_half=True))
                length_acc += BRICK_HALF + HEAD_JOINT

            while True:
                if toggle:
                    if length_acc + BRICK_FULL + HEAD_JOINT > WALL_WIDTH:
                        break
                    row.append(Brick())
                    length_acc += BRICK_FULL + HEAD_JOINT
                else:
                    if length_acc + BRICK_HALF + HEAD_JOINT > WALL_WIDTH:
                        break
                    row.append(Brick(is_half=True))
                    length_acc += BRICK_HALF + HEAD_JOINT
                toggle = not toggle

            rows.append(row)

        return rows

    def generate_english_bond(self) -> List[List[Brick]]:
        rows: List[List[Brick]] = []
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        for row_index in range(num_courses):
            row: List[Brick] = []
            length_acc = 0
            is_header_row = (row_index % 2 == 1)

            if is_header_row:
                # queen closer (¼‐brick) + joint
                qlen = BRICK_FULL // 4 + HEAD_JOINT
                if length_acc + qlen <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_quarter=True))
                    length_acc += qlen
                # half header + joint
                hhalf_len = BRICK_HEADER // 2 + HEAD_JOINT
                if length_acc + hhalf_len <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_half=True))
                    length_acc += hhalf_len
                # rest are headers
                while length_acc + BRICK_HEADER + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_header=True))
                    length_acc += BRICK_HEADER + HEAD_JOINT
            else:
                # full stretchers
                while length_acc + BRICK_FULL + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick())
                    length_acc += BRICK_FULL + HEAD_JOINT
                if length_acc + BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_half=True))

            rows.append(row)

        return rows

    def generate_wild_bond(self) -> List[List[Brick]]:
        def has_stagger_chain(curr_joints: set, prev_joints: set) -> bool:
            chain = 0
            for pos in sorted(curr_joints):
                if any(abs(pos - p) in {BRICK_FULL, BRICK_HALF} for p in prev_joints):
                    chain += 1
                    if chain > MAX_STAGGER_CHAIN:
                        return True
                else:
                    chain = 0
            return False

        def has_adjacent_halves(row_list: List[Brick]) -> bool:
            for idx in range(len(row_list) - 1):
                if row_list[idx].is_half and row_list[idx + 1].is_half:
                    return True
            return False

        rows: List[List[Brick]] = []
        prev_joints: set = set()
        num_courses = int(WALL_HEIGHT // COURSE_HEIGHT)

        target_width = WALL_WIDTH + BRICK_FULL + HEAD_JOINT  # 2520
        to_remove = BRICK_FULL + HEAD_JOINT                  # 220

        for row_num in range(num_courses):
            attempts = 0
            while True:
                attempts += 1
                x_offset = (BRICK_FULL // 4) * (row_num % 4)
                x = x_offset
                row_bricks: List[Brick] = []
                curr_joints: set = set()
                last_half = False

                # prepend quarter‐bricks
                num_quarters = x_offset // (BRICK_FULL // 4)
                for _ in range(num_quarters):
                    row_bricks.append(Brick(is_quarter=True))

                # place random half/full bricks
                while x + BRICK_HALF <= target_width:
                    is_half = random.choice([True, False])
                    if last_half:
                        is_half = False
                    brick_len = BRICK_HALF if is_half else BRICK_FULL
                    if x + brick_len > target_width:
                        break
                    row_bricks.append(Brick(is_half=is_half))
                    x += brick_len + HEAD_JOINT
                    curr_joints.add(x)
                    last_half = is_half

                # check constraints
                if (
                    has_adjacent_halves(row_bricks)
                    or has_stagger_chain(curr_joints, prev_joints)
                    or (curr_joints & prev_joints)
                ):
                    if attempts >= 1000:
                        raise RuntimeError(f"Cannot generate wild row {row_num} after 1000 tries")
                    continue

                # place one final brick if enough gap
                used_width = x - HEAD_JOINT
                gap = target_width - used_width
                if gap >= BRICK_FULL:
                    row_bricks.append(Brick(is_half=False))
                    x += BRICK_FULL + HEAD_JOINT
                    curr_joints.add(x)
                elif gap >= BRICK_HALF:
                    row_bricks.append(Brick(is_half=True))
                    x += BRICK_HALF + HEAD_JOINT
                    curr_joints.add(x)
                # else leave blank

                prev_joints = curr_joints
                break

            # crop 220 mm from left
            remaining_to_remove = to_remove
            new_row: List[Brick] = []
            i_br = 0
            while i_br < len(row_bricks) and remaining_to_remove > 0:
                brick = row_bricks[i_br]
                span = brick.length + HEAD_JOINT
                if remaining_to_remove >= span:
                    remaining_to_remove -= span
                    i_br += 1
                    continue
                else:
                    if remaining_to_remove < brick.length:
                        brick.length -= remaining_to_remove
                        remaining_to_remove = 0
                        new_row.append(brick)
                        i_br += 1
                        break
                    else:
                        remaining_to_remove -= brick.length
                        if remaining_to_remove >= HEAD_JOINT:
                            remaining_to_remove -= HEAD_JOINT
                            i_br += 1
                            continue
                        else:
                            remaining_to_remove = 0
                            i_br += 1
                            break

            for j in range(i_br, len(row_bricks)):
                new_row.append(row_bricks[j])

            rows.append(new_row)

        return rows

    def assign_strides(self):
        """
        Assign each brick to a 'stride' (color zone) if it overlaps that zone.
        """
        stride_id = 0
        for top in range(0, WALL_HEIGHT, BUILD_HEIGHT):
            for left in range(0, WALL_WIDTH, BUILD_WIDTH):
                h_start = int(top // COURSE_HEIGHT)
                h_end   = min(int((top + BUILD_HEIGHT) // COURSE_HEIGHT), len(self.rows))
                for i in range(h_start, h_end):
                    row_x = 0
                    for j, brick in enumerate(self.rows[i]):
                        brick_left  = row_x
                        brick_right = row_x + brick.length
                        zone_left   = left
                        zone_right  = left + BUILD_WIDTH
                        if (brick_left < zone_right) and (brick_right > zone_left):
                            brick.stride = stride_id
                        row_x += brick.length + HEAD_JOINT
                stride_id += 1

        # English adjustment: headers get same stride as brick beneath
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

    def _compute_min_movement_build_order(self):
        """
        Build children only after parents, minimizing movement between strides.
        """
        self._link_parents_for_all_bricks()
        all_bricks = [(i, j, brick) for i, row in enumerate(self.rows) for j, brick in enumerate(row)]
        total = len(all_bricks)
        built_set = set()
        build_sequence = []
        stride_id = 0

        X_ANCHORS = [0, 300, 700, 1200, 1500]
        Y_ANCHORS = [0, 700]
        anchor_x = 0
        anchor_y = 0

        while len(built_set) < total:
            buildable = [(i, j, b) for (i, j, b) in all_bricks if (not b.built) and all(p.built for p in b.parents)]
            if not buildable:
                raise RuntimeError("No buildable bricks remain but wall is incomplete.")

            best_cost = None
            best_diag = None
            best_anchor = (0, 0)
            best_item = None

            for (i, j, brick) in buildable:
                # compute offset for Flemish, none for Wild after cropping
                if self.bond_type == "flemish" and (i % 2 == 1):
                    x_offset_i = BRICK_FULL // 4
                else:
                    x_offset_i = 0
                x_mm = self.positions_mm[i][j] + x_offset_i
                y_mm = i * COURSE_HEIGHT
                length_mm = brick.length
                height_mm = BRICK_HEIGHT

                cand_cost = None
                cand_anchor = (0, 0)
                for nax in X_ANCHORS:
                    if not (x_mm >= nax and (x_mm + length_mm) <= nax + BUILD_WIDTH):
                        continue
                    for nay in Y_ANCHORS:
                        if not (y_mm >= nay and (y_mm + height_mm) <= nay + BUILD_HEIGHT):
                            continue
                        dx = abs(nax - anchor_x)
                        dy = abs(nay - anchor_y)
                        cost = dx + dy
                        if cand_cost is None or cost < cand_cost:
                            cand_cost = cost
                            cand_anchor = (nax, nay)
                        if cost == 0:
                            break
                    if cand_cost == 0:
                        break

                if cand_cost is None:
                    nax = min(max(0, x_mm), WALL_WIDTH - BUILD_WIDTH)
                    nay = min(max(0, y_mm), WALL_HEIGHT - BUILD_HEIGHT)
                    dx = abs(nax - anchor_x)
                    dy = abs(nay - anchor_y)
                    cand_cost = dx + dy
                    cand_anchor = (nax, nay)

                diag_key = i + (x_mm / BRICK_FULL)
                if (best_cost is None) or (cand_cost < best_cost) or (cand_cost == best_cost and diag_key < best_diag):
                    best_cost = cand_cost
                    best_diag = diag_key
                    best_anchor = cand_anchor
                    best_item = (i, j, brick)

            bi, bj, chosen = best_item
            if best_cost > 0:
                stride_id += 1
                anchor_x, anchor_y = best_anchor

            chosen.built = True
            chosen.stride = stride_id
            built_set.add(chosen)
            build_sequence.append((bi, bj))

        self.brick_order = build_sequence

    def _link_parents_for_all_bricks(self):
        """
        Determine which bricks in row i−1 overlap each brick in row i.
        """
        n_rows = len(self.rows)
        for i in range(1, n_rows):
            if self.bond_type == "flemish" and (i % 2 == 1):
                x_offset_i = BRICK_FULL // 4
            else:
                x_offset_i = 0
            if self.bond_type == "flemish" and ((i - 1) % 2 == 1):
                x_offset_prev = BRICK_FULL // 4
            else:
                x_offset_prev = 0

            for j, brick in enumerate(self.rows[i]):
                left1 = self.positions_mm[i][j] + x_offset_i
                right1 = left1 + brick.length
                brick.parents = []
                for k, below in enumerate(self.rows[i - 1]):
                    left2 = self.positions_mm[i - 1][k] + x_offset_prev
                    right2 = left2 + below.length
                    if max(left1, left2) < min(right1, right2):
                        brick.parents.append(below)


    def build_next(self) -> bool:
        if self.build_index >= len(self.brick_order):
            return False

        i, j = self.brick_order[self.build_index]
        brick = self.rows[i][j]
        is_english = (self.bond_type == "english")
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
