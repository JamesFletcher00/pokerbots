import torch
import os
import json
from nfsp_agent import NFSPAgent

class BotWrapper:
    def __init__(self, name, style="default", state_size=7, action_size=3):
        self.name = name
        self.style = style
        self.agent = NFSPAgent(name, state_size, action_size)
        self.opponent_stats = {}
        self.opponent_profiles = {}

        # Initialize policy based on style
        self.agent.initialise_with_style(style)

        # Style-based exploration
        if style == "strategist":
            self.agent.epsilon = 0.05
        elif style == "novice":
            self.agent.epsilon = 0.3
        else:
            self.agent.epsilon = 0.1

        self.last_state_tensor = None
        self.last_chip_count = 1000  # Starting chip count; update this after each round

    def decide_action(self, state_tensor, can_check=False):
        """Choose action index and convert to action name."""
        self.last_state_tensor = state_tensor
        action_index = self.agent.select_action(state_tensor, use_avg_policy=False)
        return self.index_to_action(action_index, can_check)

    def index_to_action(self, index, can_check):
        """Maps action index to readable string. Index: 0=fold, 1=call/check, 2=raise."""
        mapping = ["fold", "call", "raise"]
        action = mapping[index]
        if can_check and action == "call":
            return "check"
        return action

    def store_experience(self, state, action, reward, next_state, done):
        """Stores an RL transition and SL snapshot."""
        self.agent.store_rl((state, action, reward, next_state, done))
        self.agent.store_sl(state, action)

    def store_imitation(self, state, action):
        self.agent.store_sl(state, action)

    def store_final_reward(self, final_reward):
        """Update the last experience with final reward and done=True."""
        if not self.agent.rl_buffer.buffer:
            return

        last_exp = self.agent.rl_buffer.buffer[-1]
        state, action, _, next_state, _ = last_exp
        self.agent.rl_buffer.buffer[-1] = (state, action, final_reward, next_state, True)

    def train(self, batch_size=32, gamma=0.99):
        """Train both RL and SL networks."""
        self.agent.train_rl(batch_size, gamma)
        self.agent.train_policy(batch_size)

    def save_experiences_to_json(self, filename=None, win_type="unknown"):
        """Save RL buffer to a JSON file."""
        data = list(self.agent.rl_buffer.buffer)
        serializable_data = []

        for state, action, reward, next_state, done in data:
            serializable_data.append({
                "personality": self.style,
                "state": state.tolist(),
                "action": int(action),
                "reward": float(reward),
                "next_state": next_state.tolist(),
                "done": bool(done),
                "win_type": win_type
            })

        os.makedirs("training_logs", exist_ok=True)
        if not filename:
            filename = f"{self.name}_history"

        filepath = os.path.join("training_logs", f"{filename}.json")

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                existing = json.load(f)
        else:
            existing = []

        existing.extend(serializable_data)

        with open(filepath, "w") as f:
            json.dump(existing, f, indent=2)

        print(f"[LOG] Appended {len(serializable_data)} entries to {filepath}")

    def update_opponent_profile(self):
        for name, stats in self.opponent_stats.items():
            rounds = max(1, stats.get("rounds", 1))
            raise_rate = stats.get("raise", 0) / rounds
            fold_rate = stats.get("fold", 0) / rounds
            call_rate = stats.get("call", 0) / rounds

            if raise_rate > 0.4:
                profile = "aggressive"
            elif fold_rate > 0.5:
                profile = "tight"
            elif call_rate > 0.5 and raise_rate < 0.2:
                profile = "loose"
            else:
                profile = "balanced"

            self.opponent_profiles[name] = profile

