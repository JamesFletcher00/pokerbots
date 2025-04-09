import random
from collections import Counter
from itertools import combinations

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
        self.dealer_index = -1
        self.sb_index = 0
        self.bb_index = 1
        self.betting_order = []
        self.first_betting_round = True

    def deal_hole_cards(self):
        for player in self.players:
            player.hand = []
            for _ in range(2):
                player.receive_card(self.deck.draw_card())
        self.post_blinds()
        self.turn_index = (self.bb_index + 1) % len(self.players)

    def reveal_community_cards(self, num):
        drawn_cards = [self.deck.draw_card() for _ in range(num)]
        self.community_cards.extend(drawn_cards)
        return drawn_cards

    def post_blinds(self):
        small_blind_player = self.players[self.sb_index]
        big_blind_player = self.players[self.bb_index]

        small_blind_player.current_bet = 25
        small_blind_player.total_bet = 25
        small_blind_player.chips -= 25

        big_blind_player.current_bet = 50
        big_blind_player.total_bet = 50
        big_blind_player.chips -= 50

        self.current_bet = 50

    def next_turn(self):
        if len(self.players) == 1:
            self.round_active = False
            return
        self.current_turn = (self.current_turn + 1) % len(self.players)
        while self.players[self.current_turn].folded:
            self.current_turn = (self.current_turn + 1) % len(self.players)

    def start_betting_round(self):
        self.betting_order = []
        start_index = (self.bb_index + 1) % len(self.players) if self.state == "pre-flop" else (self.dealer_index + 1) % len(self.players)
        for i in range(len(self.players)):
            index = (start_index + i) % len(self.players)
            player = self.players[index]
            if not player.folded:
                self.betting_order.append(player)
        self.current_betting_index = 0
        self.turn_player = self.betting_order[0]

    def handle_betting_round(self):
        all_bets_equal = all(player.total_bet == self.current_bet and self.current_bet > 0 for player in self.players if not player.folded)
        all_checked = all(player.checked for player in self.players if not player.folded)

        if all_bets_equal or all_checked:
            if self.state == "pre-flop":
                self.start_betting_round()
                self.flop.extend(self.reveal_community_cards(3))
                self.state = "flop"
                self.reset_bets()
            elif self.state == "flop":
                self.turn.extend(self.reveal_community_cards(1))
                self.state = "turn"
                self.reset_bets()
            elif self.state == "turn":
                self.river.extend(self.reveal_community_cards(1))
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
            player.checked = False
        self.current_bet = 0
        self.current_turn = 0

    def reset_player_actions(self):
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
            self.next_turn()
            return True

    def handle_call(self, player):
        if player.bet >= self.highest_bet_this_round:
            return False
        call_amount = min(self.highest_bet_this_round, player.chips)
        player.chips -= call_amount
        self.pot += call_amount
        player.bet = self.highest_bet_this_round
        self.next_turn()

    def remove_folded_player(self, player_index):
        if len(self.players) > 1:
            del self.players[player_index]
            self.current_turn = player_index % len(self.players)
            self.round_winner()
        else:
            self.state = "end_round"

    def round_winner(self):
        if len(self.players) == 1:
            self.determine_winner()

    def determine_winner(self):
        player_hands = {}
        for player in self.players:
            if not player.folded:
                best_hand = PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
                player_hands[player.name] = best_hand
        if not player_hands:
            print("No valid hands available. No winner.")
            return None
        winner = max(player_hands.items(), key=lambda x: x[1])
        winner_name, winner_hand = winner
        print(f"Winner: {winner_name} with {list(hand_ranks.keys())[winner_hand[0]]}")
        return winner_name