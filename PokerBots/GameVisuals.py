import pygame as pg
import random
from GameLogic import GameLoop, hand_ranks, suits, ranks, card_values

pg.init()

# Screen and UI setup
screen_width = 1536
screen_height = 1024
screen = pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Poker")
FONT = pg.font.SysFont("bodoniblack", 36)

# Load images
def load_scaled(path, size):
    return pg.transform.scale(pg.image.load(path), size)

poker_table = load_scaled('PokerBots/Assets/Poker Table.png', (screen_width, screen_height))
poker_table_rect = poker_table.get_rect()

# Load cards
card_images = {}
for suit in suits:
    for rank in ranks:
        name = f"{rank}_of_{suit}"
        path = f"PokerBots/Assets/{rank} of {suit}.png"
        card_images[name] = load_scaled(path, (128, 256))

# Load chips
chip_values = [5, 10, 25, 50, 100, 500]
chip_images = {f"{v} Chip": load_scaled(f"PokerBots/Assets/{v}Chip_TopDown.png", (64, 64)) for v in chip_values}

def draw_player_chips(screen, players):
    positions = [(204, 76), (1228, 76), (204, 588), (1228, 588)]
    for i, player in enumerate(players):
        text = FONT.render(f"{player.chips}", True, (0, 0, 0))
        rect = text.get_rect(center=(positions[i][0] + 52, positions[i][1] + 20))
        pg.draw.rect(screen, (255, 255, 255), (*positions[i], 105, 40))
        screen.blit(text, rect)

# Load buttons and blinds
check_button = load_scaled('PokerBots/Assets/Check Button.png', (128, 128))
call_button = load_scaled('PokerBots/Assets/Call Button.png', (128, 128))
bet_button = load_scaled('PokerBots/Assets/Bet Button.png', (128, 128))
fold_button = load_scaled('PokerBots/Assets/Fold Button.png', (128, 128))

check_button_rect = check_button.get_rect(topleft=(448, 704))
call_button_rect = call_button.get_rect(topleft=(448, 704))
bet_button_rect = bet_button.get_rect(topleft=(704, 704))
fold_button_rect = fold_button.get_rect(topleft=(960, 704))

big_blind = load_scaled('PokerBots/Assets/Big Blind.png', (64, 64))
small_blind = load_scaled('PokerBots/Assets/Small Blind.png', (64, 64))

# Input UI
class TextInput:
    def __init__(self, x, y, w, h):
        self.rect = pg.Rect(x, y, w, h)
        self.color = (255, 255, 255)
        self.text = ""
        self.font = pg.font.Font(None, 36)
        self.active = False

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_RETURN:
                return self.text
            elif event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return None

    def draw(self, screen):
        pg.draw.rect(screen, self.color, self.rect, 2)
        surface = self.font.render(self.text, True, self.color)
        screen.blit(surface, (self.rect.x + 5, self.rect.y + 5))

# Game setup
game = GameLoop(["AIan", "AIleen", "AInsley", "AbigAIl"])
game.deal_hole_cards()

hole_card_images = {i: [card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand] for i, player in enumerate(game.players)}

bet_input = TextInput(600, 850, 200, 50)
ok_button = pg.Rect(820, 850, 100, 50)
waiting_for_bet = False

def draw_cards():
    positions = [(128, 128), (1152, 128), (128, 640), (1152, 640)]
    for i, pos in enumerate(positions):
        if len(hole_card_images[i]) == 2:
            screen.blit(hole_card_images[i][0], pos)
            screen.blit(hole_card_images[i][1], (pos[0] + 128, pos[1]))
    for i, card in enumerate(game.flop + game.turn + game.river):
        name = f"{card.rank}_of_{card.suit}"
        screen.blit(card_images[name], (448 + i * 128, 384))

def display_bet_ui():
    current_player = game.players[game.current_turn]
    bet_text = FONT.render(f"{current_player.name}'s Bet: {current_player.bet}", True, (255, 255, 255))
    pot_text = FONT.render(f"Pot: {game.pot}", True, (255, 255, 255))
    screen.blit(bet_text, (screen_width // 2 - 150, screen_height - 100))
    screen.blit(pot_text, (screen_width // 2 - 100, screen_height - 150))

def draw_blinds():
    locations = [(64, 64), (1408, 64), (64, 576), (1408, 576)]
    screen.blit(small_blind, locations[game.sb_index])
    screen.blit(big_blind, locations[game.bb_index])

# Main loop
running = True
while running:
    screen.blit(poker_table, poker_table_rect)

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            running = False
            pg.quit()
        elif event.type == pg.MOUSEBUTTONDOWN:
            current_player = game.players[game.current_turn]
            if bet_button_rect.collidepoint(event.pos):
                waiting_for_bet = True
            elif call_button_rect.collidepoint(event.pos):
                call_amount = game.current_bet - current_player.total_bet
                if call_amount > 0:
                    current_player.total_bet += call_amount
                    current_player.chips -= call_amount
                    game.pot += call_amount
                    game.handle_betting_round()
                else:
                    current_player.checked = True
                    game.handle_betting_round()
            elif fold_button_rect.collidepoint(event.pos):
                game.remove_folded_player(game.current_turn)
            elif waiting_for_bet and ok_button.collidepoint(event.pos):
                try:
                    amount = int(bet_input.text)
                    if 0 < amount <= current_player.chips and amount >= game.current_bet - current_player.total_bet:
                        current_player.total_bet += amount
                        current_player.chips -= amount
                        game.pot += amount
                        game.current_bet = max(game.current_bet, current_player.total_bet)
                        game.handle_betting_round()
                        waiting_for_bet = False
                        bet_input.text = ""
                except ValueError:
                    pass
        if waiting_for_bet:
            bet_input.handle_event(event)

        if game.state == "end_round":
            running = False

    screen.blit(poker_table, poker_table_rect)
    screen.blit(call_button, call_button_rect.topleft)
    screen.blit(bet_button, bet_button_rect.topleft)
    screen.blit(fold_button, fold_button_rect.topleft)
    draw_blinds()
    draw_cards()
    draw_player_chips(screen, game.players)

    if waiting_for_bet:
        bet_input.draw(screen)
        pg.draw.rect(screen, (0, 255, 0), ok_button)
        screen.blit(pg.font.Font(None, 36).render("OK", True, (0, 0, 0)), (ok_button.x + 30, ok_button.y + 10))

    display_bet_ui()
    pg.display.flip()

pg.quit()
