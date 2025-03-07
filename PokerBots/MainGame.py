import pygame as pg
import random
from collections import Counter

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
    
    def collect_bets(self):
        for player in self.players:
            if not player.folded:
                self.pot += player.bet
                player.chips -= player.bet
            player.bet = 0
    

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
    
    def deal_hole_cards(self):
        for player in self.players:
            player.hand = []
            for _ in range(2):
                player.receive_card(self.deck.draw_card())

    def reveal_community_cards(self, num):
        return [self.deck.draw_card() for _ in range(num)]

    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.players)
        if all (player.folded for player in self.players):
            self.state = "end_game"


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
    

running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == pg.MOUSEBUTTONDOWN:
            if bet_button_rect.collidepoint(event.pos):
                current_player = game.players[game.current_turn]
                # For simplicity, assume a fixed bet (you can later implement dynamic betting)
                bet_amount = 50
                if current_player.chips >= bet_amount:
                    current_player.bet = bet_amount
                    game.pot += bet_amount
                    current_player.chips -= bet_amount
                    game.next_turn()  # Move to next player
            elif call_button_rect.collidepoint(event.pos):
                current_player = game.players[game.current_turn]
                # Call logic: Match the current bet
                if current_player.chips >= game.current_bet:
                    current_player.bet = game.current_bet
                    game.pot += game.current_bet
                    current_player.chips -= game.current_bet
                    game.next_turn()
            elif fold_button_rect.collidepoint(event.pos):
                current_player = game.players[game.current_turn]
                current_player.folded = True
                game.next_turn()

    screen.blit(poker_table, poker_table_rect)
    screen.blit(call_button,call_button_rect.topleft)
    screen.blit(bet_button,bet_button_rect.topleft)
    screen.blit(fold_button, fold_button_rect.topleft)
    draw_cards()
    display_bet_ui()
    pg.display.flip()       


            
pg.quit()
#    screen.blit(big_blind, (64, 64))
#    screen.blit(small_blind, (64, 576))
#    screen.blit(big_blind, (1408, 64))
#    screen.blit(small_blind, (1408, 576))