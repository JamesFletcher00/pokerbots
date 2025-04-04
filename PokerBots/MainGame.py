import pygame as pg
import random
from collections import Counter
from itertools import combinations

pg.init()

screen_width = 1536
screen_height = 1024

screen =  pg.display.set_mode((screen_width, screen_height))
pg.display.set_caption("Poker")

FONT = pg.font.SysFont("bodoniblack", 36)

#POKER TABLE
poker_table = pg.transform.scale(pg.image.load('PokerBots/Assets/Poker Table.png'),(screen_width, screen_height))
poker_table_rect = poker_table.get_rect()

#CARDS
card_images = {}

suits = ["Spades", "Hearts", "Clubs", "Diamonds"]
ranks = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"]

hand_ranks = {
    "High Card": 0,
    "One Pair": 1,
    "Two Pair": 2,
    "Three of a Kind": 3,
    "Straight": 4,
    "Flush": 5,
    "Full House": 6,
    "Four of a Kind": 7,
    "Straight Flush": 8,
    "Royal Flush": 9
}

card_values = {'2': 2,
               '3': 3,
                '4': 4,
                '5': 5,
                '6': 6,
                '7': 7,
                '8': 8,
                '9': 9,
                '10': 10,
                'J': 11,
                'Q': 12,
                'K': 13,
                'A': 14
}

for suit in suits:
    for rank in ranks:
        card_name = f"{rank}_of_{suit}"
        file_path = f"PokerBots/Assets/{rank} of {suit}.png"
        card_images[card_name] = pg.transform.scale(pg.image.load(file_path), (128,256))
print(f"{card_name}")

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"
    
    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"
    
    def get_card_ranks(hand):
        return sorted ([card_values[card[0]] for card in hand], reverse=True)
        
    def count_ranks(hand):
        values = [card[0] for card in hand]
        counts = Counter(values)
        return counts
    
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

def draw_player_chips(screen, players):
    chip_positions = [
        (204, 76),
        (1228, 76),
        (204, 588),
        (1228, 588)
    ]

    box_width = 105
    box_height = 40

    for i, player in enumerate(players):
        chip_text = f"{player.chips}"
        text_surface = FONT.render(chip_text, True, (0, 0, 0))
        text_rect = text_surface.get_rect()
        box_x, box_y = chip_positions[i]
        
        # Center the text within the box
        text_rect.center = (box_x + box_width // 2, box_y + box_height // 2)

        pg.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height))  # Box
        screen.blit(text_surface, text_rect)

class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hand = []
        self.folded = False
        self.checked = False
        self.bet = 0
        self.total_bet = 0

    def receive_card(self, card):
        self.hand.append(card)

    def show_hand(self):
        return [str(card) for card in self.hand]

class PokerHandEvaluator:
    def is_straight(ranks):
        return ranks == list(range(ranks[0], ranks[0] - 5, -1)) or ranks == [14,5,4,3,2]
    
    def is_flush(hand):
        suits = [card[1] for card in hand]
        return len(set(suits)) == 1

    @staticmethod
    def evaluate_five_card_hand(hand):
        """Evaluates a five-card poker hand and returns (rank, tiebreaker)."""
        if not hand or len(hand) != 5:
            return (0, [])  # Invalid hand case
        
        ranks = Card.get_card_ranks(hand)  # Get numeric values of cards
        counts = Card.count_ranks(hand)  # Count occurrences of each rank
        flush = PokerHandEvaluator.is_flush(hand)
        straight = PokerHandEvaluator.is_straight(ranks)

        # Sort occurrences: [(count, rank), ...] and sort by count DESC, then rank DESC
        sorted_counts = sorted(((cnt, rank) for rank, cnt in counts.items()), reverse=True)

        if straight and flush:
            return (9, ranks)  # Royal Flush or Straight Flush
        if sorted_counts[0][0] == 4:
            return (7, [sorted_counts[0][1], sorted_counts[1][1]])  # Four of a Kind (rank, kicker)
        if sorted_counts[0][0] == 3 and sorted_counts[1][0] == 2:
            return (6, [sorted_counts[0][1], sorted_counts[1][1]])  # Full House (trips, pair)
        if flush:
            return (5, ranks)  # Flush (sorted cards)
        if straight:
            return (4, ranks)  # Straight (highest card in straight)
        if sorted_counts[0][0] == 3:
            return (3, [sorted_counts[0][1]] + ranks)  # Three of a Kind
        if sorted_counts[0][0] == 2 and sorted_counts[1][0] == 2:
            return (2, [sorted_counts[0][1], sorted_counts[1][1], sorted_counts[2][1]])  # Two Pair
        if sorted_counts[0][0] == 2:
            return (1, [sorted_counts[0][1]] + ranks)  # One Pair
        return (0, ranks)  # High Card
    
    @staticmethod
    def evaluate_best_hand(hand, community_cards):
        """Evaluates the best possible five-card poker hand from seven cards."""
        all_cards = hand + community_cards
        if len(all_cards) < 5:
            return (0, [])  # Not enough cards to evaluate
        
        possible_hands = [PokerHandEvaluator.evaluate_five_card_hand(list(combo)) for combo in combinations(all_cards, 5)]
        
        if not possible_hands:
            return (0, [])  # No valid hands found
        
        best_hand = max(possible_hands, key=lambda x: (x[0], x[1]))  # Consider hand rank and tiebreakers
        return best_hand



