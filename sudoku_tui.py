#!/usr/bin/env python3
import random
import curses
import sys

def is_valid(board, r, c, num):
    if num in board[r]: return False
    if num in [board[i][c] for i in range(9)]: return False
    br, bc = 3 * (r // 3), 3 * (c // 3)
    for i in range(br, br + 3):
        for j in range(bc, bc + 3):
            if board[i][j] == num: return False
    return True

def count_solutions(board, limit=2):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                count = 0
                for num in range(1, 10):
                    if is_valid(board, r, c, num):
                        board[r][c] = num
                        count += count_solutions(board, limit - count)
                        board[r][c] = 0
                        if count >= limit: return count
                return count
    return 1

def generate_solved():
    board = [[0]*9 for _ in range(9)]
    def fill(idx):
        if idx == 81: return True
        r, c = divmod(idx, 9)
        nums = list(range(1, 10))
        random.shuffle(nums)
        for n in nums:
            if is_valid(board, r, c, n):
                board[r][c] = n
                if fill(idx + 1): return True
                board[r][c] = 0
        return False
    fill(0)
    return board

def generate_puzzle(difficulty):
    solved = generate_solved()
    puzzle = [row[:] for row in solved]
    targets = {"easy": 35, "medium": 45, "hard": 55}
    to_remove = targets.get(difficulty, 45)

    positions = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(positions)
    removed = 0
    for r, c in positions:
        if removed >= to_remove: break
        val = puzzle[r][c]
        puzzle[r][c] = 0
        if count_solutions([row[:] for row in puzzle]) == 1:
            removed += 1
        else:
            puzzle[r][c] = val
    return puzzle, solved

def draw_board(stdscr, current, fixed, sel_r, sel_c, difficulty, won):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    if h < 16 or w < 36:
        stdscr.addstr(0, 0, "Терминал слишком маленький! (мин. 36x16)")
        stdscr.refresh()
        return

    title = f" Судоку [{difficulty.upper()}] "
    controls = "←↑↓→: выбор | 1-9: ввод | Backspace: стереть | Q: выход | R: новая"
    stdscr.addstr(0, 2, title, curses.A_BOLD | curses.A_UNDERLINE)
    if w > len(title) + len(controls) + 2:
        stdscr.addstr(0, 2 + len(title), controls, curses.A_DIM)

    stdscr.box()

    start_y, start_x = 2, 4
    
    for r in range(9):
        for c in range(9):
            x = start_x + c * 2 + c // 3
            y = start_y + r + r // 3
            
            val = current[r][c]
            ch = str(val) if val != 0 else "·"
            
            attr = curses.A_DIM if fixed[r][c] else curses.A_NORMAL
            if (r, c) == (sel_r, sel_c):
                attr = curses.A_REVERSE
            if won and not fixed[r][c] and val != 0:
                attr = curses.A_BOLD | curses.color_pair(2) if curses.has_colors() else attr
                
            stdscr.addstr(y, x, ch, attr)

    sep_attr = curses.A_DIM
    for vx in [start_x + 5, start_x + 12]:
        stdscr.vline(start_y, vx, curses.ACS_VLINE, 11, sep_attr)
    for hy in [start_y + 3, start_y + 7]:
        stdscr.hline(hy, start_x, curses.ACS_HLINE, 19, sep_attr)
    for vx in [start_x + 5, start_x + 12]:
        for hy in [start_y + 3, start_y + 7]:
            stdscr.addch(hy, vx, curses.ACS_PLUS, sep_attr)

    if won:
        msg = "🎉 Победа! R - новая, Q - выход"
        stdscr.addstr(14, max(2, (w - len(msg)) // 2), msg, curses.A_BOLD | curses.A_BLINK)
        
    stdscr.refresh()

def main(stdscr, difficulty):
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    try:
        curses.start_color()
        curses.init_pair(2, curses.COLOR_GREEN, -1)
    except curses.error:
        pass

    puzzle, solution = generate_puzzle(difficulty)
    current = [row[:] for row in puzzle]
    fixed = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
    sel_r, sel_c = 0, 0
    won = False

    while True:
        draw_board(stdscr, current, fixed, sel_r, sel_c, difficulty, won)
        key = stdscr.getch()

        if key in (ord('q'), ord('Q')):
            break
            
        if key in (ord('r'), ord('R')):
            puzzle, solution = generate_puzzle(difficulty)
            current = [row[:] for row in puzzle]
            fixed = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
            won = False
            sel_r, sel_c = 0, 0
            continue

        if not won:
            if key == curses.KEY_UP and sel_r > 0: sel_r -= 1
            elif key == curses.KEY_DOWN and sel_r < 8: sel_r += 1
            elif key == curses.KEY_LEFT and sel_c > 0: sel_c -= 1
            elif key == curses.KEY_RIGHT and sel_c < 8: sel_c += 1
            elif key in (curses.KEY_BACKSPACE, curses.KEY_DC, 127):
                if not fixed[sel_r][sel_c]: current[sel_r][sel_c] = 0
            elif ord('1') <= key <= ord('9'):
                if not fixed[sel_r][sel_c]: 
                    current[sel_r][sel_c] = key - ord('0')

        # ✅ Исправленная проверка победы: сравниваем с эталонным решением
        if not won and current == solution:
            won = True

if __name__ == "__main__":
    diff = "medium"
    if len(sys.argv) > 1:
        d = sys.argv[1].lower()
        if d in ("easy", "medium", "hard"): diff = d
    
    print(f"🎮 Запуск Судоку... Уровень: {diff}")
    curses.wrapper(lambda stdscr: main(stdscr, diff))
