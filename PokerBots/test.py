from GameLogic import GameLoop, Player, Card

# Mock players with identical hands (will cause a tie)
p1 = Player("BotA", chips=0)
p2 = Player("BotB", chips=0)
p3 = Player("BotC", chips=0)

# Give them identical two pair hands: Jacks and Sixes
p1.hand = [Card("Jack", "Hearts"), Card("Six", "Spades")]
p2.hand = [Card("Jack", "Diamonds"), Card("Six", "Clubs")]
p3.hand = [Card("Jack", "Spades"), Card("Six", "Hearts")]

players = [p1, p2, p3]
game = GameLoop(player_objs=players)

# Set pot size and community cards to enforce tie
game.pot = 150
game.community_cards = [
    Card("Jack", "Clubs"), Card("Six", "Diamonds"), Card("Two", "Hearts"),
    Card("Three", "Spades"), Card("King", "Hearts")
]

# Run showdown
game.determine_winner()

# Check results
for p in game.players:
    print(f"{p.name}: Chips = {p.chips}")

# Expected output:
# Each player should get 50 chips
# Console log should say it's a split between all three
