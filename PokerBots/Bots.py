import torch
from nfsp_agent import NFSPAgent
import json
import os

class BotWrapper:
    def __init__(self, name, style="default", state_size=4, action_size=3):
        self.name = name
        self.style = style
        self.agent = NFSPAgent(name, state_size, action_size)

    def decide_action(self, state_tensor, can_check=False):
        print(f"[{self.name}] STATE → {state_tensor.tolist()}")

        self.last_state_tensor = state_tensor
        action_index = self.agent.select_action(state_tensor, use_avg_policy=False)
        action = self.index_to_action(action_index, can_check)

        print(f"[{self.name}] DECISION → Action: {action} (Index: {action_index}), Can Check: {can_check}")
        return action


    def index_to_action(self, index, can_check):
        mapping = ["fold", "call", "raise"]
        action = mapping[index]

        if action == "raise":
            strength = self.last_state_tensor[0].item()
            if strength < 0.6:
                return "call"
        if can_check and action == "call":
            return "check"
        return action


    def store_experience(self, state, action, reward, next_state, done):
        self.agent.store_rl((state, action, reward, next_state, done))
        self.agent.store_sl(state, action)

    def train(self, batch_size=32, gamma=0.99):
        self.agent.train_rl(batch_size, gamma)
        self.agent.train_policy(batch_size)

    def save_experiences_to_json(self, filename=None):
        data = list(self.agent.rl_buffer.buffer)
        serializable_data = []

        for state, action, reward, next_state, done in data:
            serializable_data.append({
                "state": state.tolist(),
                "action": int(action),
                "reward": float(reward),
                "next_state": next_state.tolist(),
                "done": bool(done)
            })

        os.makedirs("training_logs", exist_ok=True)
        if not filename:
            filename = f"{self.name}_history"

        filepath = os.path.join("training_logs", f"{filename}.json")

        # Append to existing JSON if it exists
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                existing = json.load(f)
        else:
            existing = []

        existing.extend(serializable_data)

        with open(filepath, "w") as f:
            json.dump(existing, f, indent=2)

        print(f"[LOG] Appended {len(serializable_data)} entries to {filepath}")