class GameLoop:
    def __init__(self, player_names, starting_chips=1000):
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0
        self.state = "pre-flop"
        self.current_turn = 0
        self.highest_bet_this_round = 0

        self.flop = []
        self.turn = []
        self.river = []
        self.community_cards = []
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
    
    def handle_betting_round(self):
        all_bets_equal = all(player.total_bet == self.current_bet and self.current_bet > 0 for player in self.players if not player.folded)
        all_checked = all(player.checked for player in self.players if not player.folded)

        if all_bets_equal or all_checked:
            if self.state == "pre-flop":
                self.flop.extend(self.reveal_community_cards(3))  # Flop
                self.state = "flop"
                self.reset_bets()
            
            elif self.state == "flop":
                self.turn.extend(self.reveal_community_cards(1))  # Turn
                self.state = "turn"
                self.reset_bets()

            elif self.state == "turn":
                self.river.extend(self.reveal_community_cards(1))  # River
                self.state = "river"
                self.reset_bets()
            
            elif self.state == "river":
                self.state = "showdown"
                self.determine_winner()
            
        else:
            self.next_turn()


    def reset_bets(self):
        for player in self.players:
            player.bet = 0
            self.current_bet = 0
            self.current_turn = 0
            player.checked = False      

          
    def reset_player_actions(self):
        """Reset player's bet and folded state after each hand."""
        for player in self.players:
            player.bet = 0
            player.folded = False

    def handle_bet(self, player, bet_amount):
        if bet_amount < self.highest_bet_this_round:
            print(f"Bet must be {self.highest_bet_this_round}. Choose another action.")
            return False
        else:
            player.chips -= bet_amount
            self.pot += bet_amount
            player.bet = bet_amount
            self.highest_bet_this_round = max(self.highest_bet_this_round, bet_amount)
            game.next_turn()
            return True

    def handle_call(self, player):
        if player.bet >= self.highest_bet_this_round:
            return False
        call_amount = min(self.highest_bet_this_round, player.chips)
        player.chips -= call_amount
        self.pot += call_amount
        player.bet = self.highest_bet_this_round
        game.next_turn()

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
            if not player.folded:
                best_hand = PokerHandEvaluator.evaluate_best_hand(player.hand, self.community_cards)
                player_hands[player.name] = best_hand

        if not player_hands:
            print("No valid hands available. No winner.")
            return None

        winner = max(player_hands.items(), key=lambda x: x[1])  # Sort by hand ranking and tiebreaker
        winner_name, winner_hand = winner

        print(f"Winner: {winner_name} with {list(hand_ranks.keys())[winner_hand[0]]}")
        return winner_name



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

check_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Check Button.png'),(128,128))
check_button_rect = check_button.get_rect(topleft=(448, 704))
call_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Call Button.png'),(128,128))
call_button_rect = call_button.get_rect(topleft=(448, 704))
bet_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Bet Button.png'),(128,128))
bet_button_rect = bet_button.get_rect(topleft=(704, 704))
fold_button = pg.transform.scale(pg.image.load('PokerBots/Assets/Fold Button.png'),(128,128))
fold_button_rect = fold_button.get_rect(topleft=(960, 704))


big_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Big Blind.png'),(64,64))
small_blind = pg.transform.scale(pg.image.load('PokerBots/Assets/Small Blind.png'),(64,64))

game = GameLoop(["AIan", "AIleen", "AInsley", "AbigAIl"])
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
    current_player = game.players[game.current_turn]
    bet_text = FONT.render(f"{current_player.name}'s Bet: {current_player.bet}", True, (255, 255, 255))
    pot_text = FONT.render(f"Pot: {game.pot}", True, (255, 255, 255))
    screen.blit(bet_text, (screen_width // 2 - 150, screen_height - 100))
    screen.blit(pot_text, (screen_width // 2 - 100, screen_height - 150))
    

# GAME LOOP
running = True
waiting_for_bet = False  # Initialize state
while running:
    screen.blit(poker_table, poker_table_rect)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running = False  # Use assignment, not comparison
                pg.quit()

        elif event.type == pg.MOUSEBUTTONDOWN:
            current_player = game.players[game.current_turn]

            # Clicked Bet Button
            if bet_button_rect.collidepoint(event.pos):
                waiting_for_bet = True

            # Clicked Call Button
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


            # Clicked Fold Button
            elif fold_button_rect.collidepoint(event.pos):
                game.remove_folded_player(game.current_turn)

            # Confirm Bet Input
            elif waiting_for_bet and ok_button.collidepoint(event.pos):
                try:
                    bet_amount = int(bet_input.text)
                    if bet_amount > 0 and bet_amount <= current_player.chips:
                        # Enforce minimum bet rules
                        if bet_amount >= game.current_bet - current_player.total_bet:
                            # Handle raise
                            current_player.total_bet += bet_amount
                            current_player.chips -= bet_amount
                            game.pot += bet_amount
                            game.current_bet = max(game.current_bet, current_player.total_bet)  # Update max bet this round
                            game.handle_betting_round()
                            waiting_for_bet = False  # Reset waiting state
                            bet_input.text = ""
                        else:
                            print("Bet must match or exceed the current bet.")
                except ValueError:
                    pass

             

        # Round End Condition
        if game.state == "end_round":
            running = False


        if waiting_for_bet:
            bet_input.handle_event(event)



        # After finishing the river, you might want to calculate the winner and reset the game for the next round
        #game.reset_player_actions()
        #game.round_active = True  # Restart the round for the next phase

    screen.blit(poker_table, poker_table_rect)
    #screen.blit(check_button, check_button_rect.topleft)
    screen.blit(call_button,call_button_rect.topleft)
    screen.blit(bet_button,bet_button_rect.topleft)
    screen.blit(fold_button, fold_button_rect.topleft)
    draw_cards()
    draw_player_chips(screen,game.players)

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