#!/usr/bin/env python3
import curses
import random
import sys

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

def safe_add(stdscr, y, x, s, attr=0):
    h, w = stdscr.getmaxyx()
    if 0 <= y < h and 0 <= x < w - len(s):
        stdscr.addstr(y, x, s, attr)

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.face_up = False
    @property
    def color_pair(self):
        return 1 if self.suit in (0, 3) else 2  # 1=Cyan(♠♣), 2=Red(♥♦)
    def __str__(self):
        if not self.face_up: return "[??]"
        return f"[{RANKS[self.rank]:>2}{SUITS[self.suit]}]"

class Solitaire:
    def __init__(self):
        self.reset()

    def reset(self):
        deck = [Card(s, r) for s in range(4) for r in range(13)]
        random.shuffle(deck)
        self.stock = []
        self.waste = []
        self.foundations = [[] for _ in range(4)]
        self.tableau = [[] for _ in range(7)]
        
        idx = 0
        for i in range(7):
            for j in range(i + 1):
                c = deck[idx]; idx += 1
                c.face_up = (j == i)
                self.tableau[i].append(c)
        self.stock = deck[idx:]
        self.holding = None  # {'cards': [Card], 'from': ('type', idx)}
        self.won = False

    def draw_stock(self):
        if self.holding: return
        if self.stock:
            c = self.stock.pop()
            c.face_up = True
            self.waste.append(c)
        elif self.waste:
            self.stock = [Card(c.suit, c.rank) for c in reversed(self.waste)]
            for c in self.stock: c.face_up = False
            self.waste.clear()

    def can_place_tableau(self, card, pile_idx):
        pile = self.tableau[pile_idx]
        if not pile: return card.rank == 12
        top = pile[-1]
        return top.face_up and card.rank == top.rank - 1 and card.color_pair != top.color_pair

    def can_place_foundation(self, card, f_idx):
        pile = self.foundations[f_idx]
        if not pile: return card.rank == 0 and card.suit == f_idx
        top = pile[-1]
        return top.suit == f_idx and card.rank == top.rank + 1

    def pickup_tableau(self, col_idx, count=1):
        """Забирает карты из столбца, возвращает список и обновляет столбец."""
        pile = self.tableau[col_idx]
        if count > len(pile): return []
        
        cards = pile[-count:]
        del pile[-count:]  # Удаляем из стола сразу!
        
        # Если под снятыми картами была рубашка, открываем её
        if pile and not pile[-1].face_up:
            pile[-1].face_up = True
            
        return cards

    def execute_move(self, target_type, target_idx):
        if not self.holding: return False
        cards = self.holding['cards']
        first_card = cards[0]

        placed = False
        if target_type == 'tableau':
            if self.can_place_tableau(first_card, target_idx):
                self.tableau[target_idx].extend(cards)
                placed = True
        elif target_type == 'foundation' and len(cards) == 1:
            if self.can_place_foundation(first_card, target_idx):
                self.foundations[target_idx].append(first_card)
                placed = True

        if placed:
            # Карты уже удалены из источника при взятии, просто очищаем руку
            self.holding = None
            if all(len(f) == 13 for f in self.foundations):
                self.won = True
            return True
        return False
    
    def cancel_hold(self):
        """Возвращает карты обратно в исходное место."""
        if not self.holding: return
        
        src_type, src_idx = self.holding['from']
        cards = self.holding['cards']
        
        if src_type == 'tableau':
            self.tableau[src_idx].extend(cards)
        elif src_type == 'waste':
            self.waste.extend(cards)
        elif src_type == 'foundation':
            self.foundations[src_idx].extend(cards)
            
        self.holding = None

