import torch
import time
import random
from collections import Counter
from itertools import combinations
from Bots import BotWrapper

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
    def __init__(self, name, chips=1000, is_bot = False, bot_instance = None):
        self.name = name
        self.chips = chips
        self.hand = []
        self.folded = False
        self.checked = False
        self.bet = 0
        self.total_bet = 0
        self.has_acted = False
        self.is_bot = is_bot
        self.bot_instance = bot_instance


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
            return max(possible_hands, key=lambda x: x[0:2]) if possible_hands else (0, [])

        if not hand or len(hand) != 5:
            return (0, [])

        ranks = Card.get_card_ranks(hand)
        counts = Card.count_ranks(hand)
        flush = PokerHandEvaluator.is_flush(hand)
        straight = PokerHandEvaluator.is_straight(ranks)

        sorted_counts = sorted(
            ((cnt, card_values[rank]) for rank, cnt in counts.items()),
            key=lambda x: (-x[0], -x[1])
        )
        rank_values = [card_values[card.rank] for card in hand]
        rank_values.sort(reverse=True)

        if straight and flush:
            return (9, rank_values)
        if sorted_counts[0][0] == 4:
            four = sorted_counts[0][1]
            kicker = max([v for v in rank_values if v != four])
            return (7, [four, kicker])
        if sorted_counts[0][0] == 3 and sorted_counts[1][0] == 2:
            return (6, [sorted_counts[0][1], sorted_counts[1][1]])
        if flush:
            return (5, rank_values)
        if straight:
            return (4, rank_values)
        if sorted_counts[0][0] == 3:
            trips = sorted_counts[0][1]
            kickers = [v for v in rank_values if v != trips][:2]
            return (3, [trips] + kickers)
        if sorted_counts[0][0] == 2 and sorted_counts[1][0] == 2:
            high_pair = sorted_counts[0][1]
            low_pair = sorted_counts[1][1]
            kicker = max([v for v in rank_values if v != high_pair and v != low_pair])
            return (2, [high_pair, low_pair, kicker])
        if sorted_counts[0][0] == 2:
            pair = sorted_counts[0][1]
            kickers = [v for v in rank_values if v != pair][:3]
            return (1, [pair] + kickers)
        return (0, rank_values)


class BettingManager:
    def __init__(self, players, dealer_index):
        self.players = players
        self.dealer_index = dealer_index
        self.sb_index = None
        self.bb_index = None
        self.current_bet = 0
        self.betting_order = []
        self.turn_index = 0

    def set_blinds(self):
        self.sb_index = (self.dealer_index) % len(self.players)
        self.bb_index = (self.dealer_index + 1) % len(self.players)


    def build_betting_order(self, state):
        if state == "pre-flop":
            start_index = (self.bb_index + 1) % len(self.players)
        else:
            start_index = (self.dealer_index + 1) % len(self.players)

        self.betting_order = []
        for i in range(len(self.players)):
            idx = (start_index + i) % len(self.players)
            if not self.players[idx].folded:
                self.betting_order.append(self.players[idx])

        self.turn_index = 0  # Always reset turn index

    def reset_bets(self):
        for player in self.players:
            player.has_acted = False
            player.checked = False
            player.bet = 0
        self.current_bet = 0
        self.turn_index = 0

    def current_player(self):
        return self.betting_order[self.turn_index] if self.turn_index < len(self.betting_order) else None

    def next_turn(self):
        print(f"[NEXT TURN] Moved to: {self.turn_index} – {self.betting_order[self.turn_index].name}")

        total_players = len(self.betting_order)
        original_index = self.turn_index
        loop_count = 0

        while loop_count < total_players:
            self.turn_index = (self.turn_index + 1) % total_players
            next_player = self.betting_order[self.turn_index]

            if not next_player.folded and not next_player.has_acted:
                print(f"[NEXT TURN] Next player is {next_player.name}")
                return True

            loop_count += 1

        print("[NEXT TURN] No players left to act.")
        return False




