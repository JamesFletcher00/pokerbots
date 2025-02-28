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

    def receive_card(self, card):
        self.hand.append(card)

    def show_hand(self):
        return [str(card) for card in self.hand]
    

class GameLoop:
    def __init__(self, player_names, starting_chips=1000):
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0
    
    def deal_hole_cards(self):
        for player in self.players:
            player.hand = []
            for _ in range(2):
                player.receive_card(self.deck.draw_card())

    def play_round(self):
        self.deck = Deck()
        self.deal_hole_cards()

#GAME LOOP
#RANDOMISER JUST TO TEST THE IMAGE LOADING 
#NEEDS CHANGING
random_chip_value = random.choice(chip_values)
random_chip_name = f"{random_chip_value} Chip"
random_chip_image = chip_images[random_chip_name]

call_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Call Button.png'),(128,128))
bet_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Bet Button.png'),(128,128))
fold_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Fold Button.png'),(128,128))

big_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Big Blind.png'),(64,64))
small_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Small Blind.png'),(64,64))

game = GameLoop(["Player 1", "Player 2", "Player 3", "Player 4"])
game.play_round()

hole_card_images = {i: [card_images[f"{card.rank}_of_{card.suit}"] for card in player.hand] for i, player in enumerate(game.players)}
running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    screen.blit(poker_table, poker_table_rect)
    # Display Player 1's hole cards
    if len(hole_card_images[0]) == 2:
        screen.blit(hole_card_images[0][0], (128, 128))  # First card
        screen.blit(hole_card_images[0][1], (256, 128))  # Second card
    
    # Display Player 2's hole cards
    if len(hole_card_images[1]) == 2:
        screen.blit(hole_card_images[1][0], (1152, 128))  # First card
        screen.blit(hole_card_images[1][1], (1280, 128))  # Second card

    if len(hole_card_images[2]) == 2:
        screen.blit(hole_card_images[2][0], (128, 640))  # First card
        screen.blit(hole_card_images[2][1], (256, 640))  # Second card

    if len(hole_card_images[3]) == 2:
        screen.blit(hole_card_images[3][0], (1152, 640))  # First card
        screen.blit(hole_card_images[3][1], (1280, 640))  # Second card

    #COMMUNITY CARDS COORDINATES (SPOT 1- 448,384)(SPOT 2- 576,384)(SPOT 3- 704,384)(SPOT 4- 832,384)(SPOT 5- 960,384)
    screen.blit(call_button, (448, 704))
    screen.blit(bet_button, (704, 704))
    screen.blit(fold_button, (960, 704))

#    screen.blit(big_blind, (64, 64))
#    screen.blit(small_blind, (64, 576))
#    screen.blit(big_blind, (1408, 64))
#    screen.blit(small_blind, (1408, 576))

    #screen.blit(random_chip_image, (500, 425))

    pg.display.flip()        
            
pg.quit()