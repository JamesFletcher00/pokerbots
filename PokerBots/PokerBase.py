from collections import Counter
import random

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
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        self.cards = [Card(rank, suit) for rank in ranks for suit in suits]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if self.cards:
            return self.cards.pop()
        else:
            raise ValueError("No cards left in the deck.")

class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hand = []
        
    def receive_card(self, card):
        """Add a card to the player's hand."""
        self.hand.append(card)

    def show_hand(self):
        """Return the player's hand as a list of strings."""
        return [str(card) for card in self.hand]
    
    def bet(self, amount):
        """Place a bet by deducting chips."""
        if amount > self.chips:
            raise ValueError(f"{self.name} does not have enough chips to bet {amount}.")
        self.chips -= amount
        return amount

class PokerGame:
    def __init__(self, player_names, starting_chips=1000):
        self.deck = Deck()
        self.players = [Player(name, starting_chips) for name in player_names]
        self.pot = 0

    def deal_hole_cards(self):
        """Deal two cards to each player."""
        for player in self.players:
            player.hand = []  # Reset hands at the start of the round.
            for _ in range(2):
                player.receive_card(self.deck.draw())

    def betting_round(self, round_name=""):
        """Conduct a betting round with options to check, raise, call, or fold."""
        print(f"\n--- Betting Round {round_name} ---")
        current_bet = 0  # The current highest bet in this round
        for player in self.players:
            while True:
                try:
                    # Show the player's hand and options
                    print(f"{player.name}, your hand: {', '.join(player.show_hand())}")
                    if current_bet == 0:  # No bet has been raised yet
                        action = input(f"{player.name} ({player.chips} chips), choose an action: [check/raise/fold]: ").lower()
                        if action == "check":
                            print(f"{player.name} checks.")
                            break
                        elif action == "raise":
                            raise_amount = int(input(f"Enter the amount to raise (min 1 chip): "))
                            if raise_amount <= current_bet:
                                print("You must raise to an amount higher than the current bet.")
                                continue
                            self.pot += player.bet(raise_amount)
                            current_bet = raise_amount
                            print(f"{player.name} raises to {current_bet}. Current pot: {self.pot}")
                            break
                        elif action == "fold":
                            print(f"{player.name} folds and is out of this round.")
                            self.players.remove(player)  # Remove the player from the round
                            break
                        else:
                            print("Invalid action. Please enter check, raise, or fold.")
                            continue
                    else:  # The pot has been raised
                        action = input(f"{player.name} ({player.chips} chips), choose an action: [call/raise/fold]: ").lower()
                        if action == "call":
                            self.pot += player.bet(current_bet)
                            print(f"{player.name} calls. Current pot: {self.pot}")
                            break
                        elif action == "raise":
                            raise_amount = int(input(f"Enter the amount to raise (must be higher than {current_bet}): "))
                            if raise_amount <= current_bet:
                                print("You must raise to an amount higher than the current bet.")
                                continue
                            self.pot += player.bet(raise_amount)
                            current_bet = raise_amount
                            print(f"{player.name} raises to {current_bet}. Current pot: {self.pot}")
                            break
                        elif action == "fold":
                            print(f"{player.name} folds and is out of this round.")
                            self.players.remove(player)  # Remove the player from the round
                            break
                        else:
                            print("Invalid action. Please enter call, raise, or fold.")
                            continue
                except ValueError as e:
                    print(f"Invalid input: {e}. Please try again.")
                    continue


    def reveal_community_cards(self, num_cards, already_revealed):
        """Reveal community cards incrementally."""
        print(f"\n--- Revealing {num_cards} Community Card(s) ---")
        new_cards = [self.deck.draw() for _ in range(num_cards)]
        community_cards = already_revealed + new_cards
        print("Community cards:", ", ".join(str(card) for card in community_cards))
        return community_cards

    def evaluate_hand(self, cards):
        """
        Evaluate the hand using poker hand rankings.
        :param cards: List of Card objects (player's hand + community cards)
        :return: Tuple (rank, description), e.g., (3, "Three of a Kind")
        """
        rank_values = {str(i): i for i in range(2, 11)}
        rank_values.update({'J': 11, 'Q': 12, 'K': 13, 'A': 14})

        # Count occurrences of ranks and suits
        ranks = [card.rank for card in cards]
        suits = [card.suit for card in cards]
        rank_counts = Counter(ranks)
        suit_counts = Counter(suits)

        # Sort ranks by frequency and then by rank value
        sorted_ranks = sorted(rank_counts.keys(), key=lambda r: (-rank_counts[r], -rank_values[r]))

        # Check for combinations
        is_flush = max(suit_counts.values()) >= 5
        is_straight = self.is_straight(sorted_ranks, rank_values)
        if is_flush and is_straight:
            return (8, "Straight Flush")
        if 4 in rank_counts.values():
            return (7, "Four of a Kind")
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            return (6, "Full House")
        if is_flush:
            return (5, "Flush")
        if is_straight:
            return (4, "Straight")
        if 3 in rank_counts.values():
            return (3, "Three of a Kind")
        if list(rank_counts.values()).count(2) >= 2:
            return (2, "Two Pair")
        if list(rank_counts.values()).count(2) == 1:
            return (1, "One Pair")
        return (0, f"High Card: {sorted_ranks[0]}")

    def is_straight(self, sorted_ranks, rank_values):
        """Check if the ranks form a straight."""
        sorted_values = sorted(rank_values[rank] for rank in sorted_ranks)
        for i in range(len(sorted_values) - 4):
            if sorted_values[i:i + 5] == list(range(sorted_values[i], sorted_values[i] + 5)):
                return True
        return False

    def determine_winner(self, community_cards):
        """Determine the winner based on the best hand."""
        print("\n--- Determining Winner ---")
        best_player = None
        best_hand = (-1, "")  # Rank and description of the best hand

        for player in self.players:
            full_hand = player.hand + community_cards
            hand_rank = self.evaluate_hand(full_hand)
            print(f"{player.name}'s hand: {', '.join(player.show_hand())} -> {hand_rank[1]}")
            if hand_rank > best_hand:
                best_player = player
                best_hand = hand_rank

        if best_player:
            print(f"The winner is {best_player.name} with a {best_hand[1]}!")
            best_player.chips += self.pot
            self.pot = 0
        else:
            print("It's a tie!")

    def play_round(self):
        """Play a single round of poker."""
        print("\n--- New Round ---")
        self.deck = Deck()  # Reset and shuffle the deck.
        self.deal_hole_cards()

        # Pre-Flop Betting Round
        self.betting_round("Pre-Flop")

        # The flop
        community_cards = self.reveal_community_cards(3, [])
        self.betting_round("Post-Flop")

        # The turn
        community_cards = self.reveal_community_cards(1, community_cards)
        self.betting_round("Post-Turn")

        # The river
        community_cards = self.reveal_community_cards(1, community_cards)
        self.betting_round("Post-River")

        self.determine_winner(community_cards)

    def start(self):
        """Start the poker game."""
        print("--- Welcome to Poker ---")
        while True:
            self.play_round()
            cont = input("Do you want to play another round? (yes/no): ").lower()
            if cont != 'yes':
                print("Thanks for playing!")
                break





# Start the game
game = PokerGame(["Alice", "Bob"])
game.start()