class GameLoop:
    def __init__(self, player_objs=None, player_names=None, starting_chips=1000):
        self.deck = Deck()

        if player_objs:
            self.players = player_objs
        elif player_names:
            self.players = []
            for name in player_names:
                if "AI" in name:
                    bot = BotWrapper(name)
                    self.players.append(Player(name, starting_chips, is_bot=True, bot_instance=bot))
                else:
                    self.players.append(Player(name, starting_chips))

        else:
            raise ValueError("Needs player_objs or player_names")
        

        self.pot = 0
        self.state = "pre-flop"
        self.flop = []
        self.turn = []
        self.river = []
        self.community_cards = []
        self.dealer_index = 0
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self._request_ui_clear = False

    def deal_hole_cards(self):
        for player in self.players:
            player.hand = [self.deck.draw_card(), self.deck.draw_card()]
        self.betting_manager.set_blinds()
        self.post_blinds()
        self.betting_manager.build_betting_order(self.state)
        self.pot += 25 + 50


    def reveal_community_cards(self, num):
        drawn = [self.deck.draw_card() for _ in range(num)]
        self.community_cards.extend(drawn)
        return drawn

    def handle_betting_round(self):
        players_in_hand = [p for p in self.players if not p.folded]

        if not players_in_hand:
            return

        highest_bet = max(p.total_bet for p in players_in_hand)
        all_bets_equal = all(p.total_bet == highest_bet for p in players_in_hand)
        all_checked = all(p.checked for p in players_in_hand)
        all_acted = all(p.has_acted for p in players_in_hand)

        print(f"[ROUND CHECK] all_acted={all_acted}, all_bets_equal={all_bets_equal}, all_checked={all_checked}")

        if all_acted and (all_bets_equal or all_checked):
            print("[ROUND] Advancing to next phase...")
            self.advance_game_phase()




    def post_blinds(self):
        sb_index = self.betting_manager.sb_index
        bb_index = self.betting_manager.bb_index

        sb = self.players[sb_index]
        bb = self.players[bb_index]

        sb.current_bet = 25
        sb.total_bet = 25
        sb.chips -= 25

        bb.current_bet = 50
        bb.total_bet = 50
        bb.chips -= 50

        self.betting_manager.current_bet = 50
        self.pot += 75

    def get_bot_state(self, player):
        if self.state == "pre-flop":
            card1, card2 = player.hand
            v1, v2 = card_values[card1.rank], card_values[card2.rank]
            suited = card1.suit == card2.suit
            pair = card1.rank == card2.rank
            gap = abs(v1 - v2)

            base_strength = (v1 + v2) / 28.0  # Normalize 2–14 + 2–14

            if pair:
                base_strength += 0.3
            if suited:
                base_strength += 0.1
            if gap == 1:
                base_strength += 0.05  # Connectors like 10-J
            elif gap == 0:
                pass  # already scored in pair bonus
            elif gap <= 3:
                base_strength += 0.02  # semi-connected

            # Extra boost for high-card hands
            high_card_bonus = max(v1, v2) / 14.0 * 0.05
            base_strength += high_card_bonus

            hand_strength = min(base_strength, 1.0)

        else:
            # Evaluate actual 5-card strength post-flop
            rank, values = PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
            max_rank_value = values[0] if values else 0
            hand_strength = (rank + (max_rank_value / 14.0) * 0.5) / 9.0  # Blend rank + high card

        position_index = self.players.index(player)
        pot_ratio = self.pot / (player.chips + 1)
        street_map = {"pre-flop": 0, "flop": 1, "turn": 2, "river": 3, "showdown": 4}
        street_val = street_map.get(self.state, 0)

        return torch.tensor([hand_strength, position_index, pot_ratio, street_val])

    

    def bot_take_action(self, player):
        print(f"[DEBUG] {player.name} Bot Acting – State: {self.state}, Chips: {player.chips}")

        if player.is_bot and player.bot_instance:
            state_tensor = self.get_bot_state(player)
            bet_diff = self.betting_manager.current_bet - player.total_bet
            can_check = bet_diff <= 0

            action = player.bot_instance.decide_action(state_tensor, can_check=can_check)
            print(f"[ACTION] {player.name} decided to {action.upper()}")

            if action == "fold":
                player.folded = True

            elif action == "check" and can_check:
                player.checked = True

            elif action == "call":
                if bet_diff > 0:
                    player.total_bet += bet_diff
                    player.chips -= bet_diff
                    self.pot += bet_diff
                else:
                    player.checked = True

            elif action == "raise":
                raise_amount = 50
                total_required = bet_diff + raise_amount
                if player.chips >= total_required:
                    player.total_bet += total_required
                    player.chips -= total_required
                    self.pot += total_required
                    self.betting_manager.current_bet = player.total_bet

                    # Reset others
                    for p in self.players:
                        if p != player and not p.folded:
                            p.has_acted = False
                            p.checked = False
                else:
                    player.checked = True
                     
            # Store transition: (state, action, reward, next_state, done=False)
            next_state = self.get_bot_state(player)
            player.bot_instance.store_experience(
                state=state_tensor,
                action=["fold", "call", "raise", "check"].index(action),  # convert to index
                reward=0,  # Use actual chip diff or 0 here for now
                next_state=next_state,
                done=False
            )


            player.has_acted = True



    def advance_game_phase(self):
        print(f"[ADVANCE] Moving from {self.state} to next phase.")

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

        self.betting_manager.reset_bets()
        for p in self.players:
            print(f"[DEBUG] {p.name} has_acted: {p.has_acted}")
        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0


    def determine_winner(self):
        player_hands = {
            player.name: PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
            for player in self.players if not player.folded
        }
        if not player_hands:
            print("No valid hands. No winner.")
            return None
        
        winner_name, winner_hand = max(player_hands.items(), key=lambda x: x[1])
        print(f"Winner: {winner_name} with {list(hand_ranks.keys())[winner_hand[0]]}")

        # ✅ Give pot to winner
        for player in self.players:
            if player.name == winner_name:
                player.chips += self.pot
                break
            
        self.state = "showdown"
        self._ready_to_reset = True
        return winner_name
    
    def reset_round(self):
        self.pot = 0
        self.state = "pre-flop"
        self.community_cards = []
        self._request_ui_clear = True
        self.flop = []
        self.turn = []
        self.river = []

        for player in self.players:
            player.hand = []
            player.bet = 0
            player.total_bet = 0
            player.folded = False
            player.checked = False

        # ✅ Rotate dealer
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

        # ✅ Create new betting manager and update blind positions
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self.betting_manager.set_blinds()

        self.deck = Deck()

        # ✅ DEBUG OUTPUT
        print(f"[RESET] Dealer index is now: {self.dealer_index}")
        print(f"[BLINDS] SB: {self.betting_manager.sb_index}, BB: {self.betting_manager.bb_index}")

        # ✅ Deal hole cards and post blinds
        self.deal_hole_cards()

        # ✅ Build new betting order for this round
        self.betting_manager.build_betting_order(self.state)

        print("[ORDER] Betting order this round:")
        for player in self.betting_manager.betting_order:
            print(f"  - {player.name}")

    def reset_if_ready(self):
        if getattr(self, "_ready_to_reset", False):
            for player in self.players:
                if player.is_bot and player.bot_instance:
                    if not hasattr(player.bot_instance, 'results'):
                        player.bot_instance.results = []  # Initialize storage

                    # Track final chip stack or pot share
                    player.bot_instance.results.append(player.chips)

                    # Save experience if needed
                    player.bot_instance.save_experiences_to_json()

            self.reset_round()
            self._ready_to_reset = False


