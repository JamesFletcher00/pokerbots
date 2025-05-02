import matplotlib.pyplot as plt
import os
import json

def load_win_counts():
    path = "training_logs/game_wins.json"
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        return json.load(f)



def plot_bot_wins_pie(bot_names, save_path="None"):
    win_data = load_win_counts()

    labels = []
    win_counts = []

    for name in bot_names:
        wins = win_data.get(name, 0)
        if wins > 0:
            labels.append(name)
            win_counts.append(wins)

    if not win_counts:
        print("No wins recorded for any bots.")
        return

    def format_label(pct, all_vals):
        total = sum(all_vals)
        count = int(round(pct * total / 100.0))
        return f'{pct:.1f}% ({count})'

    plt.figure(figsize=(8, 8))
    plt.pie(
        win_counts,
        labels=labels,
        autopct=lambda pct: format_label(pct, win_counts),
        startangle=140
    )
    plt.title("Total Wins by Poker Bot")
    plt.axis('equal')
    if save_path:
        plt.savefig(save_path)
        print(f"[SAVED] Pie chart saved to {save_path}")
        plt.close()
    else:
        plt.tight_layout()
        plt.show()

def plot_round_win_pie(save_path="round_wins.png"):
    path = "training_logs/round_wins.json"
    if not os.path.exists(path):
        print("[ROUND PIE] No round_wins.json found.")
        return

    with open(path, "r") as f:
        win_data = json.load(f)

    if not win_data:
        print("[ROUND PIE] No wins to plot.")
        return

    # Prepare data for each win type
    win_types = ["fold", "showdown"]
    for win_type in win_types:
        labels = []
        counts = []
        for bot, wins in win_data.items():
            count = wins.get(win_type, 0)
            if count > 0:
                labels.append(bot)
                counts.append(count)

        if counts:
            def format_label(pct, all_vals):
                total = sum(all_vals)
                count = int(round(pct * total / 100.0))
                return f'{pct:.1f}% ({count})'

            plt.figure(figsize=(8, 8))
            plt.pie(counts, labels=labels, autopct=lambda pct: format_label(pct, counts), startangle=140)
            plt.title(f"Total Round Wins by {win_type.capitalize()}")
            plt.axis('equal')
            chart_path = save_path.replace(".png", f"_{win_type}.png")
            plt.savefig(chart_path)
            print(f"[ROUND PIE] Saved pie chart to {chart_path}")
            plt.close()
        else:
            print(f"[ROUND PIE] No {win_type} wins to plot.")


if __name__ == "__main__":
    bot_names = ["novice", "agressive", "conservative", "strategist"]
    plot_bot_wins_pie(bot_names)
    plot_round_win_pie(bot_names)
