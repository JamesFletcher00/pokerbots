import pygame as pg
import random
from collections import Counter
from itertools import combinations

pg.init()

screen_width = 1536
screen_height = 1024

screen =  pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Poker")


#POKER TABLE
poker_table = pg.transform.scale(pg.image.load('PokerBots/Assets/Poker Table.png'),(screen_width, screen_height))
poker_table_rect = poker_table.get_rect()

#CARDS
card_images = {}

suits = ["Spades", "Hearts", "Clubs", "Diamonds"]
ranks = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"]

rank_values = {
    "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7,
    "Eight": 8, "Nine": 9, "Ten": 10, "Jack": 11, "Queen": 12, "King": 13, "Ace": 14
}

hand_ranks = [
    "High Card", "One Pair", "Two Pair", "Three of a Kind", "Straight",
    "Flush", "Full House", "Four of a Kind", "Straight Flush", "Royal Flush"
]

for suit in suits:
    for rank in ranks:
        card_name = f"{rank}_of_{suit}"
        file_path = f"PokerBots/Assets/{rank} of {suit}.png"
        card_images[card_name] = pg.transform.scale(pg.image.load(file_path), (128,256))


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"
    
    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"
    
class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in ranks for suit in suits]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_card(self):
        return self.cards.pop() if self.cards else None


#CHIPS
chip_values = [5, 10, 25, 50, 100, 500]

chip_images = {}

for value in chip_values:
    chip_name = f"{value} Chip"
    file_path = f"PokerBots/Assets/{value}Chip_TopDown.png"
    chip_images[chip_name] = pg.transform.scale(pg.image.load(file_path), (64,64))

class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hand = []
        self.folded = False
        self.bet = 0

    def receive_card(self, card):
        self.hand.append(card)

    def show_hand(self):
        return [str(card) for card in self.hand]
    

class PokerHandEvaluator:
    @staticmethod
    def evaluate_hand(cards):
        values = sorted([rank_values[card.rank] for card in cards], reverse=True)
        suits = [card.suit for card in cards]
        value_count = Counter(values)
        suit_count = Counter(suits)

        def is_straight(vals):
            vals = sorted(set(vals), reverse=True)
            for i in range(len(vals) - 4):
                if vals[i] - vals[i + 4] == 4:
                    return vals[i:i + 5]
            return [14, 5, 4, 3, 2] if set([14, 5, 4, 3, 2]).issubset(vals) else None

        flush_suit = next((s for s, count in suit_count.items() if count >= 5), None)
        if flush_suit:
            flush_cards = [rank_values[card.rank] for card in cards if card.suit == flush_suit]
            straight_flush = is_straight(flush_cards)
            if straight_flush:
                return ("Royal Flush",) if straight_flush == [14, 13, 12, 11, 10] else ("Straight Flush", straight_flush)

        if 4 in value_count.values():
            quads = [k for k, v in value_count.items() if v == 4]
            kicker = max([k for k in value_count if k != quads[0]])
            return ("Four of a Kind", quads[0], kicker)

        if 3 in value_count.values() and 2 in value_count.values():
            trips = [k for k, v in value_count.items() if v == 3]
            pair = [k for k, v in value_count.items() if v == 2]
            return ("Full House", trips[0], pair[0])

        if flush_suit:
            flush_cards = sorted([rank_values[card.rank] for card in cards if card.suit == flush_suit], reverse=True)[:5]
            return ("Flush", flush_cards)

        straight = is_straight(values)
        if straight:
            return ("Straight", straight)

        if 3 in value_count.values():
            trips = [k for k, v in value_count.items() if v == 3]
            kickers = sorted([k for k in value_count if k != trips[0]], reverse=True)[:2]
            return ("Three of a Kind", trips[0], kickers)

        pairs = [k for k, v in value_count.items() if v == 2]
        if len(pairs) >= 2:
            pairs.sort(reverse=True)
            kicker = max([k for k in value_count if k not in pairs])
            return ("Two Pair", pairs[0], pairs[1], kicker)

        if len(pairs) == 1:
            kicker = sorted([k for k in value_count if k != pairs[0]], reverse=True)[:3]
            return ("One Pair", pairs[0], kicker)

        return ("High Card", sorted(values, reverse=True)[:5])
    

class GameLoop:
    def __init__(self, player_names, starting_chips=1000):
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0
        self.state = "hole_cards"
        self.current_turn = 0

        self.flop = []
        self.turn = []
        self.river = []
        self.current_bet = 0
        self.round_active = True
    
    def deal_hole_cards(self):
        for player in self.players:
            player.hand = []
            for _ in range(2):
                player.receive_card(self.deck.draw_card())

    def reveal_community_cards(self, num):
        return [self.deck.draw_card() for _ in range(num)]

    def next_turn(self):
        if len(self.players) == 1:
            self.round_active = False
            return
        self.current_turn = (self.current_turn + 1) % len(self.players)
        while self.players[self.current_turn].folded:
            self.current_turn = (self.current_turn + 1) % len(self.players)
    
            
    def reset_player_actions(self):
        """Reset player's bet and folded state after each round."""
        for player in self.players:
            player.bet = 0
            player.folded = False

    def collect_bets(self):
        for player in self.players:
            if not player.folded:
                self.pot += player.bet
                player.chips -= player.bet
            player.bet = 0       

    def remove_folded_player(self, player_index):
        """Remove a player from the game when they fold and adjust turn order."""
        if len(self.players) > 1:
            del self.players[player_index]  # Remove the player from the list
            self.current_turn = player_index % len(self.players)  # Adjust turn index
            self.round_winner()
        else:
            self.state = "end_round"  # If only one player remains, end the round
        
    def round_winner(self):
        if len(self.players) == 1:
            self.determine_winner()


    def determine_winner(self):
        player_hands = {}
        for player in self.players:
            hand = PokerHandEvaluator.evaluate_hand(player.hand)
            player_hands[player.name] = hand

        winner = max(player_hands.items(), key=lambda x: x[1])
        print(f"Winner: {winner[0]} with {winner[1][0]}")