def draw_game(stdscr, game, cursor, msg=""):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    if h < 20 or w < 50:
        safe_add(stdscr, 0, 0, "⚠ Увеличь терминал (мин. 50x20)")
        stdscr.refresh(); return

    safe_add(stdscr, 0, 2, " K L O N D I K E ", curses.A_BOLD | curses.A_UNDERLINE)
    safe_add(stdscr, 0, 25, "Space: колода | Enter: взять/положить | M: стопка | Esc: отмена | R: рестарт | Q: выход | 1-7: столбцы", curses.A_DIM)

    # Stock & Waste
    safe_add(stdscr, 2, 2, "[  ]" if not game.stock else "[🂠]", curses.A_DIM)
    if game.waste:
        safe_add(stdscr, 2, 8, str(game.waste[-1]), curses.color_pair(game.waste[-1].color_pair) | curses.A_BOLD)
    else:
        safe_add(stdscr, 2, 8, "[  ]", curses.A_DIM)

    # Foundations
    for i in range(4):
        x = 14 + i * 5
        safe_add(stdscr, 2, x, f"[{SUITS[i]}]", curses.A_DIM)
        if game.foundations[i]:
            safe_add(stdscr, 2, x, str(game.foundations[i][-1]), curses.color_pair(game.foundations[i][-1].color_pair) | curses.A_BOLD)

    # Tableau
    col_start_x = 2
    col_spacing = 5
    row_start = 4
    for col_idx in range(7):
        pile = game.tableau[col_idx]
        x = col_start_x + col_idx * col_spacing
        for i, card in enumerate(pile):
            y = row_start + i
            if y >= h - 4:
                safe_add(stdscr, y, x, f"▼+{len(pile)-i}", curses.A_DIM)
                break
            attr = curses.color_pair(card.color_pair) | curses.A_BOLD if card.face_up else curses.A_DIM
            safe_add(stdscr, y, x, str(card), attr)

    # Cursor
    pile_map = {0: (2, 2), 1: (2, 8)}
    for i in range(4): pile_map[2+i] = (2, 14 + i*5)
    for i in range(7): pile_map[6+i] = (row_start, col_start_x + i*col_spacing)

    if cursor in pile_map:
        cy, cx = pile_map[cursor]
        safe_add(stdscr, cy-1, cx, " ▲", curses.A_REVERSE | curses.A_BOLD)

    # Status
    status_y = h - 2
    if game.holding:
        count = len(game.holding['cards'])
        cards_str = " ".join(str(c) for c in game.holding['cards'])
        safe_add(stdscr, status_y, 2, f"✋ Держу ({count}): {cards_str}", curses.A_BOLD | curses.A_BLINK)
    else:
        safe_add(stdscr, status_y, 2, "✋ Ничего не держу", curses.A_DIM)

    if game.won:
        safe_add(stdscr, h-1, 2, "🎉 ПОБЕДА! R - новая, Q - выход", curses.A_BOLD | curses.color_pair(3))
    if msg:
        safe_add(stdscr, h-1, 40, msg, curses.A_BOLD | curses.color_pair(2))
        
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
    except: pass

    game = Solitaire()
    cursor = 1
    msg = ""
    
    while True:
        draw_game(stdscr, game, cursor, msg)
        key = stdscr.getch()
        msg = ""

        if key in (ord('q'), ord('Q')): break
        if key in (ord('r'), ord('R')):
            game.reset(); cursor = 1; msg = "🔄 Новая игра"; continue
            
        if key == ord(' '):
            game.draw_stock(); continue
            
        if key == 27:  # Esc
            if game.holding:
                game.cancel_hold()
                msg = "↩ Отмена"
            continue

        if key == curses.KEY_LEFT: cursor = max(0, cursor-1); continue
        if key == curses.KEY_RIGHT: cursor = min(12, cursor+1); continue
        if key == curses.KEY_UP:
            if 6 <= cursor <= 12: cursor -= 6
            elif 2 <= cursor <= 5: cursor = 0
            continue
        if key == curses.KEY_DOWN:
            if 0 <= cursor <= 1: cursor += 6
            elif 2 <= cursor <= 5: cursor += 4
            continue
        if ord('1') <= key <= ord('7'):
            cursor = 5 + (key - ord('0')); continue

        if key in (curses.KEY_ENTER, 10, 13):
            if game.holding:
                # Положить карты
                t_type = 'foundation' if 2 <= cursor <= 5 else 'tableau'
                t_idx = cursor - 2 if t_type == 'foundation' else cursor - 6
                if game.execute_move(t_type, t_idx):
                    msg = "✅ Ход выполнен"
                else:
                    msg = "❌ Нельзя сюда"
            else:
                # Взять карты
                if cursor == 0:
                    game.draw_stock()
                elif cursor == 1 and game.waste:
                    # Взять из сброса
                    card = game.waste.pop()
                    game.holding = {'cards': [card], 'from': ('waste', 0)}
                elif 2 <= cursor <= 5 and game.foundations[cursor-2]:
                    # Взять из базы
                    card = game.foundations[cursor-2].pop()
                    game.holding = {'cards': [card], 'from': ('foundation', cursor-2)}
                elif 6 <= cursor <= 12:
                    # Взять верхнюю карту из столбца
                    col_idx = cursor - 6
                    pile = game.tableau[col_idx]
                    if pile and pile[-1].face_up:
                        cards = game.pickup_tableau(col_idx, 1)
                        game.holding = {'cards': cards, 'from': ('tableau', col_idx)}
                    else:
                        msg = "❌ Нет открытых карт"

        if key in (ord('m'), ord('M')):
            if not game.holding and 6 <= cursor <= 12:
                # Взять всю открытую стопку
                col_idx = cursor - 6
                pile = game.tableau[col_idx]
                count = 0
                for c in reversed(pile):
                    if c.face_up: count += 1
                    else: break
                
                if count > 0:
                    cards = game.pickup_tableau(col_idx, count)
                    game.holding = {'cards': cards, 'from': ('tableau', col_idx)}
                else:
                    msg = "❌ Нет открытых карт"

if __name__ == "__main__":
    print("🃏 Запуск Klondike Solitaire...")
    curses.wrapper(main)
