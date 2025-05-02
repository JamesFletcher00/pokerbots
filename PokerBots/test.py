import random
from itertools import combinations
from GameLogic import Card, Deck, PokerHandEvaluator, hand_ranks

def simulate_game(num_players=4):
    deck = Deck()
    hole_cards = [deck.draw_card() for _ in range(num_players * 2)]
    players = {f"Player {i+1}": [hole_cards[i*2], hole_cards[i*2+1]] for i in range(num_players)}
    community = [deck.draw_card() for _ in range(5)]

    results = []
    for name, hand in players.items():
        rank, tiebreakers = PokerHandEvaluator.evaluate_five_card_hand(hand, community)
        results.append((name, rank, tiebreakers, hand))

    results.sort(key=lambda x: (x[1], x[2]), reverse=True)
    winner = results[0]
    runner_up = results[1]

    # Validate that winner's rank is not lower than runner-up
    if winner[1] < runner_up[1]:
        print(f"[ERROR] Wrong winner: {winner[0]} beat {runner_up[0]}")
        print("Community:", [str(c) for c in community])
        for name, rank, tb, hand in results:
            print(f"{name}: {list(hand_ranks.keys())[rank]} ({rank}), Hand: {[str(c) for c in hand]}, Tiebreakers: {tb}")
        return False
    return True

# Run multiple games
failures = 0
rounds = 10000

print(f"\n🧪 Running {rounds} stress test rounds...\n")

for i in range(rounds):
    if not simulate_game():
        failures += 1

print(f"\n✅ Completed {rounds} rounds.")
if failures == 0:
    print("🎉 All evaluations passed.")
else:
    print(f"❌ {failures} hands were ranked incorrectly.")
