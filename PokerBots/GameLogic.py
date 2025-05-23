import torch
import time
import random
import json
import os
from collections import Counter
from itertools import combinations
from Bots import BotWrapper

"""
Run The GameVisuals Script To Run Project
"""

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
rank_values = {
    "Spades": 0, "Hearts": 1, "Clubs": 2, "Diamonds": 3
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
    def __init__(self, name, chips=2500, is_bot = False, bot_instance = None):
        self.name = name
        self.chips = chips
        self.hand = []
        self.folded = False
        self.checked = False
        self.bet = 0
        self.total_bet = 0
        self.all_in = False
        self.has_acted = False
        self.is_bot = is_bot
        self.bot_instance = bot_instance
        self.eliminated = False


    def receive_card(self, card):
        self.hand.append(card)

    def show_hand(self):
        return [str(card) for card in self.hand]

class PokerHandEvaluator:
    # Checks if a list of card ranks forms a straight (including ace-low straight)
    @staticmethod
    def is_straight(ranks):
        return ranks == list(range(ranks[0], ranks[0] - 5, -1)) or ranks == [14, 5, 4, 3, 2]

    # Checks if all cards in a hand are of the same suit
    @staticmethod
    def is_flush(hand):
        suits = [card.suit for card in hand]
        return len(set(suits)) == 1

    # Evaluates a 5-card poker hand or best 5-card hand from a larger set (e.g. hole + community)
    @staticmethod
    def evaluate_five_card_hand(hand, community_cards=None):
        if community_cards:
            # If community cards are provided, build all 5-card combos from total cards
            all_cards = hand + community_cards
            if len(all_cards) < 5:
                return (0, [])
            best = max(
                (PokerHandEvaluator.evaluate_five_card_hand(list(combo)) for combo in combinations(all_cards, 5)),
                key=lambda x: (x[0], x[1])  # Maximize rank first, then tiebreakers
            )
            return best

        if not hand or len(hand) != 5:
            return (0, [])  # Invalid hand

        # Count frequency of each rank in the hand
        counts = Counter(card.rank for card in hand)
        count_pairs = sorted(counts.items(), key=lambda x: (-x[1], -card_values[x[0]]))  # Prioritize by count, then rank
        values = [card_values[card.rank] for card in hand]
        suits = [card.suit for card in hand]
        sorted_ranks = sorted(values, reverse=True)
        is_flush = len(set(suits)) == 1
        unique_values = sorted(set(values), reverse=True)

        # Handle special case: 5-high straight (A-2-3-4-5)
        straight_low = [14, 5, 4, 3, 2]
        is_straight = False
        high_card = None
        if unique_values == straight_low:
            is_straight = True
            high_card = 5
        elif len(unique_values) >= 5 and all(unique_values[i] - 1 == unique_values[i + 1] for i in range(len(unique_values) - 1)):
            is_straight = True
            high_card = unique_values[0]

        # Hand Ranking Logic:
        # 9 - Royal Flush
        if is_flush and set(values) == {10, 11, 12, 13, 14}:
            return (9, [14])  # Ace-high

        # 8 - Straight Flush
        if is_flush and is_straight:
            return (8, [high_card])

        # 7 - Four of a Kind
        if count_pairs[0][1] == 4:
            four_val = card_values[count_pairs[0][0]]
            kicker = max(v for v in values if v != four_val)
            return (7, [four_val, kicker])

        # 6 - Full House
        if count_pairs[0][1] == 3 and count_pairs[1][1] == 2:
            triple = card_values[count_pairs[0][0]]
            pair = card_values[count_pairs[1][0]]
            return (6, [triple, pair])

        # 5 - Flush
        if is_flush:
            return (5, sorted(values, reverse=True))

        # 4 - Straight
        if is_straight:
            return (4, [high_card])

        # 3 - Three of a Kind
        if count_pairs[0][1] == 3:
            triple = card_values[count_pairs[0][0]]
            kickers = sorted([v for v in values if v != triple], reverse=True)[:2]
            return (3, [triple] + kickers)

        # 2 - Two Pair
        if count_pairs[0][1] == 2 and count_pairs[1][1] == 2:
            high_pair = card_values[count_pairs[0][0]]
            low_pair = card_values[count_pairs[1][0]]
            kicker = max(v for v in values if v != high_pair and v != low_pair)
            return (2, [high_pair, low_pair, kicker])

        # 1 - One Pair
        if count_pairs[0][1] == 2:
            pair = card_values[count_pairs[0][0]]
            kickers = sorted([v for v in values if v != pair], reverse=True)[:3]
            return (1, [pair] + kickers)

        # 0 - High Card
        return (0, sorted(values, reverse=True))


class BettingManager:
    # initialises the betting manager with player list and dealer position
    def __init__(self, players, dealer_index):
        self.players = players
        self.dealer_index = dealer_index
        self.sb_index = None  # Small blind index
        self.bb_index = None  # Big blind index
        self.current_bet = 0
        self.betting_order = []  # List of players in current betting round
        self.turn_index = 0
        self.last_raise_amount = 50

    # Sets small blind and big blind players based on dealer position
    def set_blinds(self):
        active = [p for p in self.players if not p.eliminated]
        if not active:
            print("[ERROR] No active players left to set blinds.")
            self.sb_index = self.bb_index = -1
            return

        sb_player = active[self.dealer_index % len(active)]
        bb_player = active[(self.dealer_index + 1) % len(active)]

        self.sb_index = self.players.index(sb_player)
        self.bb_index = self.players.index(bb_player)

    # Builds the betting order depending on the game phase (pre-flop vs post-flop)
    def build_betting_order(self, state):
        if state == "pre-flop":
            start_index = (self.bb_index + 1) % len(self.players)
        else:
            start_index = (self.dealer_index + 1) % len(self.players)

        self.betting_order = []

        # Iterate through players to build the correct order of action
        for i in range(len(self.players)):
            idx = (start_index + i) % len(self.players)
            player = self.players[idx]
            if not player.folded and not player.eliminated and not player.all_in:
                self.betting_order.append(player)

        self.turn_index = 0

    # Resets individual player bets and betting state between rounds/phases
    def reset_bets(self):
        for player in self.players:
            player.has_acted = False
            player.checked = False
            player.bet = 0
        self.current_bet = 0
        self.turn_index = 0
        self.last_raise_amount = 50  

    # Returns the player whose turn it currently is
    def current_player(self):
        return self.betting_order[self.turn_index] if self.turn_index < len(self.betting_order) else None

    # checks whether all players have acted this round
    @property
    def all_acted(self):
        return all(p.has_acted or p.folded or p.all_in or p.eliminated for p in self.players)

    #  checks if all remaining players (not all-in) have equal bets
    @property
    def all_bets_equal(self):
        active = [p for p in self.players if not p.folded and not p.eliminated]
        non_allin = [p for p in active if not p.all_in]

        if not non_allin:
            return True  # Everyone is all-in or folded

        first_bet = non_allin[0].total_bet
        return all(p.total_bet == first_bet for p in non_allin)

    # Advances to the next player's turn in the betting order
    def next_turn(self):
        if not self.betting_order:
            return False  # No valid betting order (e.g., all folded or all-in)

        if self.turn_index >= len(self.betting_order):
            self.turn_index = 0

        total_players = len(self.betting_order)
        original_index = self.turn_index
        loop_count = 0

        while loop_count < total_players:
            self.turn_index = (self.turn_index + 1) % total_players
            next_player = self.betting_order[self.turn_index]

            # Skip players who cannot act
            if (
                not next_player.folded and 
                not next_player.has_acted and 
                not next_player.eliminated and 
                not next_player.all_in
            ):
                return True  # Found the next player who can act

            loop_count += 1

        # No valid player found after looping through everyone
        return False

class GameLoop:
    # Main orchestrator for a single game of poker (manages state, players, betting, AI, and training)
    def __init__(self, player_objs=None, player_names=None, starting_chips=2500):
        self.deck = Deck()  # Fresh deck of cards

        # initialise players either from pre-built objects or from a name list (bots auto-wrapped)
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
        
        # Core game state
        self.pot = 0
        self.state = "pre-flop"  # Game phase
        self.flop = []
        self.turn = []
        self.river = []
        self.community_cards = []  # Shared board cards
        self.recent_actions = []   # Records of ["name", "action"] for the current round

        self.dealer_index = 0
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self._request_ui_clear = False
        self.win_type = None  # "fold" or "showdown"
        self.completed_rounds = 0

        self.initial_player_names = [p.name for p in player_objs] if player_objs else player_names
        self.games_won = {name: 0 for name in self.initial_player_names}

    # Deals 2 hole cards to each active (non-eliminated) player and sets up blinds and betting order
    def deal_hole_cards(self):
        for player in self.players:
            if player.eliminated:
                continue
            player.hand = [self.deck.draw_card(), self.deck.draw_card()]
        self.betting_manager.set_blinds()
        self.post_blinds()
        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0

    # Reveals a number of community cards and adds them to the board
    def reveal_community_cards(self, num):
        drawn = [self.deck.draw_card() for _ in range(num)]
        self.community_cards.extend(drawn)
        return drawn

    # Manages the logic for one betting round: advancing if betting conditions are met
    def handle_betting_round(self):
        players_in_hand = [p for p in self.players if not p.folded and not p.eliminated]

        if not players_in_hand:
            return  # All players eliminated or folded

        # If one player remains, award pot immediately
        if len(players_in_hand) == 1:
            players_in_hand[0].chips += self.pot
            self.pot = 0
            self.win_type = "fold"
            self.end_round_immediately()
            return

        # Auto-advance phase if no active players can act
        active_and_able = [
            p for p in self.players 
            if not p.folded and not p.all_in and not p.eliminated
        ]
        if not active_and_able:
            print("[AUTO] All remaining players are folded or all-in. Advancing phase...")
            self.advance_game_phase()
            return

        # Determine betting resolution conditions
        highest_bet = max(p.total_bet for p in players_in_hand)
        all_bets_equal = all(p.total_bet == highest_bet for p in players_in_hand)
        all_acted = all(p.has_acted for p in players_in_hand)

        # If everyone has acted and bets are equal, go to next phase
        if self.betting_manager.all_acted and self.betting_manager.all_bets_equal:
            self.advance_game_phase()

        # If everyone has acted but bets are not equal (due to raises), restart turn order
        if self.betting_manager.all_acted and not self.betting_manager.all_bets_equal:
            for p in self.players:
                if not p.folded and not p.all_in and not p.eliminated:
                    p.has_acted = False
            self.betting_manager.turn_index = -1  # Ensures restart at index 0
            self.betting_manager.build_betting_order(self.state)
            self.betting_manager.turn_index = 0
            return

    # Posts small and big blinds, subtracts from chip stacks, updates pot and all-in status
    def post_blinds(self):
        sb_index = self.betting_manager.sb_index
        bb_index = self.betting_manager.bb_index

        sb = self.players[sb_index]
        bb = self.players[bb_index]

        sb_blind = min(sb.chips, 25)
        bb_blind = min(bb.chips, 50)

        sb.current_bet = sb_blind
        sb.total_bet = sb_blind
        sb.chips -= sb_blind
        if sb.chips == 0:
            sb.all_in = True

        bb.current_bet = bb_blind
        bb.total_bet = bb_blind
        bb.chips -= bb_blind
        if bb.chips == 0:
            bb.all_in = True

        self.betting_manager.current_bet = max(sb_blind, bb_blind)
        self.pot += sb_blind + bb_blind

    # Constructs a 20-dimension feature vector representing the current game state for a given bot.
    def get_bot_state(self, player):
        # Extract bot's hole card info (rank and suit as ints)
        card1, card2 = player.hand
        rank1 = card_values[card1.rank]
        suit1 = rank_values[card1.suit]
        rank2 = card_values[card2.rank]
        suit2 = rank_values[card2.suit]

        # Positional and contextual game features
        position_index = next((i for i, p in enumerate(self.players) if p.name == player.name), -1)
        pot_ratio = self.pot / (player.chips + 1)  # Avoid div by zero
        street_map = {"pre-flop": 0, "flop": 1, "turn": 2, "river": 3, "showdown": 4}
        street_val = street_map.get(self.state, 0)

        # Encode community cards as flat list of rank/suit pairs (max 5 cards)
        community_vals = []
        for card in self.community_cards:
            community_vals.append(card_values[card.rank])
            community_vals.append(rank_values[card.suit])
        while len(community_vals) < 10:
            community_vals.append(0)

        # Round-based aggression (opponent raises this round)
        opponent_names = [p.name for p in self.players if p != player and not p.eliminated]
        opponent_raises = [1 for name, act in self.recent_actions if name in opponent_names and act == "raise"]
        opponent_actions = [1 for name, act in self.recent_actions if name in opponent_names]
        round_raise_rate = len(opponent_raises) / max(1, len(opponent_actions))

        # Historical aggression from player tracking dictionary
        opp_stats = player.bot_instance.opponent_stats
        raise_rates = []
        for name in opponent_names:
            stats = opp_stats.get(name, {})
            r = stats.get("raise", 0)
            rounds = max(1, stats.get("rounds", 0))
            raise_rates.append(r / rounds)
        avg_opp_aggressiveness = sum(raise_rates) / max(1, len(raise_rates))

        # Style-based dynamic modifier based on opponent tendencies
        bot = player.bot_instance
        styles = {"aggressive": 0, "tight": 0, "loose": 0, "balanced": 0}
        for p in self.players:
            if p == player or p.eliminated:
                continue
            profile = bot.opponent_profiles.get(p.name, "balanced")
            styles[profile] += 1

        total_opponents = sum(styles.values())
        risk_modifier = 0.0
        if total_opponents > 0:
            if styles["tight"] / total_opponents > 0.5:
                risk_modifier = +0.2
            elif styles["loose"] / total_opponents > 0.5:
                risk_modifier = -0.2
            elif styles["aggressive"] / total_opponents > 0.5:
                risk_modifier = -0.1

        # 20-dim tensor: hole cards, board state, position, dynamics, style
        return torch.tensor([
            rank1, suit1,
            rank2, suit2,
            *community_vals,
            position_index,
            pot_ratio,
            street_val,
            round_raise_rate,
            avg_opp_aggressiveness,
            risk_modifier
        ], dtype=torch.float32)

    # Handles the entire AI turn for a bot player, including action resolution and experience recording.
    def bot_take_action(self, player):
        if player.eliminated or player.folded or player.all_in:
            return
        if not player.is_bot or not player.bot_instance:
            return

        # Generate current state vector and get decision from the bot policy
        state_tensor = self.get_bot_state(player)
        can_check = player.total_bet == self.betting_manager.current_bet
        action = player.bot_instance.decide_action(state_tensor, can_check=can_check)

        self.recent_actions.append((player.name, action))
        if action not in ["fold", "call", "raise", "check"]:
            return

        normalized_action = "call" if action == "check" else action
        action_index = ["fold", "call", "raise"].index(normalized_action)

        # Update internal stats for learning opponent models
        for opp in self.players:
            if opp == player or opp.eliminated:
                continue
            bot = player.bot_instance
            if opp.name not in bot.opponent_stats:
                bot.opponent_stats[opp.name] = {"raise": 0, "fold": 0, "call": 0, "showdown": 0, "wins": 0, "rounds": 0}
            if action in ["raise", "call", "fold"]:
                bot.opponent_stats[opp.name][action] += 1

        # Apply action to game state
        if action == "fold":
            player.folded = True

        elif action == "check":
            player.checked = True

        elif action == "call":
            call_amount = self.betting_manager.current_bet - player.total_bet
            if call_amount > 0:
                if player.chips <= call_amount:
                    call_amount = player.chips
                    player.all_in = True
                player.chips -= call_amount
                player.total_bet += call_amount
                self.pot += call_amount
            else:
                player.checked = True

        elif action == "raise":
            hand_strength = state_tensor[0].item()
            proposed_raise = int(player.chips * hand_strength * 0.25)
            proposed_raise = max(self.betting_manager.last_raise_amount, proposed_raise)
            proposed_raise = max(5, round(proposed_raise / 5) * 5)  # round to nearest 5

            total_required = (self.betting_manager.current_bet - player.total_bet) + proposed_raise
            total_required = max(0, total_required)

            if player.chips <= total_required:
                total_required = player.chips
                player.all_in = True

            player.chips -= total_required
            player.total_bet += total_required
            self.pot += total_required

            # Update current bet tracking
            raise_difference = player.total_bet - self.betting_manager.current_bet
            self.betting_manager.current_bet = max(self.betting_manager.current_bet, player.total_bet)
            self.betting_manager.last_raise_amount = max(self.betting_manager.last_raise_amount, raise_difference)

        if player.chips <= 0 and not player.eliminated:
            player.all_in = True
            player.chips = 0

        player.has_acted = True

        # Record state-action pair (and placeholder reward = 0) into experience buffer
        next_state = self.get_bot_state(player)
        player.bot_instance.store_experience(
            state=state_tensor,
            action=action_index,
            reward=0,
            next_state=next_state,
            done=False
        )

        print(f"[DEBUG] {player.name} completed action. Chips now: {player.chips}, Total Bet: {player.total_bet}, Pot: {self.pot}")

    # Moves the game to the next phase (flop → turn → river → showdown)
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

        # Reset turn tracking and bets for the new phase
        self.betting_manager.reset_bets()
        for p in self.players:
            self.betting_manager.build_betting_order(self.state)
            self.betting_manager.turn_index = 0

    # Determines the winner(s) at showdown, splits pot, and prepares for round reset
    def determine_winner(self):
        player_hands = {}
        for player in self.players:
            if not player.folded and not player.eliminated:
                rank, tiebreakers = PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
                player_hands[player.name] = (rank, tiebreakers)

        if not player_hands:
            print("No valid hands. No winner.")
            return None

        # Determine best hand rank and tiebreakers
        best_hand = max(player_hands.values(), key=lambda x: (x[0], x[1]))
        best_rank, best_values = best_hand
        tied_players = [
            name for name, hand in player_hands.items()
            if hand[0] == best_rank and hand[1] == best_values
        ]

        # Split the pot evenly, then distribute remainder by dealer order
        split_amount = self.pot // len(tied_players)
        remainder = self.pot % len(tied_players)

        for player in self.players:
            if player.name in tied_players:
                player.chips += split_amount

        dealer_index = self.dealer_index
        name_order = [self.players[(dealer_index + i) % len(self.players)].name for i in range(len(self.players))]
        tied_order = [name for name in name_order if name in tied_players]
        for i in range(remainder):
            recipient = tied_order[i % len(tied_order)]
            for player in self.players:
                if player.name == recipient:
                    player.chips += 1
                    break

        # Register winner and update state
        self.round_winner_name = tied_players[0]  # Just pick the first for tracking
        self.win_type = "showdown"
        self.state = "showdown"
        self._ready_to_reset = True
        return self.round_winner_name

    # Resets state after a completed round and rotates dealer; prepares for next hand
    def reset_round(self):
        # Eliminate players with 0 chips
        for p in self.players:
            if p.chips <= 0:
                p.eliminated = True
            p.all_in = False  # Reset all-in status

        # Reset shared game state
        self.pot = 0
        self.state = "pre-flop"
        self.community_cards = []
        self._request_ui_clear = True
        self.flop = []
        self.turn = []
        self.river = []

        # Reset per-player hand state
        for player in self.players:
            player.hand = []
            player.bet = 0
            player.total_bet = 0
            player.folded = False
            player.checked = False
            player.all_in = False

        # Rotate dealer clockwise
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

        # Reset betting manager and deck, re-deal
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self.betting_manager.set_blinds()
        self.deck = Deck()
        self.deal_hole_cards()

        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0

        for player in self.betting_manager.betting_order:
            print(f"  - {player.name}")

        self.pending_bot_action = None

    # Controls what happens at the end of a round (rewarding, logging, learning, round/game resets)
    def reset_if_ready(self):
        if getattr(self, "_ready_to_reset", False):
            round_winner = getattr(self, "round_winner_name", None)

            # Log win stats to file
            round_win_path = "training_logs/round_wins.json"
            os.makedirs("training_logs", exist_ok=True)

            if os.path.exists(round_win_path):
                with open(round_win_path, "r") as f:
                    round_wins = json.load(f)
            else:
                round_wins = {"rounds_played": 0}

            round_wins["rounds_played"] += 1

            if round_winner:
                if round_winner not in round_wins:
                    round_wins[round_winner] = {"fold": 0, "showdown": 0}
                round_wins[round_winner][self.win_type] += 1

            with open(round_win_path, "w") as f:
                json.dump(round_wins, f, indent=2)

            # Imitation Learning: copy winning actions to opponents' imitation buffers
            winner_obj = next((p for p in self.players if p.name == self.round_winner_name), None)
            if winner_obj and winner_obj.is_bot and hasattr(winner_obj.bot_instance, 'agent'):
                recent_actions = list(winner_obj.bot_instance.agent.sl_buffer.buffer)[-3:]
                for player in self.players:
                    if player.is_bot and player.name != self.round_winner_name:
                        for (state, action) in recent_actions:
                            player.bot_instance.store_imitation(state, action)

            # Update long-term opponent stats
            for player in self.players:
                if player.is_bot:
                    for opp in player.bot_instance.opponent_stats:
                        player.bot_instance.opponent_stats[opp]["rounds"] += 1
                    if round_winner and round_winner in player.bot_instance.opponent_stats:
                        player.bot_instance.opponent_stats[round_winner]["wins"] += 1

            # Reward assignment based on personality traits
            personality_weights = {
                "novice": {"fold_penalty": -0.2, "showdown_bonus": 0.2},
                "conservative": {"fold_penalty": -0.3, "showdown_bonus": 0.3},
                "aggressive": {"fold_penalty": -0.5, "showdown_bonus": 0.5},
                "strategist": {"fold_penalty": -0.4, "showdown_bonus": 0.4}
            }

            for player in self.players:
                if not player.is_bot:
                    continue
                weights = personality_weights.get(player.bot_instance.style, {})
                fold_penalty = weights.get("fold_penalty", -0.6)
                showdown_bonus = weights.get("showdown_bonus", 0.6)

                final_reward = 0
                if player.folded:
                    final_reward += fold_penalty
                elif self.win_type == "showdown" and not player.folded:
                    final_reward += showdown_bonus

                # Extra penalty: small blind folded in a heads-up game
                active_players = [p for p in self.players if not p.eliminated]
                if len(active_players) == 2:
                    is_sb = self.betting_manager.sb_index == self.players.index(player)
                    if player.folded and is_sb:
                        final_reward += fold_penalty * 1.5

                player.bot_instance.store_final_reward(final_reward)

            # Save RL training data to SQLite
            for player in self.players:
                if player.is_bot:
                    player.bot_instance.save_experiences_to_sqlite(win_type=self.win_type)
                    player.bot_instance.results = player.bot_instance.results if hasattr(player.bot_instance, 'results') else []
                    player.bot_instance.results.append(player.chips)

            # Train policies after round
            for player in self.players:
                if player.is_bot:
                    player.bot_instance.train()

            # Update learned player style profiles
            for player in self.players:
                if player.is_bot:
                    player.bot_instance.update_opponent_profile()

            # Reset for next hand
            self.reset_round()
            self._ready_to_reset = False
            self.win_type = None

            # Check if someone has won the game
            active_players = [p for p in self.players if not p.eliminated]
            if len(active_players) == 1:
                winner = active_players[0].name
                self.games_won[winner] += 1
                with open("training_logs/game_wins.json", "w") as f:
                    json.dump(self.games_won, f, indent=2)
                self.restart_full_game()
                return

            # Chart win rate stats periodically
            if round_wins["rounds_played"] == 50 or round_wins["rounds_played"] % 1000 == 0:
                from bot_learning import plot_round_win_pie, plot_combined_win_pie
                plot_round_win_pie(save_path=f"training_logs/round_pie_{round_wins['rounds_played']}.png")
                plot_combined_win_pie(save_path=f"training_logs/combined_pie_{round_wins['rounds_played']}.png")

            # Print and save policy accuracy
            if round_wins["rounds_played"] % 1 == 0:
                accuracy_path = "training_logs/accuracy_log.json"
                os.makedirs("training_logs", exist_ok=True)
                log_entry = {"round": round_wins["rounds_played"]}

                for player in self.players:
                    if player.is_bot:
                        acc = player.bot_instance.compute_policy_accuracy()
                        log_entry[player.name] = round(acc, 4)
                        print(f"[ACCURACY] {player.name} policy accuracy: {acc:.2%}")

                if os.path.exists(accuracy_path):
                    with open(accuracy_path, "r") as f:
                        accuracy_data = json.load(f)
                else:
                    accuracy_data = []

                accuracy_data.append(log_entry)

                with open(accuracy_path, "w") as f:
                    json.dump(accuracy_data, f, indent=2)

    # Immediately ends round due to all others folding; sets winner and triggers reset
    def end_round_immediately(self):
        remaining = [p for p in self.players if not p.folded and not p.eliminated and p.chips > 0]
        if remaining:
            self.round_winner_name = remaining[0].name
        self.win_type = "fold"
        self.state = "end_round"
        self._ready_to_reset = True

    # Resets the entire game state (new bots, chips, deck) once a full game ends
    def restart_full_game(self):
        self.players = []
        for name in self.initial_player_names:
            bot = BotWrapper(name)
            self.players.append(Player(name, chips=2500, is_bot=True, bot_instance=bot))

        self.dealer_index = 0
        self.deck = Deck()
        self.pot = 0
        self.state = "pre-flop"
        self.community_cards = []
        self.flop, self.turn, self.river = [], [], []
        self._request_ui_clear = True

        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self.betting_manager.set_blinds()
        self.deal_hole_cards()
        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0
