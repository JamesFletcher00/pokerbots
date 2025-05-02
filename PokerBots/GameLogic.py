import torch
import time
import random
import json
import os
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
            best = max(
                (PokerHandEvaluator.evaluate_five_card_hand(list(combo)) for combo in combinations(all_cards, 5)),
                key=lambda x: (x[0], x[1])
            )
            return best

        if not hand or len(hand) != 5:
            return (0, [])

        # Rank counts
        counts = Counter(card.rank for card in hand)
        count_pairs = sorted(counts.items(), key=lambda x: (-x[1], -card_values[x[0]]))
        sorted_ranks = sorted([card_values[card.rank] for card in hand], reverse=True)
        suits = [card.suit for card in hand]
        values = [card_values[card.rank] for card in hand]
        is_flush = len(set(suits)) == 1

        unique_values = sorted(set(values), reverse=True)

        # Ace-low straight handling
        straight_low = [14, 5, 4, 3, 2]
        is_straight = False
        high_card = None
        if unique_values == straight_low:
            is_straight = True
            high_card = 5
        elif len(unique_values) >= 5 and all(unique_values[i] - 1 == unique_values[i+1] for i in range(len(unique_values)-1)):
            is_straight = True
            high_card = unique_values[0]

        # Royal flush
        if is_flush and set(values) == {10, 11, 12, 13, 14}:
            return (9, [14])  # Royal flush

        # Straight flush
        if is_flush and is_straight:
            return (8, [high_card])

        # Four of a Kind
        if count_pairs[0][1] == 4:
            four_val = card_values[count_pairs[0][0]]
            kicker = max(v for v in values if v != four_val)
            return (7, [four_val, kicker])

        # Full House
        if count_pairs[0][1] == 3 and count_pairs[1][1] == 2:
            triple = card_values[count_pairs[0][0]]
            pair = card_values[count_pairs[1][0]]
            return (6, [triple, pair])

        # Flush
        if is_flush:
            return (5, sorted(values, reverse=True))

        # Straight
        if is_straight:
            return (4, [high_card])

        # Three of a Kind
        if count_pairs[0][1] == 3:
            triple = card_values[count_pairs[0][0]]
            kickers = sorted([v for v in values if v != triple], reverse=True)[:2]
            return (3, [triple] + kickers)

        # Two Pair
        if count_pairs[0][1] == 2 and count_pairs[1][1] == 2:
            high_pair = card_values[count_pairs[0][0]]
            low_pair = card_values[count_pairs[1][0]]
            kicker = max(v for v in values if v != high_pair and v != low_pair)
            return (2, [high_pair, low_pair, kicker])

        # One Pair
        if count_pairs[0][1] == 2:
            pair = card_values[count_pairs[0][0]]
            kickers = sorted([v for v in values if v != pair], reverse=True)[:3]
            return (1, [pair] + kickers)

        # High Card
        return (0, sorted(values, reverse=True))



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
        active = [p for p in self.players if not p.eliminated]
        self.sb_index = self.players.index(active[self.dealer_index % len(active)])
        self.bb_index = self.players.index(active[(self.dealer_index + 1) % len(active)])



    def build_betting_order(self, state):
        if state == "pre-flop":
            start_index = (self.bb_index + 1) % len(self.players)
        else:
            start_index = (self.dealer_index + 1) % len(self.players)

        self.betting_order = []

        for i in range(len(self.players)):
            idx = (start_index + i) % len(self.players)
            player = self.players[idx]
            if not player.folded and not player.eliminated and not player.all_in:
                self.betting_order.append(player)

        self.turn_index = 0



    def reset_bets(self):
        for player in self.players:
            player.has_acted = False
            player.checked = False
            player.bet = 0
        self.current_bet = 0
        self.turn_index = 0

    def current_player(self):
        return self.betting_order[self.turn_index] if self.turn_index < len(self.betting_order) else None
    
    @property
    def all_acted(self):
        return all(p.has_acted or p.folded or p.all_in or p.eliminated for p in self.players)

    @property
    def all_bets_equal(self):
        active_players = [p for p in self.players if not p.folded and not p.all_in and not p.eliminated]
        if not active_players:
            return True
        first_bet = active_players[0].total_bet
        return all(p.total_bet == first_bet for p in active_players)


    def next_turn(self):
        print(f"[NEXT TURN] Moved to: {self.turn_index} – {self.betting_order[self.turn_index].name}")
        
        # ✅ Ensure turn_index is within bounds of current betting_order
        if self.turn_index >= len(self.betting_order):
            self.turn_index = 0

        total_players = len(self.betting_order)
        original_index = self.turn_index
        loop_count = 0

        while loop_count < total_players:
            self.turn_index = (self.turn_index + 1) % total_players
            next_player = self.betting_order[self.turn_index]

            if (
                not next_player.folded and 
                not next_player.has_acted and 
                not next_player.eliminated and 
                not next_player.all_in
                ):
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
        self.recent_actions = []
        self.dealer_index = 0
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self._request_ui_clear = False
        self.win_type = None
        self.completed_rounds = 0
        self.initial_player_names = [p.name for p in player_objs] if player_objs else player_names
        self.games_won = {name: 0 for name in self.initial_player_names}

    def deal_hole_cards(self):
        for player in self.players:
            if player.eliminated:
                continue
            player.hand = [self.deck.draw_card(), self.deck.draw_card()]
        self.betting_manager.set_blinds()
        self.post_blinds()
        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0

    def reveal_community_cards(self, num):
        drawn = [self.deck.draw_card() for _ in range(num)]
        self.community_cards.extend(drawn)
        return drawn

    def handle_betting_round(self):
        players_in_hand = [p for p in self.players if not p.folded and not p.eliminated]

        if not players_in_hand:
            return
        
        if len(players_in_hand) == 1:
            players_in_hand[0].chips += self.pot
            self.pot = 0
            self.win_type = "fold"
            self.end_round_immediately()
            return

        highest_bet = max(p.total_bet for p in players_in_hand)
        all_bets_equal = all(p.total_bet == highest_bet for p in players_in_hand)
        all_acted = all(p.has_acted for p in players_in_hand)

        print(f"[ROUND CHECK] all_acted={all_acted}, all_bets_equal={all_bets_equal}")

        if self.betting_manager.all_acted and self.betting_manager.all_bets_equal:
            print("[ROUND] Advancing to next phase...")
            self.advance_game_phase()

        if self.betting_manager.all_acted and not self.betting_manager.all_bets_equal:
            print("[WARN] All acted but bets unequal — resetting actions and restarting turn order.")
            for p in self.players:
                if not p.folded and not p.all_in and not p.eliminated:
                    p.has_acted = False
            self.betting_manager.turn_index = -1  # So next_turn starts at 0
            self.betting_manager.build_betting_order(self.state)
            self.betting_manager.turn_index = 0
            return


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
            print(f"[BLIND] {sb.name} posts small blind and is all-in!")

        bb.current_bet = bb_blind
        bb.total_bet = bb_blind
        bb.chips -= bb_blind
        if bb.chips == 0:
            bb.all_in = True
            print(f"[BLIND] {bb.name} posts big blind and is all-in!")

        self.betting_manager.current_bet = max(sb_blind, bb_blind)
        self.pot += sb_blind + bb_blind

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

        # Per-round (short-term) aggression
        opponent_names = [p.name for p in self.players if p != player and not p.eliminated]
        opponent_raises = [1 for name, act in self.recent_actions if name in opponent_names and act == "raise"]
        opponent_actions = [1 for name, act in self.recent_actions if name in opponent_names]
        round_raise_rate = len(opponent_raises) / max(1, len(opponent_actions))

        # Cumulative (long-term) aggression
        opp_stats = player.bot_instance.opponent_stats
        raise_rates = []
        for name in opponent_names:
            stats = opp_stats.get(name, {})
            r = stats.get("raise", 0)
            rounds = max(1, stats.get("rounds", 0))
            raise_rates.append(r / rounds)
        avg_opp_aggressiveness = sum(raise_rates) / max(1, len(raise_rates))

        # Final state vector: 6 dimensions
        return torch.tensor([
            hand_strength,
            position_index,
            pot_ratio,
            street_val,
            round_raise_rate,
            avg_opp_aggressiveness
        ])


    
    def bot_take_action(self, player):
        print(f"[DEBUG] {player.name} Bot Acting – State: {self.state}, Chips: {player.chips}")

        # Skip if not valid
        if player.eliminated or player.folded or player.all_in:
            return

        if not player.is_bot or not player.bot_instance:
            return

        # Get bot decision
        state_tensor = self.get_bot_state(player)
        can_check = player.total_bet == self.betting_manager.current_bet
        action = player.bot_instance.decide_action(state_tensor, can_check=can_check)

        print(f"[ACTION] {player.name} decided to {action.upper()}")
        self.recent_actions.append((player.name, action))

        for opp in self.players:
            if opp == player or opp.eliminated:
                continue
            bot = player.bot_instance
            if opp.name not in bot.opponent_stats:
                bot.opponent_stats[opp.name] = {"raise": 0, "fold": 0, "call": 0, "showdown": 0, "wins": 0, "rounds": 0}

            # Record visible action tendencies (not hidden strategy)
            action_key = action.lower()
            if action_key in ["raise", "call", "fold"]:
                bot.opponent_stats[opp.name][action_key] += 1
                # Normalize for RL training
                normalized_action = "call" if action == "check" else action
                action_index = ["fold", "call", "raise"].index(normalized_action)

        if action == "fold":
            player.folded = True

        elif action == "check":
            player.checked = True

        elif action == "call":
            call_amount = self.betting_manager.current_bet - player.total_bet
            if call_amount > 0:
                if player.chips <= call_amount:
                    call_amount = player.chips
                    print(f"[ALL-IN] {player.name} is all-in for {call_amount} chips!")
                player.chips -= call_amount
                player.total_bet += call_amount
                self.pot += call_amount
            else:
                player.checked = True

        elif action == "raise":
            hand_strength = state_tensor[0].item()

            # Dynamic raise: up to 25% of chips, minimum 5
            proposed_raise = int(player.chips * hand_strength * 0.25)
            proposed_raise = max(5, round(proposed_raise / 5) * 5)

            total_required = (self.betting_manager.current_bet - player.total_bet) + proposed_raise
            total_required = max(total_required, 0)

            if player.chips <= total_required:
                total_required = player.chips
                print(f"[ALL-IN] {player.name} raises all-in with {total_required} chips!")

            player.chips -= total_required
            player.total_bet += total_required
            self.pot += total_required

            self.betting_manager.current_bet = max(self.betting_manager.current_bet, player.total_bet)

            for p in self.players:
                if p != player and not p.folded and not p.all_in and not p.eliminated:
                    p.has_acted = False
                    p.checked = False

        # ✅ Final chip check for all-in status
        if player.chips <= 0 and not player.eliminated:
            player.all_in = True
            player.chips = 0

        player.has_acted = True

        # Store experience
        next_state = self.get_bot_state(player)
        player.bot_instance.store_experience(
            state=state_tensor,
            action=action_index,
            reward=0,
            next_state=next_state,
            done=False
        )

        print(f"[DEBUG] {player.name} completed action. Chips now: {player.chips}, Total Bet: {player.total_bet}, Pot: {self.pot}")

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
        # Evaluate hands of players still in the hand
        player_hands = {
            player.name: PokerHandEvaluator.evaluate_five_card_hand(player.hand, self.community_cards)
            for player in self.players if not player.folded
        }

        if not player_hands:
            print("[SHOWDOWN] No valid hands to evaluate.")
            return None

        # Find the best hand (rank and tiebreak values)
        best_hand = max(player_hands.values(), key=lambda x: (x[0], x[1]))
        best_rank, best_values = best_hand

        # Find all players who tied for the best hand
        tied_players = [
            name for name, hand in player_hands.items()
            if hand[0] == best_rank and hand[1] == best_values
        ]

        # Split the pot
        split_amount = self.pot // len(tied_players)
        remainder = self.pot % len(tied_players)

        for player in self.players:
            if player.name in tied_players:
                player.chips += split_amount

        # Distribute remainder to tied players one chip at a time (dealer order)
        dealer_index = self.dealer_index
        name_order = [self.players[(dealer_index + i) % len(self.players)].name for i in range(len(self.players))]
        tied_order = [name for name in name_order if name in tied_players]

        for i in range(remainder):
            recipient = tied_order[i % len(tied_order)]
            for player in self.players:
                if player.name == recipient:
                    player.chips += 1
                    break

        # Log outcome
        if len(tied_players) > 1:
            print(f"[SHOWDOWN] Split pot between: {', '.join(tied_players)}")
            self.round_winner_name = tied_players[0]  # Use one winner for consistency
        else:
            print(f"[SHOWDOWN] Winner: {tied_players[0]} with {list(hand_ranks.keys())[best_rank]}")
            self.round_winner_name = tied_players[0]

        self.win_type = "showdown"
        self.state = "showdown"
        self._ready_to_reset = True
        return self.round_winner_name


    
    def reset_round(self):

        for p in self.players:
                if p.chips <= 0:
                    p.eliminated = True
                p.all_in = False
        
        active_players = [p for p in self.players if not p.eliminated]

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
            player.all_in = False

        # ✅ Rotate dealer
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

        # ✅ Create new betting manager and update blind positions
        self.betting_manager = BettingManager(self.players, self.dealer_index)
        self.betting_manager.set_blinds()
        self.deck = Deck()
        self.deal_hole_cards()

        # ✅ DEBUG OUTPUT
        print(f"[RESET] Dealer index is now: {self.dealer_index}")
        print(f"[BLINDS] SB: {self.betting_manager.sb_index}, BB: {self.betting_manager.bb_index}")

        # ✅ Build new betting order for this round
        self.betting_manager.build_betting_order(self.state)
        self.betting_manager.turn_index = 0

        print("[ORDER] Betting order this round:")
        for player in self.betting_manager.betting_order:
            print(f"  - {player.name}")

        self.pending_bot_action = None

    def reset_if_ready(self):
        if getattr(self, "_ready_to_reset", False):

            # ✅ Log round win
            round_winner = getattr(self, "round_winner_name", None)
            if round_winner:
                round_win_path = "training_logs/round_wins.json"
                os.makedirs("training_logs", exist_ok=True)

                if os.path.exists(round_win_path):
                    with open(round_win_path, "r") as f:
                        round_wins = json.load(f)
                else:
                    round_wins = {}

                if round_winner not in round_wins:
                    round_wins[round_winner] = {"fold": 0, "showdown": 0}

                round_wins[round_winner][self.win_type] += 1

                with open(round_win_path, "w") as f:
                    json.dump(round_wins, f, indent=2)

            # ✅ Update opponent stats
            for player in self.players:
                if player.is_bot and player.bot_instance:
                    # Update rounds
                    for opp_name in player.bot_instance.opponent_stats:
                        player.bot_instance.opponent_stats[opp_name]["rounds"] += 1

                    # Update win count
                    if round_winner and round_winner in player.bot_instance.opponent_stats:
                        player.bot_instance.opponent_stats[round_winner]["wins"] += 1

            # ✅ Save experiences
            for player in self.players:
                if player.is_bot and player.bot_instance:
                    player.bot_instance.save_experiences_to_json(win_type=self.win_type)
                    if not hasattr(player.bot_instance, 'results'):
                        player.bot_instance.results = []
                    player.bot_instance.results.append(player.chips)
                    player.bot_instance.save_experiences_to_json()

            # ✅ Reset round
            self.reset_round()
            self._ready_to_reset = False
            self.win_type = None

            # ✅ Check for game over
            active_players = [p for p in self.players if not p.eliminated]
            if len(active_players) == 1:
                winner = active_players[0].name
                print(f"[GAME COMPLETE] {winner} wins the full game!")
                self.games_won[winner] += 1

                os.makedirs("training_logs", exist_ok=True)
                with open("training_logs/game_wins.json", "w") as f:
                    json.dump(self.games_won, f, indent=2)

                self.restart_full_game()
                return

            # ✅ Round complete tracking
            self.completed_rounds += 1
            if self.completed_rounds % 50 == 0:
                from bot_learning import plot_round_win_pie
                pie_path = f"training_logs/round_pie_{self.completed_rounds}.png"
                plot_round_win_pie(save_path=pie_path)

    def end_round_immediately(self):
        remaining = [p for p in self.players if not p.folded and not p.eliminated and p.chips > 0]
        if remaining:
            self.round_winner_name = remaining[0].name
        self.win_type = "fold"
        self.state = "end_round"
        self._ready_to_reset = True
    
    def restart_full_game(self):
        self.players = []
        for name in self.initial_player_names:
            bot = BotWrapper(name)
            self.players.append(Player(name, chips=1000, is_bot=True, bot_instance=bot))

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



