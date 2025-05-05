import json
import matplotlib.pyplot as plt
from collections import defaultdict

# Load the data
with open("training_logs/accuracy_log.json", "r") as file:
    data = json.load(file)

# Filter data to include only rounds <= 9999
data = [entry for entry in data if entry["round"] <= 10999]

# Prepare data structures
bin_size = 1000
bins = defaultdict(lambda: defaultdict(list))

# Group data into 1000-round bins
for entry in data:
    round_num = entry["round"]
    bin_start = (round_num // bin_size) * bin_size
    bin_label = f"{bin_start}-{bin_start + bin_size - 1}"
    for agent in ["novice", "agressive", "conservative", "strategist"]:
        bins[bin_label][agent].append(entry[agent])

# Sort bin labels numerically by starting round
labels = sorted(bins.keys(), key=lambda x: int(x.split("-")[0]))

# Compute average accuracy per bin
average_scores = defaultdict(list)
for label in labels:
    for agent in ["novice", "agressive", "conservative", "strategist"]:
        scores = bins[label][agent]
        avg = sum(scores) / len(scores) if scores else 0
        average_scores[agent].append(avg)

# Plotting
plt.figure(figsize=(12, 6))
for agent, scores in average_scores.items():
    plt.plot(labels, scores, marker='o', label=agent)

plt.title("Average Accuracy per 1000 Rounds")
plt.xlabel("Round Interval")
plt.ylabel("Average Accuracy")
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save to file
plt.savefig("training_logs/avg_acc_score.png")
plt.close()
