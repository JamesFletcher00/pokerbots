import pygame as pg
import time
import random
from GameLogic import GameLoop, BettingManager, Player, hand_ranks, suits, ranks, card_values
from Bots import BotWrapper

pg.init()

class PokerGameUI:
    def __init__(self):
        self.screen_width = 1536
        self.screen_height = 1024
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height))
        pg.display.set_caption("Poker")
        self.FONT = pg.font.SysFont("bodoniblack", 36)
        self.POT_FONT = pg.font.SysFont("bodoniblack", 72)
        self.clock = pg.time.Clock()
        self.game_start_time = None
        self.waiting_to_start = True
        self.pending_bot_action = None
        self.bot_action_timer = 0


        self.load_assets()

        self.bot_names = ["AIan", "AIleen", "AInsley", "AbigAIl"]
        self.bot_players = [
            Player("AIan", is_bot=True, bot_instance=BotWrapper("AIan")),
            Player("AIleen", is_bot=True, bot_instance=BotWrapper("AIleen")),
            Player("AInsley", is_bot=True, bot_instance=BotWrapper("AInsley")),
            Player("AbigAIl", is_bot=True, bot_instance=BotWrapper("AbigAIl")),
        ]
        self.game = GameLoop(player_objs=self.bot_players)
        

        self.game.deal_hole_cards()

        self.hole_card_images = {
            i: [self.card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand]
            for i, player in enumerate(self.game.players)
        }

        self.bet_input = self.TextInput(600, 850, 200, 50)
        self.ok_button = pg.Rect(820, 850, 100, 50)
        self.waiting_for_bet = False
        self.last_state = self.game.state
        self.showdown_time = None 

    def load_assets(self):
        def load_scaled(path, size):
            return pg.transform.scale(pg.image.load(path), size)

        self.poker_table = load_scaled('PokerBots/Assets/Poker Table.png', (self.screen_width, self.screen_height))
        self.poker_table_rect = self.poker_table.get_rect()

        self.card_images = {
            f"{rank}_of_{suit}": load_scaled(f"PokerBots/Assets/{rank} of {suit}.png", (128, 256))
            for suit in suits for rank in ranks
        }

        self.chip_values = [5, 10, 25, 50, 100, 500]
        self.chip_images = {
            f"{v} Chip": load_scaled(f"PokerBots/Assets/{v}Chip_TopDown.png", (64, 64))
            for v in self.chip_values
        }

        self.check_button = load_scaled('PokerBots/Assets/Check Button.png', (128, 128))
        self.call_button = load_scaled('PokerBots/Assets/Call Button.png', (128, 128))
        self.bet_button = load_scaled('PokerBots/Assets/Bet Button.png', (128, 128))
        self.fold_button = load_scaled('PokerBots/Assets/Fold Button.png', (128, 128))

        self.check_button_rect = self.check_button.get_rect(topleft=(448, 704))
        self.call_button_rect = self.call_button.get_rect(topleft=(448, 704))
        self.bet_button_rect = self.bet_button.get_rect(topleft=(704, 704))
        self.fold_button_rect = self.fold_button.get_rect(topleft=(960, 704))

        self.big_blind = load_scaled('PokerBots/Assets/Big Blind.png', (64, 64))
        self.small_blind = load_scaled('PokerBots/Assets/Small Blind.png', (64, 64))

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

    def draw_player_chips(self):
        positions = [(204, 76), (1228, 76), (204, 588), (1228, 588)]
        for i, player in enumerate(self.game.players):
            text = self.FONT.render(f"{player.chips}", True, (0, 0, 0))
            rect = text.get_rect(center=(positions[i][0] + 52, positions[i][1] + 20))
            pg.draw.rect(self.screen, (255, 255, 255), (*positions[i], 105, 40))
            self.screen.blit(text, rect)

    def draw_cards(self):
        positions = [(128, 128), (1152, 128), (128, 640), (1152, 640)]
        for i, pos in enumerate(positions):
            if len(self.hole_card_images[i]) == 2:
                self.screen.blit(self.hole_card_images[i][0], pos)
                self.screen.blit(self.hole_card_images[i][1], (pos[0] + 128, pos[1]))
        for i, card in enumerate(self.game.flop + self.game.turn + self.game.river):
            name = f"{card.rank}_of_{card.suit}"
            self.screen.blit(self.card_images[name], (448 + i * 128, 384))

    def display_bet_ui(self):
        current_player = self.game.betting_manager.current_player()
        if not current_player:
            return

        # === Config ===
        bet_pos = (self.screen_width // 2 - 150, self.screen_height - 100)
        pot_box = pg.Rect(524, 268, 487, 103)  # (x, y, width, height)

        # === Clear text areas ===
        pg.draw.rect(self.screen, (79, 141, 36), (*bet_pos, 300, 50))     # Clear bet text zone
        pg.draw.rect(self.screen, (255, 255, 255), pot_box)             # Clear pot box background

        # === Render Text ===
        bet_text = self.FONT.render(f"{current_player.name}'s Bet: {current_player.bet}", True, (255, 255, 255))
        pot_text = self.POT_FONT.render(f"Pot: {self.game.pot}", True, (0, 0, 0))

        # === Blit to screen ===
        self.screen.blit(bet_text, bet_pos)
        self.screen.blit(pot_text, pot_text.get_rect(center=pot_box.center))

    def redraw_table(self):
        self.screen.blit(self.poker_table, self.poker_table_rect)
        pg.display.flip()



    def draw_blinds(self):
        sb_index = self.game.betting_manager.sb_index
        bb_index = self.game.betting_manager.bb_index
        locations = [(64, 64), (1408, 64), (64, 576), (1408, 576)]
        self.screen.blit(self.small_blind, locations[sb_index])
        self.screen.blit(self.big_blind, locations[bb_index])

    def update_after_round_reset(self):
    # Rebuild the card images after new hole cards are dealt
        self.hole_card_images = {
            i: [self.card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand]
            for i, player in enumerate(self.game.players)
    }

        self.waiting_for_bet = False
        self.bet_input.text = ""

    def run(self):
        running = True
        while running:
            if self.game_start_time is None:
                self.game_start_time = pg.time.get_ticks()

            if self.waiting_to_start:
                now = pg.time.get_ticks()
                if now - self.game_start_time < 5000:
                    # Show startup screen
                    self.screen.fill((0, 0, 0))
                    start_text = self.FONT.render("Starting Game...", True, (255, 255, 255))
                    self.screen.blit(start_text, (self.screen_width // 2 - 150, self.screen_height // 2))
                    pg.display.flip()
                    self.clock.tick(30)
                    continue
                else:
                    print("[DEBUG] Delay finished — entering main game loop.")
                    self.waiting_to_start = False

                    # Force one frame before AI starts acting
                    self.screen.blit(self.poker_table, self.poker_table_rect)
                    pg.display.flip()
                    pg.time.delay(500)

            current_player = None
            if self.game.betting_manager.turn_index < len(self.game.betting_manager.betting_order):
                current_player = self.game.betting_manager.betting_order[self.game.betting_manager.turn_index]
                print(f"[CHECK] Current player: {current_player.name}, is_bot={current_player.is_bot}")

            # Step 1: Schedule the bot, don't act yet
            if current_player and current_player.is_bot and self.pending_bot_action is None:
                self.pending_bot_action = current_player
                self.bot_action_timer = pg.time.get_ticks()

            # Step 2: Perform bot action after delay
            if self.pending_bot_action:
                if pg.time.get_ticks() - self.bot_action_timer > 1000:  # 400ms delay
                    print(f"[BOT TURN] {self.pending_bot_action.name} acting...")
                    self.game.bot_take_action(self.pending_bot_action)
                    self.game.handle_betting_round()

                    if self.game.state != "showdown":
                        has_next = self.game.betting_manager.next_turn()
                        if not has_next:
                            self.game.handle_betting_round()

                    self.pending_bot_action = None  # clear it so we wait again next turn

            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                    pg.quit()

                elif event.type == pg.MOUSEBUTTONDOWN and current_player:
                    if self.bet_button_rect.collidepoint(event.pos):
                        try:
                            amount = int(self.bet_input.text)
                            min_required = self.game.betting_manager.current_bet - current_player.total_bet
                            is_raise = amount + current_player.total_bet > self.game.betting_manager.current_bet

                            if is_raise:
                                for player in self.game.players:
                                    if not player.folded and player != current_player:
                                        player.has_acted = False
                                        player.checked = False

                                self.game.betting_manager.turn_index = -1
                                current_player.has_acted = True
                                current_player.total_bet += amount
                                current_player.chips -= amount
                                self.game.pot += amount
                                self.game.betting_manager.current_bet = max(
                                    self.game.betting_manager.current_bet,
                                    current_player.total_bet
                                )
                                self.bet_input.text = ""

                                has_next = self.game.betting_manager.next_turn()
                                if not has_next:
                                    self.game.handle_betting_round()
                            else:
                                print("[FAIL] Bet rejected. Invalid amount.")
                        except ValueError:
                            print(f"[ERROR] Invalid input: '{self.bet_input.text}'")

                    elif self.call_button_rect.collidepoint(event.pos):
                        call_amount = self.game.betting_manager.current_bet - current_player.total_bet
                        if call_amount > 0:
                            current_player.total_bet += call_amount
                            current_player.chips -= call_amount
                            self.game.pot += call_amount
                        current_player.has_acted = True
                        has_next = self.game.betting_manager.next_turn()
                        if not has_next:
                            self.game.handle_betting_round()

                    elif self.fold_button_rect.collidepoint(event.pos):
                        current_player.folded = True
                        has_next = self.game.betting_manager.next_turn()
                        if not has_next:
                            self.game.handle_betting_round()

                self.bet_input.handle_event(event)

            self.screen.blit(self.call_button, self.call_button_rect.topleft)
            self.screen.blit(self.bet_button, self.bet_button_rect.topleft)
            self.screen.blit(self.fold_button, self.fold_button_rect.topleft)
            self.draw_blinds()
            self.draw_cards()
            self.draw_player_chips()
            self.bet_input.draw(self.screen)

            if self.game.state == "showdown":
                if self.showdown_time is None:
                    self.showdown_time = pg.time.get_ticks()
                elif pg.time.get_ticks() - self.showdown_time > 2000:
                    self.game.reset_if_ready()
                    if self.game._request_ui_clear:
                        self.redraw_table()
                        self.game._request_ui_clear = False

                    self.update_after_round_reset()
                    self.showdown_time = None

            self.display_bet_ui()
            pg.display.flip()
            self.clock.tick(30)  # Keep frame rate stable

        pg.quit()


if __name__ == "__main__":
    ui = PokerGameUI()
    ui.run()

