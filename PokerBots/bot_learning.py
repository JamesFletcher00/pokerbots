import matplotlib.pyplot as plt
import os
import json

def plot_bot_wins(bot_name):
    filepath = f"training_logs/{bot_name}_history.json"

    if not os.path.exists(filepath):
        print(f"[WARNING] No log found for {bot_name}")
        return

    with open(filepath, "r") as f:
        data = json.load(f)

    cumulative_wins = []
    total_wins = 0

    for entry in data:
        win_type = entry.get("win_type", "")
        done = entry.get("done", False)

        # Count only when it's a final round-winning entry
        if win_type in ["fold", "showdown"] and done:
            total_wins += 1
            cumulative_wins.append(total_wins)

    rounds = list(range(1, len(cumulative_wins) + 1))
    plt.plot(rounds, cumulative_wins, label=bot_name)
    if rounds:
        plt.text(rounds[-1] + 0.5, cumulative_wins[-1], f"{bot_name}: {cumulative_wins[-1]} wins",
                 fontsize=9, verticalalignment='center')

def plot_all_bot_wins(bot_names):
    plt.figure(figsize=(12, 6))

    for name in bot_names:
        plot_bot_wins(name)

    plt.title("Cumulative Wins Per Round")
    plt.xlabel("Rounds Played")
    plt.ylabel("Total Wins")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    bot_names = ["AIan", "AIleen", "AInsley", "AbigAIl"]
    plot_all_bot_wins(bot_names)
