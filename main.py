from typing import List, Tuple
import random

BRICK_FULL    = 210    # mm
BRICK_HALF    = 100    # mm
BRICK_HEADER  = 100    # mm (same as half)
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
        self.stride = -1       # assigned later in assign_strides()
        self.built = False     # will be toggled when building
        self.bond_type = ""
        self.parents: List['Brick'] = []  # will be set by linking
        self.is_filler = False  # marks the “end‐of‐row filler” bricks in Wild bond


class Wall:
    def __init__(self, bond_type="stretcher"):
        self.bond_type = bond_type

        # 1) Generate bond → self.rows must be a List[List[Brick]]
        self.rows: List[List[Brick]] = self.generate_bond()

        # 2) Build positions_mm[i][j] = x‐coordinate for each brick (no offset yet)
        self.positions_mm: List[List[int]] = []
        for row in self.rows:
            x = 0
            row_positions = []
            for brick in row:
                row_positions.append(x)
                x += brick.length + HEAD_JOINT
            self.positions_mm.append(row_positions)

        # 3) Precompute x‐offset for Flemish: ¼‐brick on odd rows, else 0
        #    (Wild bond has already “cropped” to exactly 2300 mm, so its offset = 0)
        self.row_x_offset = [
            (BRICK_FULL // 4) if (self.bond_type == "flemish" and (i % 2 == 1)) else 0
            for i in range(len(self.rows))
        ]

        # 4) Assign stride IDs (zone coloring)
        self.assign_strides()

        # 5) Precompute “anchor_candidates” so we don’t brute‐force every anchor each time
        self._compute_anchor_candidates()

        # 6) Compute min‐movement build order (this temporarily marks .built = True)
        self.brick_order: List[Tuple[int, int]] = []
        self.compute_min_movement_build_order()

        # 7) Reset all .built flags so the GUI starts un‐built
        for r in self.rows:
            for brick in r:
                brick.built = False
        self.build_index = 0

        # 8) Tag each Brick.bond_type so GUI can do English back‐to‐back logic
        for row in self.rows:
            for brick in row:
                brick.bond_type = self.bond_type

    # ─────────────────────────────────────────────────────
    # 1) Bond‐generation: call the correct method, all must return List[List[Brick]]
    # ─────────────────────────────────────────────────────

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

            if row_index % 2 == 1 and BRICK_HALF + HEAD_JOINT <= WALL_WIDTH:
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
                # quarter “queen closer” + joint
                qlen = BRICK_FULL // 4 + HEAD_JOINT
                if length_acc + qlen <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_quarter=True))
                    length_acc += qlen

                # half header + joint
                hhalf_len = BRICK_HEADER // 2 + HEAD_JOINT
                if length_acc + hhalf_len <= WALL_WIDTH:
                    row.append(Brick(is_header=True, is_half=True))
                    length_acc += hhalf_len

                while length_acc + BRICK_HEADER + HEAD_JOINT <= WALL_WIDTH:
                    row.append(Brick(is_header=True))
                    length_acc += BRICK_HEADER + HEAD_JOINT
            else:
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

        target_width = WALL_WIDTH + BRICK_FULL + HEAD_JOINT  # 2300 + 210 + 10 = 2520
        to_remove = BRICK_FULL + HEAD_JOINT                  # 210 + 10 = 220

        for row_num in range(num_courses):
            attempts = 0

            while True:
                attempts += 1
                # 1) ¼‐brick offset (cycles every 4 rows)
                x_offset = (BRICK_FULL // 4) * (row_num % 4)
                x = x_offset
                row_bricks: List[Brick] = []
                curr_joints: set = set()
                last_half = False

                # Prepend quarter‐brick objects so the row starts at x_offset
                num_quarters = x_offset // (BRICK_FULL // 4)
                for _ in range(num_quarters):
                    row_bricks.append(Brick(is_quarter=True))

                # 2) Randomly place half/full bricks until no more can fit
                while x + BRICK_HALF <= target_width:
                    is_half = random.choice([True, False])
                    if last_half:
                        is_half = False  # never allow two halfs consecutively

                    brick_len = BRICK_HALF if is_half else BRICK_FULL
                    if x + brick_len > target_width:
                        break

                    row_bricks.append(Brick(is_half=is_half))
                    x += brick_len + HEAD_JOINT
                    curr_joints.add(x)
                    last_half = is_half

                # 3) Wild‐bond constraints: no two halfs, no >6 stagger steps, no overlapping joints
                if (
                    has_adjacent_halves(row_bricks)
                    or has_stagger_chain(curr_joints, prev_joints)
                    or (curr_joints & prev_joints)
                ):
                    if attempts >= 1000:
                        raise RuntimeError(f"Unable to generate wild bond row {row_num} after 1000 tries")
                    continue  # retry

                # 4) Determine leftover gap
                used_width = x - HEAD_JOINT
                gap = target_width - used_width

                # 4a) If last original brick is a half, force a full‐brick filler (if gap ≥ 100)
                last_real = row_bricks[-1] if row_bricks else None
                if last_real is not None and last_real.is_half and gap >= BRICK_HALF:
                    filler = Brick(is_half=False)
                    filler.is_filler = True
                    row_bricks.append(filler)
                    x += BRICK_FULL + HEAD_JOINT
                    curr_joints.add(x)

                else:
                    # 4b) Normal filler logic:
                    #     • gap ≥210 → full; 210 > gap ≥100 → half; else none
                    if gap >= BRICK_FULL:
                        filler = Brick(is_half=False)
                        filler.is_filler = True
                        row_bricks.append(filler)
                        x += BRICK_FULL + HEAD_JOINT
                        curr_joints.add(x)

                    elif gap >= BRICK_HALF:
                        filler = Brick(is_half=True)
                        filler.is_filler = True
                        row_bricks.append(filler)
                        x += BRICK_HALF + HEAD_JOINT
                        curr_joints.add(x)
                    # else: gap <100 → leave blank

                prev_joints = curr_joints
                break

            # 5) Crop exactly 220 mm from the left
            remaining_to_remove = to_remove  # 220 mm
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
                    # Cropping happens inside this brick
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

            # 6) Append any remaining bricks beyond cropped portion
            for j in range(i_br, len(row_bricks)):
                new_row.append(row_bricks[j])

            rows.append(new_row)

        return rows

    # ─────────────────────────────────────────────────────
    # 2) assign_strides: use positions_mm directly so no need to recompute row_x
    # ─────────────────────────────────────────────────────

    def assign_strides(self):
        stride_id = 0
        for top in range(0, WALL_HEIGHT, BUILD_HEIGHT):
            for left in range(0, WALL_WIDTH, BUILD_WIDTH):
                h_start = int(top // COURSE_HEIGHT)
                h_end   = min(int((top + BUILD_HEIGHT) // COURSE_HEIGHT), len(self.rows))
                zone_left = left
                zone_right = left + BUILD_WIDTH

                for i in range(h_start, h_end):
                    for j, brick in enumerate(self.rows[i]):
                        brick_left = self.positions_mm[i][j]
                        brick_right = brick_left + brick.length
                        if (brick_left < zone_right) and (brick_right > zone_left):
                            brick.stride = stride_id
                stride_id += 1

        # English‐bond adjustment: headers share stripe with stretcher below
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

    # ─────────────────────────────────────────────────────
    # 3) Precompute per‐brick anchor_candidates to avoid trying all 10 anchors
    # ─────────────────────────────────────────────────────

    def _compute_anchor_candidates(self):
        X_ANCHORS = [0, 300, 700, 1200, 1500]
        Y_ANCHORS = [0, 700]
        self.anchor_candidates = {}

        for i, row in enumerate(self.rows):
            x_offset = self.row_x_offset[i]
            y_mm = i * COURSE_HEIGHT

            for j, brick in enumerate(row):
                base_x = self.positions_mm[i][j] + x_offset
                length_mm = brick.length
                candidates: List[Tuple[int,int]] = []

                for nax in X_ANCHORS:
                    if base_x >= nax and (base_x + length_mm) <= (nax + BUILD_WIDTH):
                        for nay in Y_ANCHORS:
                            if y_mm >= nay and (y_mm + BRICK_HEIGHT) <= (nay + BUILD_HEIGHT):
                                candidates.append((nax, nay))

                self.anchor_candidates[(i, j)] = candidates

    # ─────────────────────────────────────────────────────
    # 4) Min‐Movement Build Order ( “fits in current window” first, so filler can share zone )
    # ─────────────────────────────────────────────────────

    def compute_min_movement_build_order(self):
        self.link_parents_for_all_bricks()

        all_bricks = [(i, j, brick) for i, row in enumerate(self.rows) for j, brick in enumerate(row)]
        total = len(all_bricks)
        built_set = set()
        build_sequence: List[Tuple[int, int]] = []
        stride_id = 0

        X_ANCHORS = [0, 300, 700, 1200, 1500]
        Y_ANCHORS = [0, 700]

        anchor_x = 0
        anchor_y = 0

        while len(built_set) < total:
            # (A) gather all bricks whose parents are already built
            buildable = [
                (i, j, b) for (i, j, b) in all_bricks
                if (not b.built) and all(p.built for p in b.parents)
            ]
            if not buildable:
                raise RuntimeError("No buildable bricks remain but wall is incomplete.")

            best_cost = None
            best_diag = None
            best_anchor = (0, 0)
            best_item = None

            for (i, j, brick) in buildable:
                # compute actual x_mm, y_mm with Flemish offset
                if self.bond_type == "flemish" and (i % 2 == 1):
                    x_offset_i = BRICK_FULL // 4
                else:
                    x_offset_i = 0

                base_x = self.positions_mm[i][j]
                x_mm = base_x + x_offset_i
                y_mm = i * COURSE_HEIGHT
                length_mm = brick.length
                height_mm = BRICK_HEIGHT

                cand_cost = None
                cand_anchor = (anchor_x, anchor_y)

                # (B) If this brick (including fillers) still fits completely inside
                #     [anchor_x .. anchor_x + 800] × [anchor_y .. anchor_y + 1300], cost = 0
                if (x_mm >= anchor_x
                    and (x_mm + length_mm) <= (anchor_x + BUILD_WIDTH)
                    and y_mm >= anchor_y
                    and (y_mm + height_mm) <= (anchor_y + BUILD_HEIGHT)):
                    cand_cost = 0
                    cand_anchor = (anchor_x, anchor_y)
                else:
                    # (C) Otherwise, try each precomputed quantized anchor
                    candidates = self.anchor_candidates.get((i, j), [])
                    for (nax, nay) in candidates:
                        dx = abs(nax - anchor_x)
                        dy = abs(nay - anchor_y)
                        cost = dx + dy
                        if (cand_cost is None) or (cost < cand_cost):
                            cand_cost = cost
                            cand_anchor = (nax, nay)
                        if cost == 0:
                            break

                    # (D) If none of those fit, choose a just‐large‐enough anchor
                    if cand_cost is None:
                        nax = min(max(0, x_mm), WALL_WIDTH - BUILD_WIDTH)
                        nay = min(max(0, y_mm), WALL_HEIGHT - BUILD_HEIGHT)
                        dx = abs(nax - anchor_x)
                        dy = abs(nay - anchor_y)
                        cand_cost = dx + dy
                        cand_anchor = (nax, nay)

                diag_key = i + (x_mm / BRICK_FULL)
                if (best_cost is None) or (cand_cost < best_cost) or (
                   cand_cost == best_cost and diag_key < best_diag):
                    best_cost = cand_cost
                    best_diag = diag_key
                    best_anchor = cand_anchor
                    best_item = (i, j, brick)

            # (E) Select the best brick
            bi, bj, chosen = best_item
            if best_cost > 0:
                stride_id += 1
                anchor_x, anchor_y = best_anchor

            chosen.built = True
            chosen.stride = stride_id
            built_set.add(chosen)
            build_sequence.append((bi, bj))

        self.brick_order = build_sequence

    # ─────────────────────────────────────────────────────
    # 5) Link parents: each brick at (i,j) depends on any overlapping bricks below (i−1)
    #    using the same offset rules. Row 0 has no parents.
    # ─────────────────────────────────────────────────────

    def link_parents_for_all_bricks(self):
        n_rows = len(self.rows)
        for i in range(1, n_rows):
            x_offset_i = (BRICK_FULL // 4) if (self.bond_type == "flemish" and (i % 2 == 1)) else 0
            x_offset_prev = (BRICK_FULL // 4) if (self.bond_type == "flemish" and ((i - 1) % 2 == 1)) else 0

            for j, brick in enumerate(self.rows[i]):
                left1  = self.positions_mm[i][j] + x_offset_i
                right1 = left1 + brick.length
                brick.parents = []
                for k, below in enumerate(self.rows[i - 1]):
                    left2  = self.positions_mm[i - 1][k] + x_offset_prev
                    right2 = left2 + below.length
                    if max(left1, left2) < min(right1, right2):
                        brick.parents.append(below)
        # row 0 bricks keep parents = []

    # ─────────────────────────────────────────────────────
    # 6) build_next: mark next brick in build_order as built.
    #    For English full‐stretchers, we toggle back_to_back on second pass.
    # ─────────────────────────────────────────────────────

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
