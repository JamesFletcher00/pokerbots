import matplotlib.pyplot as plt
import os
import json

def plot_bot_learning(bot_name):
    filepath = f"training_logs/{bot_name}_history.json"

    if not os.path.exists(filepath):
        print(f"no log found for {bot_name}")
        return
    
    with open(filepath, "r") as f:
        data = json.load(f)

    rewards = [entry["reward"] for entry in data]

    smoothed = []
    window = 10
    for i in range(len(rewards)):
        start = max(0, i - window)
        smoothed.append(sum(rewards[start:i+1]) / (i-start+1))

    plt.plot(smoothed, label = bot_name)

def plot_all_bots(bot_names):
    plt.figure(figsize=(10,6))

    for name in bot_names:
        plot_bot_learning(name)

    plt.title("PokerBot Learning Curves")
    plt.xlabel("Game Actions (smoothed)")
    plt.ylabel("Average Reward")
    plt.legend()
    plt.grid()
    plt.show()

if __name__ == "__main__":
    bot_names = ["AIan", "AIleen", "AInsley", "AbigAIl"]
    plot_all_bots(bot_names)