class TextInput:
    def __init__(self, x, y, width, height):
        self.rect = pg.Rect(x, y, width, height)
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
        text_surface = self.font.render(self.text, True, self.color)
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))

bet_input = TextInput(600, 850, 200, 50)
waiting_for_bet = False    
ok_button = pg.Rect(820, 850, 100, 50)

#GAME LOOP
#RANDOMISER JUST TO TEST THE IMAGE LOADING 
#NEEDS CHANGING
random_chip_value = random.choice(chip_values)
random_chip_name = f"{random_chip_value} Chip"
random_chip_image = chip_images[random_chip_name]

call_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Call Button.png'),(128,128))
call_button_rect = call_button.get_rect(topleft=(448, 704))
bet_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Bet Button.png'),(128,128))
bet_button_rect = bet_button.get_rect(topleft=(704, 704))
fold_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Fold Button.png'),(128,128))
fold_button_rect = fold_button.get_rect(topleft=(960, 704))


big_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Big Blind.png'),(64,64))
small_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Small Blind.png'),(64,64))

game = GameLoop(["Player 1", "Player 2", "Player 3", "Player 4"])
game.deal_hole_cards()

hole_card_images = {i: [card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand] for i, player in enumerate(game.players)}

def draw_cards():
    positions = [(128, 128), (1152, 128), (128, 640), (1152, 640)]    
    for i, pos in enumerate(positions):
        if len(hole_card_images[i]) == 2:
            screen.blit(hole_card_images[i][0], pos)                        # First card
            screen.blit(hole_card_images[i][1], (pos[0] + 128, pos[1]))     # Second card
    
    # Draw community cards
    for i, card in enumerate(game.flop + game.turn + game.river):
        card_name = f"{card.rank}_of_{card.suit}"
        screen.blit(card_images[card_name], (448 + i * 128, 384))

def display_bet_ui():
    """Display the current player's bet and the pot."""
    font = pg.font.Font(None, 36)
    current_player = game.players[game.current_turn]
    bet_text = font.render(f"{current_player.name}'s Bet: {current_player.bet}", True, (255, 255, 255))
    pot_text = font.render(f"Pot: {game.pot}", True, (255, 255, 255))
    screen.blit(bet_text, (screen_width // 2 - 150, screen_height - 100))
    screen.blit(pot_text, (screen_width // 2 - 100, screen_height - 150))
    

# GAME LOOP
running = True
while running:
    screen.blit(poker_table, poker_table_rect)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running == False
                pg.quit()
        elif event.type == pg.MOUSEBUTTONDOWN:
            if bet_button_rect.collidepoint(event.pos):
                waiting_for_bet = True

            elif call_button_rect.collidepoint(event.pos):
                current_player = game.players[game.current_turn]
                if current_player.chips >= game.current_bet:
                    current_player.bet = game.current_bet
                    game.pot += game.current_bet
                    current_player.chips -= game.current_bet
                    game.determine_winner()
                    #game.next_turn()

            elif fold_button_rect.collidepoint(event.pos):
                game.remove_folded_player(game.current_turn)

            elif waiting_for_bet and ok_button.collidepoint(event.pos):
                try:
                    bet_amount = int(bet_input.text)
                    current_player = game.players[game.current_turn]
                    if bet_amount > 0 and bet_amount <= current_player.chips:
                        current_player.bet = bet_amount
                        game.pot += bet_amount
                        current_player.chips -= bet_amount
                        game.next_turn()
                        waiting_for_bet = False
                        bet_input.text = ""
                except ValueError:
                    pass
        if game.state == "end_round":
            running = False


        if waiting_for_bet:
            bet_input.handle_event(event)


    # Check if the round is over (all players have acted)
    if not game.round_active:
        # Move to the next game phase
        if game.state == "hole_cards":
            game.flop = game.reveal_community_cards(3)
            game.state = "flop"
        elif game.state == "flop":
            game.turn = game.reveal_community_cards(1)
            game.state = "turn"
        elif game.state == "turn":
            game.river = game.reveal_community_cards(1)
            game.state = "river"
        # After finishing the river, you might want to calculate the winner and reset the game for the next round
        game.reset_player_actions()
        game.round_active = True  # Restart the round for the next phase

    screen.blit(poker_table, poker_table_rect)
    screen.blit(call_button,call_button_rect.topleft)
    screen.blit(bet_button,bet_button_rect.topleft)
    screen.blit(fold_button, fold_button_rect.topleft)
    draw_cards()

    if waiting_for_bet:
        bet_input.draw(screen)
        pg.draw.rect(screen, (0, 255, 0), ok_button)
        screen.blit(pg.font.Font(None, 36).render("OK", True, (0, 0, 0)), (ok_button.x + 30, ok_button.y + 10))
    display_bet_ui()
    pg.display.flip()       


            
pg.quit()
#    screen.blit(big_blind, (64, 64))
#    screen.blit(small_blind, (64, 576))
#    screen.blit(big_blind, (1408, 64))
#    screen.blit(small_blind, (1408, 576))