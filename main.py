import copy
import random
from dataclasses import dataclass

import pyxel


BOARD_W = 6
BOARD_H = 12
CELL = 14
BOARD_X = 26
BOARD_Y = 26
PANEL_GAP = 68
SCREEN_W = 240
SCREEN_H = 220
SOFT_DROP_FRAMES = 3
CPU_ACTION_FRAMES = 4

EMPTY = 0
GARBAGE = 6
COLORS = [8, 9, 10, 11, 12]
CHAIN_BONUS = [0, 8, 16, 32, 64, 96, 128, 160]

PLAYER_KEYS = {
    "left": pyxel.KEY_A,
    "right": pyxel.KEY_D,
    "down": pyxel.KEY_S,
    "rot_cw": pyxel.KEY_F,
    "rot_ccw": pyxel.KEY_G,
}


@dataclass
class Pair:
    x: int
    y: int
    rotation: int
    colors: tuple[int, int]


def pair_cells(pair: Pair) -> list[tuple[int, int, int]]:
    offsets = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    cells = [(pair.x, pair.y, pair.colors[0])]
    dx, dy = offsets[pair.rotation]
    cells.append((pair.x + dx, pair.y + dy, pair.colors[1]))
    return cells


class BattleBoard:
    def __init__(self, rng: random.Random, is_cpu: bool = False) -> None:
        self.rng = rng
        self.is_cpu = is_cpu
        self.grid = [[EMPTY for _ in range(BOARD_W)] for _ in range(BOARD_H)]
        self.current = self._new_pair()
        self.next_pair = self._random_colors()
        self.fall_timer = 0
        self.fall_speed = 24
        self.score = 0
        self.pending_garbage = 0
        self.garbage_meter_flash = 0
        self.attack_ready = 0
        self.chain_text = ""
        self.chain_timer = 0
        self.alive = True
        self.ai_plan: list[str] = []
        self.ai_target_x = 2
        self.ai_target_rot = 0
        self.ai_cooldown = CPU_ACTION_FRAMES

    def clone_grid(self) -> list[list[int]]:
        return [row[:] for row in self.grid]

    def _random_colors(self) -> tuple[int, int]:
        return self.rng.choice(COLORS), self.rng.choice(COLORS)

    def _new_pair(self) -> Pair:
        colors = getattr(self, "next_pair", self._random_colors())
        self.next_pair = self._random_colors()
        return Pair(2, 1, 2, colors)

    def spawn_pair(self) -> None:
        self.current = self._new_pair()
        if not self.can_place(self.current):
            self.alive = False
        if self.is_cpu and self.alive:
            self.ai_cooldown = CPU_ACTION_FRAMES
            self.plan_ai_move()

    def can_place(self, pair: Pair) -> bool:
        for x, y, _ in pair_cells(pair):
            if x < 0 or x >= BOARD_W or y >= BOARD_H:
                return False
            if y >= 0 and self.grid[y][x] != EMPTY:
                return False
        return True

    def move(self, dx: int, dy: int) -> bool:
        test = Pair(self.current.x + dx, self.current.y + dy, self.current.rotation, self.current.colors)
        if self.can_place(test):
            self.current = test
            return True
        return False

    def rotate(self, delta: int) -> bool:
        new_rot = (self.current.rotation + delta) % 4
        kicks = [0, -1, 1, -2, 2]
        for kick in kicks:
            test = Pair(self.current.x + kick, self.current.y, new_rot, self.current.colors)
            if self.can_place(test):
                self.current = test
                return True
        return False

    def hard_drop_step(self) -> bool:
        if self.move(0, 1):
            return True
        self.lock_pair()
        return False

    def update_fall(self, soft_drop: bool) -> None:
        self.fall_timer += 1
        threshold = SOFT_DROP_FRAMES if soft_drop else max(4, self.fall_speed)
        if self.fall_timer >= threshold:
            self.fall_timer = 0
            if not self.move(0, 1):
                self.lock_pair()

    def lock_pair(self) -> None:
        for x, y, color in pair_cells(self.current):
            if y < 0:
                self.alive = False
                return
            self.grid[y][x] = color
        self.resolve_board()
        if self.alive:
            self.spawn_pair()

    def resolve_board(self) -> None:
        chain = 0
        total_attack = 0
        total_cleared = 0
        while True:
            groups = self.find_groups()
            if not groups:
                break
            chain += 1
            cleared = 0
            for group in groups:
                cleared += len(group)
                for x, y in group:
                    self.grid[y][x] = EMPTY
                self.clear_adjacent_garbage(group)
            self.apply_gravity()
            total_cleared += cleared
            total_attack += max(1, cleared - 3) + CHAIN_BONUS[min(chain - 1, len(CHAIN_BONUS) - 1)] // 8
        if total_cleared:
            self.score += total_cleared * 10 + total_attack * 6
            self.chain_text = f"{chain} CHAIN" if chain > 1 else "CLEAR"
            self.chain_timer = 50
            self.attack_ready += total_attack
        self.apply_pending_garbage_if_idle()

    def find_groups(self) -> list[list[tuple[int, int]]]:
        visited = [[False for _ in range(BOARD_W)] for _ in range(BOARD_H)]
        groups: list[list[tuple[int, int]]] = []
        for y in range(BOARD_H):
            for x in range(BOARD_W):
                color = self.grid[y][x]
                if color in (EMPTY, GARBAGE) or visited[y][x]:
                    continue
                stack = [(x, y)]
                group: list[tuple[int, int]] = []
                visited[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    group.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < BOARD_W and 0 <= ny < BOARD_H and not visited[ny][nx]:
                            if self.grid[ny][nx] == color:
                                visited[ny][nx] = True
                                stack.append((nx, ny))
                if len(group) >= 4:
                    groups.append(group)
        return groups

    def clear_adjacent_garbage(self, group: list[tuple[int, int]]) -> None:
        for x, y in group:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < BOARD_W and 0 <= ny < BOARD_H and self.grid[ny][nx] == GARBAGE:
                    self.grid[ny][nx] = EMPTY

    def apply_gravity(self) -> None:
        for x in range(BOARD_W):
            stack = [self.grid[y][x] for y in range(BOARD_H) if self.grid[y][x] != EMPTY]
            for y in range(BOARD_H - 1, -1, -1):
                self.grid[y][x] = stack.pop() if stack else EMPTY

    def apply_pending_garbage_if_idle(self) -> None:
        if self.pending_garbage <= 0:
            return
        if any(self.grid[0][x] != EMPTY for x in range(BOARD_W)):
            self.alive = False
            return
        rows = min(2, (self.pending_garbage + BOARD_W - 1) // BOARD_W)
        self.drop_garbage_rows(rows)

    def receive_attack(self, amount: int) -> None:
        if amount <= 0:
            return
        self.pending_garbage += amount
        self.garbage_meter_flash = 12

    def flush_attack(self) -> int:
        sent = self.attack_ready
        self.attack_ready = 0
        return sent

    def drop_garbage_rows(self, rows: int) -> None:
        amount = min(self.pending_garbage, rows * BOARD_W)
        while amount > 0:
            holes = {self.rng.randrange(BOARD_W)}
            self.grid.pop(0)
            new_row = [GARBAGE] * BOARD_W
            for hole in holes:
                new_row[hole] = EMPTY
            self.grid.append(new_row)
            amount -= BOARD_W - len(holes)
            self.pending_garbage = max(0, self.pending_garbage - (BOARD_W - len(holes)))
        if any(self.grid[0][x] != EMPTY for x in range(BOARD_W)):
            self.alive = False

    def update_effects(self) -> None:
        if self.chain_timer > 0:
            self.chain_timer -= 1
        if self.garbage_meter_flash > 0:
            self.garbage_meter_flash -= 1

    def plan_ai_move(self) -> None:
        best_score = -10**9
        best_x = self.current.x
        best_rot = self.current.rotation
        for rot in range(4):
            for x in range(-1, BOARD_W + 1):
                result = self.simulate_drop(x, rot)
                if result is None:
                    continue
                score = result
                if score > best_score:
                    best_score = score
                    best_x = x
                    best_rot = rot
        self.ai_target_x = best_x
        self.ai_target_rot = best_rot

    def simulate_drop(self, target_x: int, target_rot: int) -> int | None:
        pair = Pair(target_x, self.current.y, target_rot, self.current.colors)
        if not self.can_place(pair):
            return None
        while True:
            dropped = Pair(pair.x, pair.y + 1, pair.rotation, pair.colors)
            if self.can_place(dropped):
                pair = dropped
            else:
                break
        grid = self.clone_grid()
        for x, y, color in pair_cells(pair):
            if y < 0:
                return None
            grid[y][x] = color
        cleared, chains = self._simulate_resolve(grid)
        height_penalty = 0
        for x in range(BOARD_W):
            for y in range(BOARD_H):
                if grid[y][x] != EMPTY:
                    height_penalty += BOARD_H - y
                    break
        adjacency = self._color_adjacency(grid)
        center_bias = -abs(pair.x - 2)
        return cleared * 14 + chains * 28 + adjacency * 2 + center_bias - height_penalty

    def _simulate_resolve(self, grid: list[list[int]]) -> tuple[int, int]:
        total = 0
        chains = 0
        while True:
            visited = [[False for _ in range(BOARD_W)] for _ in range(BOARD_H)]
            groups: list[list[tuple[int, int]]] = []
            for y in range(BOARD_H):
                for x in range(BOARD_W):
                    color = grid[y][x]
                    if color in (EMPTY, GARBAGE) or visited[y][x]:
                        continue
                    stack = [(x, y)]
                    visited[y][x] = True
                    group: list[tuple[int, int]] = []
                    while stack:
                        cx, cy = stack.pop()
                        group.append((cx, cy))
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < BOARD_W and 0 <= ny < BOARD_H and not visited[ny][nx]:
                                if grid[ny][nx] == color:
                                    visited[ny][nx] = True
                                    stack.append((nx, ny))
                    if len(group) >= 4:
                        groups.append(group)
            if not groups:
                return total, chains
            chains += 1
            for group in groups:
                total += len(group)
                for x, y in group:
                    grid[y][x] = EMPTY
            for x in range(BOARD_W):
                stack = [grid[y][x] for y in range(BOARD_H) if grid[y][x] != EMPTY]
                for y in range(BOARD_H - 1, -1, -1):
                    grid[y][x] = stack.pop() if stack else EMPTY

    def _color_adjacency(self, grid: list[list[int]]) -> int:
        score = 0
        for y in range(BOARD_H):
            for x in range(BOARD_W):
                color = grid[y][x]
                if color in (EMPTY, GARBAGE):
                    continue
                if x + 1 < BOARD_W and grid[y][x + 1] == color:
                    score += 1
                if y + 1 < BOARD_H and grid[y + 1][x] == color:
                    score += 1
        return score

    def update_ai(self) -> None:
        if self.ai_cooldown > 0:
            self.ai_cooldown -= 1
            return
        self.ai_cooldown = CPU_ACTION_FRAMES
        if not self.ai_plan:
            if self.current.rotation != self.ai_target_rot:
                self.ai_plan.append("rot")
            elif self.current.x < self.ai_target_x:
                self.ai_plan.append("right")
            elif self.current.x > self.ai_target_x:
                self.ai_plan.append("left")
            else:
                self.ai_plan.append("drop")
        action = self.ai_plan.pop(0)
        if action == "rot":
            self.rotate(1)
        elif action == "left":
            self.move(-1, 0)
        elif action == "right":
            self.move(1, 0)
        else:
            if not self.move(0, 1):
                self.lock_pair()


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Twin Drop Duel", fps=30)
        self.rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.player = BattleBoard(self.rng, is_cpu=False)
        self.cpu = BattleBoard(self.rng, is_cpu=True)
        self.cpu.plan_ai_move()
        self.winner = ""
        self.game_over = False
        self.frame_count = 0

    def update(self) -> None:
        self.frame_count += 1
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return
        if self.game_over:
            return

        self.update_player()
        if self.cpu.alive:
            self.cpu.update_ai()
            self.cpu.update_fall(False)
        if self.player.alive:
            self.player.update_fall(pyxel.btn(PLAYER_KEYS["down"]))

        self.resolve_attacks()
        self.player.update_effects()
        self.cpu.update_effects()

        if not self.player.alive or not self.cpu.alive:
            self.game_over = True
            self.winner = "PLAYER 1 WINS" if self.player.alive else "CPU WINS"

    def update_player(self) -> None:
        if not self.player.alive:
            return
        if pyxel.btnp(PLAYER_KEYS["left"], 8, 3):
            self.player.move(-1, 0)
        if pyxel.btnp(PLAYER_KEYS["right"], 8, 3):
            self.player.move(1, 0)
        if pyxel.btnp(PLAYER_KEYS["rot_cw"]):
            self.player.rotate(1)
        if pyxel.btnp(PLAYER_KEYS["rot_ccw"]):
            self.player.rotate(-1)

    def resolve_attacks(self) -> None:
        sent_left = self.player.flush_attack()
        sent_right = self.cpu.flush_attack()
        if sent_left and sent_right:
            if sent_left > sent_right:
                self.cpu.receive_attack(sent_left - sent_right)
            elif sent_right > sent_left:
                self.player.receive_attack(sent_right - sent_left)
        else:
            if sent_left:
                self.cpu.receive_attack(sent_left)
            if sent_right:
                self.player.receive_attack(sent_right)

    def draw_board(self, board: BattleBoard, x0: int, label: str) -> None:
        pyxel.rect(x0 - 6, BOARD_Y - 6, BOARD_W * CELL + 12, BOARD_H * CELL + 12, 1)
        pyxel.rectb(x0 - 6, BOARD_Y - 6, BOARD_W * CELL + 12, BOARD_H * CELL + 12, 7)
        pyxel.text(x0, 10, label, 7)
        pyxel.text(x0, 18, f"SCORE {board.score}", 6)
        pyxel.text(x0 + BOARD_W * CELL + 16, BOARD_Y, "NEXT", 7)

        for y in range(BOARD_H):
            for x in range(BOARD_W):
                self.draw_cell(x0 + x * CELL, BOARD_Y + y * CELL, board.grid[y][x])

        if board.alive:
            for x, y, color in pair_cells(board.current):
                if y >= 0:
                    self.draw_cell(x0 + x * CELL, BOARD_Y + y * CELL, color, shadow=False)

        next_preview = Pair(0, 1, 2, board.next_pair)
        for x, y, color in pair_cells(next_preview):
            px = x0 + BOARD_W * CELL + 22 + x * 10
            py = BOARD_Y + 20 + y * 10
            pyxel.rect(px, py, 8, 8, color)
            pyxel.rectb(px, py, 8, 8, 7)

        meter_h = min(BOARD_H * CELL, board.pending_garbage * 3)
        meter_color = 8 if board.garbage_meter_flash % 2 == 0 else 10
        pyxel.rect(x0 + BOARD_W * CELL + 18, BOARD_Y + BOARD_H * CELL - meter_h, 8, meter_h, meter_color)
        pyxel.rectb(x0 + BOARD_W * CELL + 17, BOARD_Y, 10, BOARD_H * CELL, 7)
        pyxel.text(x0 + BOARD_W * CELL + 14, BOARD_Y + BOARD_H * CELL + 6, "G", 7)

        if board.chain_timer > 0:
            pyxel.text(x0 + 10, BOARD_Y - 12, board.chain_text, 10)

    def draw_cell(self, px: int, py: int, color: int, shadow: bool = True) -> None:
        if color == EMPTY:
            pyxel.rect(px, py, CELL - 1, CELL - 1, 0)
            pyxel.rectb(px, py, CELL - 1, CELL - 1, 1)
            return
        fill = 13 if color == GARBAGE else color
        pyxel.rect(px, py, CELL - 1, CELL - 1, fill)
        pyxel.rect(px + 2, py + 2, CELL - 5, CELL - 5, 7 if color != GARBAGE else 6)
        if shadow:
            pyxel.rect(px + 1, py + CELL - 4, CELL - 3, 2, 1)
        pyxel.rectb(px, py, CELL - 1, CELL - 1, 7)

    def draw(self) -> None:
        pyxel.cls(2)
        for i in range(0, SCREEN_W, 16):
            pyxel.line(i, 0, i - 30, SCREEN_H, 3)
        pyxel.text(78, 4, "TWIN DROP DUEL", 7)
        pyxel.text(20, 202, "A/D MOVE  S DROP  F/G ROTATE  R RESTART", 7)
        self.draw_board(self.player, BOARD_X, "PLAYER 1")
        self.draw_board(self.cpu, BOARD_X + BOARD_W * CELL + PANEL_GAP, "CPU")

        pyxel.text(104, 30, "VS", 8)
        pyxel.text(96, 42, "CLEAR 4+", 7)
        pyxel.text(95, 52, "SEND GARBAGE", 7)

        if self.game_over:
            pyxel.rect(48, 86, 144, 36, 0)
            pyxel.rectb(48, 86, 144, 36, 7)
            pyxel.text(88, 96, self.winner, 10)
            pyxel.text(83, 108, "PRESS R TO REMATCH", 7)


Game()
