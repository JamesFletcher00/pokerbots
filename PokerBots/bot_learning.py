import matplotlib.pyplot as plt
import os
import json

def count_bot_wins(bot_name):
    filepath = f"training_logs/{bot_name}_history.json"

    if not os.path.exists(filepath):
        print(f"[WARNING] No log found for {bot_name}")
        return 0

    with open(filepath, "r") as f:
        data = json.load(f)

    wins = 0
    for entry in data:
        if entry.get("win_type") in ["fold", "showdown"]:
            wins += 1
    return wins

def format_label(pct, all_vals):
    total = sum(all_vals)
    count = int(round(pct * total / 100.0))
    return f'{pct:.1f}% ({count})'




def plot_bot_wins_pie(bot_names):
    labels = []
    win_counts = []

    for name in bot_names:
        wins = count_bot_wins(name)
        if wins > 0:
            labels.append(name)
            win_counts.append(wins)

    if not win_counts:
        print("No wins recorded for any bots.")
        return

    plt.figure(figsize=(8, 8))
    plt.pie(
        win_counts,
        labels=labels,
        autopct=lambda pct: format_label(pct, win_counts),
        startangle=140
    )
    plt.title("Total Wins by Poker Bot")
    plt.axis('equal')  # Equal aspect ratio makes pie circular.
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    bot_names = ["AIan", "AIleen", "AInsley", "AbigAIl"]
    plot_bot_wins_pie(bot_names)
