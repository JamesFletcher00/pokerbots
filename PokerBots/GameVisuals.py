import pygame as pg
import time
import random
from GameLogic import GameLoop, BettingManager, Player, hand_ranks, suits, ranks, card_values
from Bots import BotWrapper

pg.init()

#Main UI Class for rendering the game using pygame
class PokerGameUI:
    #initialised the UI, loads assets, sets up players and game logic
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
        self.last_debug_time = 0

        self.load_assets()

        self.bot_names = ["novice", "agressive", "conservative", "strategist"]
        self.bot_players = [
            Player("novice", is_bot=True, bot_instance=BotWrapper("novice", style="novice")),
            Player("agressive", is_bot=True, bot_instance=BotWrapper("agressive", style="agressive")),
            Player("conservative", is_bot=True, bot_instance=BotWrapper("conservative", style="conservative")),
            Player("strategist", is_bot=True, bot_instance=BotWrapper("strategist", style="strategist")),
        ]
        self.game = GameLoop(player_objs=self.bot_players)
        

        self.game.deal_hole_cards()

        self.hole_card_images = {
            i: [self.card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand]
            for i, player in enumerate(self.game.players) if not player.eliminated
        }
        self.ok_button = pg.Rect(820, 850, 100, 50)
        self.waiting_for_bet = False
        self.last_state = self.game.state
        self.showdown_time = None 

    #loads all asset images
    def load_assets(self):
        def load_scaled(path, size):
            return pg.transform.scale(pg.image.load(path), size)

        self.poker_table = load_scaled('PokerBots/Assets/Poker Table.png', (self.screen_width, self.screen_height))
        self.poker_table_rect = self.poker_table.get_rect()

        self.card_images = {
            f"{rank}_of_{suit}": load_scaled(f"PokerBots/Assets/{rank} of {suit}.png", (128, 256))
            for suit in suits for rank in ranks
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

    #Displays players chip count
    def draw_player_chips(self):
        positions = [(204, 76), (1228, 76), (204, 588), (1228, 588)]
        for i, player in enumerate(self.game.players):
            text = self.FONT.render(f"{player.chips}", True, (0, 0, 0))
            rect = text.get_rect(center=(positions[i][0] + 52, positions[i][1] + 20))
            pg.draw.rect(self.screen, (255, 255, 255), (*positions[i], 105, 40))
            self.screen.blit(text, rect)

    #displays the hole cards and community cards on the table
    def draw_cards(self):
        positions = [(128, 128), (1152, 128), (128, 640), (1152, 640)]
        for i, pos in enumerate(positions):
            if len(self.hole_card_images[i]) == 2:
                self.screen.blit(self.hole_card_images[i][0], pos)
                self.screen.blit(self.hole_card_images[i][1], (pos[0] + 128, pos[1]))
        for i, card in enumerate(self.game.flop + self.game.turn + self.game.river):
            name = f"{card.rank}_of_{card.suit}"
            self.screen.blit(self.card_images[name], (448 + i * 128, 384))

    #displays amount of chips in the pot
    def display_bet_ui(self):
        pot_box = pg.Rect(524, 268, 487, 103) 
        pg.draw.rect(self.screen, (255, 255, 255), pot_box) # Clear pot box background
        pot_text = self.POT_FONT.render(f"Pot: {self.game.pot}", True, (0, 0, 0))
        self.screen.blit(pot_text, pot_text.get_rect(center=pot_box.center))

    #redraws table after screen updates
    def redraw_table(self):
        self.screen.blit(self.poker_table, self.poker_table_rect)
        pg.display.flip()

    #draws small and big blinds on appropriate players
    def draw_blinds(self):
        sb_index = self.game.betting_manager.sb_index
        bb_index = self.game.betting_manager.bb_index
        locations = [(64, 64), (1408, 64), (64, 576), (1408, 576)]
        self.screen.blit(self.small_blind, locations[sb_index])
        self.screen.blit(self.big_blind, locations[bb_index])

    #updates card image reference after round
    def update_after_round_reset(self):
        self.hole_card_images = {
            i: [self.card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand]
            for i, player in enumerate(self.game.players)
    }
        self.waiting_for_bet = False

    #Main Game Loop -  Handles all events, turns, rendering and round flow
    def run(self):
        running = True
        while running:
            if self.game_start_time is None:
                self.game_start_time = pg.time.get_ticks()

            if self.waiting_to_start:
                now = pg.time.get_ticks()
                if now - self.game_start_time < 500:
                    self.screen.fill((0, 0, 0))
                    start_text = self.FONT.render("Starting Game...", True, (255, 255, 255))
                    self.screen.blit(start_text, (self.screen_width // 2 - 150, self.screen_height // 2))
                    pg.display.flip()
                    self.clock.tick(30)
                    continue
                else:
                    print("[DEBUG] Delay finished — entering main game loop.")
                    self.waiting_to_start = False
                    self.screen.blit(self.poker_table, self.poker_table_rect)
                    pg.display.flip()
                    pg.time.delay(500)

                        # Every 5 seconds, print debug status
            now = pg.time.get_ticks()
            if now - self.last_debug_time > 5000:
                self.last_debug_time = now
                folded = [p.name for p in self.game.players if p.folded]
                all_in = [p.name for p in self.game.players if p.all_in]
                current_turn = (
                    self.game.betting_manager.betting_order[self.game.betting_manager.turn_index].name
                    if self.game.betting_manager.betting_order and self.game.betting_manager.turn_index < len(self.game.betting_manager.betting_order)
                    else "None"
                )
                print(f"[DEBUG] Folded: {folded}")
                print(f"[DEBUG] All-in: {all_in}")
                print(f"[DEBUG] Current turn: {current_turn}")


            current_player = None
            if self.game.betting_manager.turn_index < len(self.game.betting_manager.betting_order):
                candidate = self.game.betting_manager.betting_order[self.game.betting_manager.turn_index]
                if not candidate.eliminated:
                    current_player = candidate


            if current_player and current_player.is_bot and self.pending_bot_action is None:
                self.pending_bot_action = current_player
                self.bot_action_timer = pg.time.get_ticks()

            if self.pending_bot_action:
                if self.pending_bot_action.eliminated or self.pending_bot_action.chips <= 0:
                    print(f"[SKIP] {self.pending_bot_action.name} eliminated. Clearing pending action.")
                    self.pending_bot_action = None
                    self.game.betting_manager.next_turn()  

                elif pg.time.get_ticks() - self.bot_action_timer > 500:
                    print(f"[BOT TURN] {self.pending_bot_action.name} acting...")
                    self.game.bot_take_action(self.pending_bot_action)
                    self.game.handle_betting_round()

                    if self.game.state != "showdown":
                        has_next = self.game.betting_manager.next_turn()
                        if not has_next:
                            self.game.handle_betting_round()

                    self.pending_bot_action = None

            # Handle events
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                    pg.quit()

            # Draw interface
            self.screen.blit(self.call_button, self.call_button_rect.topleft)
            self.screen.blit(self.bet_button, self.bet_button_rect.topleft)
            self.screen.blit(self.fold_button, self.fold_button_rect.topleft)
            self.draw_blinds()
            self.draw_cards()
            self.draw_player_chips()

            if self.game.state in ["showdown", "end_round"]:
                if self.showdown_time is None:
                    self.showdown_time = pg.time.get_ticks()
                elif pg.time.get_ticks() - self.showdown_time > 1000:
                    self.game.reset_if_ready()
                    if self.game._request_ui_clear:
                        self.redraw_table()
                        self.game._request_ui_clear = False
                    self.update_after_round_reset()
                    self.showdown_time = None

            self.display_bet_ui()
            pg.display.flip()
            self.clock.tick(30)

        pg.quit()


if __name__ == "__main__":
    ui = PokerGameUI()
    ui.run()

