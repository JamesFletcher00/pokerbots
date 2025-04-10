# Full updated script using BettingManager and cleaned GameLoop

import random
from collections import Counter
from itertools import combinations

suits = ["Spades", "Hearts", "Clubs", "Diamonds"]
ranks = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Jack", "Queen", "King"]

hand_ranks = {
    "High Card": 0, "One Pair": 1, "Two Pair": 2, "Three of a Kind": 3,
    "Straight": 4, "Flush": 5, "Full House": 6, "Four of a Kind": 7,
    "Straight Flush": 8, "Royal Flush": 9
}

card_values = {
    'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5, 'Six': 6, 'Seven': 7,
    'Eight': 8, 'Nine': 9, 'Ten': 10, 'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 14
}

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank} of {self.suit}"

    def __repr__(self):
        return f"Card('{self.rank}', '{self.suit}')"

    def get_card_ranks(hand):
        return sorted([card_values[card.rank] for card in hand], reverse=True)

    def count_ranks(hand):
        values = [card.rank for card in hand]
        return Counter(values)

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in ranks for suit in suits]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_card(self):
        return self.cards.pop() if self.cards else None

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
    @staticmethod
    def is_straight(ranks):
        return ranks == list(range(ranks[0], ranks[0] - 5, -1)) or ranks == [14, 5, 4, 3, 2]

    @staticmethod
    def is_flush(hand):
        suits = [card.suit for card in hand]
        return len(set(suits)) == 1

    @staticmethod
    def evaluate_five_card_hand(hand, community_cards=None):
        if community_cards:
            all_cards = hand + community_cards
            if len(all_cards) < 5:
                return (0, [])
            possible_hands = [
                PokerHandEvaluator.evaluate_five_card_hand(list(combo))
                for combo in combinations(all_cards, 5)
            ]
            return max(possible_hands, key=lambda x: x[0]) if possible_hands else (0, [])

        if not hand or len(hand) != 5:
            return (0, [])

        ranks = Card.get_card_ranks(hand)
        counts = Card.count_ranks(hand)
        flush = PokerHandEvaluator.is_flush(hand)
        straight = PokerHandEvaluator.is_straight(ranks)
        sorted_counts = sorted(((cnt, rank) for rank, cnt in counts.items()), reverse=True)

        if straight and flush:
            return (9, ranks)
        if sorted_counts[0][0] == 4:
            return (7, [sorted_counts[0][1], sorted_counts[1][1]])
        if sorted_counts[0][0] == 3 and sorted_counts[1][0] == 2:
            return (6, [sorted_counts[0][1], sorted_counts[1][1]])
        if flush:
            return (5, ranks)
        if straight:
            return (4, ranks)
        if sorted_counts[0][0] == 3:
            return (3, [sorted_counts[0][1]] + ranks)
        if sorted_counts[0][0] == 2 and sorted_counts[1][0] == 2:
            return (2, [sorted_counts[0][1], sorted_counts[1][1], sorted_counts[2][1]])
        if sorted_counts[0][0] == 2:
            return (1, [sorted_counts[0][1]] + ranks)
        return (0, ranks)

class BettingManager:
    def __init__(self, players, dealer_index):
        self.players = players
        self.dealer_index = dealer_index
        self.sb_index = (dealer_index) % len(players)
        self.bb_index = (dealer_index + 1) % len(players)
        self.current_bet = 0
        self.betting_order = []
        self.turn_index = 0

    def post_blinds(self):
        sb = self.players[self.sb_index]
        bb = self.players[self.bb_index]
        sb.current_bet = 25
        sb.total_bet = 25
        sb.chips -= 25
        bb.current_bet = 50
        bb.total_bet = 50
        bb.chips -= 50
        self.current_bet = 50
        print(f"{sb.name} posts small blind (25)")
        print(f"{bb.name} posts big blind (50)")

    def build_betting_order(self, phase):
        self.betting_order = []
        start_index = (self.bb_index + 1) % len(self.players) if phase == "pre-flop" else (self.dealer_index + 1) % len(self.players)
        for i in range(len(self.players)):
            index = (start_index + i) % len(self.players)
            player = self.players[index]
            if not player.folded:
                self.betting_order.append(player)
        self.turn_index = 0
        print("Betting order:", [p.name for p in self.betting_order])

    def current_player(self):
        return self.betting_order[self.turn_index] if self.turn_index < len(self.betting_order) else None

    def next_turn(self):
        self.turn_index += 1
        while self.turn_index < len(self.betting_order):
            if not self.betting_order[self.turn_index].folded:
                return True
            self.turn_index += 1
        return False

class GameLoop:
    def __init__(self, player_names, starting_chips=1000):
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0
        self.state = "pre-flop"
        self.flop = []
        self.turn = []
        self.river = []
        self.community_cards = []
        self.dealer_index = 0
        self.betting_manager = BettingManager(self.players, self.dealer_index)

    def deal_hole_cards(self):
        for player in self.players:
            player.hand = [self.deck.draw_card(), self.deck.draw_card()]
        self.betting_manager.post_blinds()
        self.betting_manager.build_betting_order(self.state)
        self.pot += 25 + 50


    def reveal_community_cards(self, num):
        drawn = [self.deck.draw_card() for _ in range(num)]
        self.community_cards.extend(drawn)
        return drawn

    def handle_betting_round(self):
        current_player = self.betting_manager.current_player()
        if current_player:
            print(f"{current_player.name}'s turn to act.")
            # Here you'd hook into UI or AI logic to handle action
            self.betting_manager.next_turn()
        else:
            print("Betting round complete. Moving to next phase.")
            self.advance_game_phase()

    def advance_game_phase(self):
        if self.state == "pre-flop":
            self.flop = self.reveal_community_cards(3)
            self.state = "flop"
        elif self.state == "flop":
            self.turn = self.reveal_community_cards(1)
            self.state = "turn"
        elif self.state == "turn":
            self.river = self.reveal_community_cards(1)
            self.state = "river"
        elif self.state == "river":
            self.state = "showdown"
            self.determine_winner()

        self.betting_manager.build_betting_order(self.state)

    def determine_winner(self):
        print("Showdown! Determining winner...")
        player_hands = {
            player.name: PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
            for player in self.players if not player.folded
        }
        if not player_hands:
            print("No valid hands. No winner.")
            return None
        winner = max(player_hands.items(), key=lambda x: x[1])
        print(f"Winner: {winner[0]} with {list(hand_ranks.keys())[winner[1][0]]}")
        return winner[0]

