import torch
import os
import json
import sqlite3
from nfsp_agent import NFSPAgent

"""
Run The GameVisuals Script To Run Project
"""

class BotWrapper:
    """
    A wrapper around NFSPAgent that integrates:
    - Style-based behavior initialization
    - Reinforcement and imitation learning
    - Persistent experience logging (SQLite)
    - Opponent modeling and profiling
    """

    def __init__(self, name, style="default", state_size=20, action_size=3):
        self.name = name
        self.style = style
        self.agent = NFSPAgent(name, state_size, action_size)
        self.opponent_stats = {}     # Tracks opponents' action frequencies
        self.opponent_profiles = {}  # Categorizes opponents based on behavior
        os.makedirs("training_logs", exist_ok=True)
        self.db_path = f"training_logs/{name}_experiences.sqlite"
        self._init_db()

        # Style-specific Q-biasing
        self.agent.initialise_with_style(style)

        # Exploration adjustment based on style
        if style == "strategist":
            self.agent.epsilon = 0.05
        elif style == "novice":
            self.agent.epsilon = 0.3
        else:
            self.agent.epsilon = 0.1

        self.last_state_tensor = None
        self.last_chip_count = 1000

    def compute_policy_accuracy(self):
        """
        Evaluates how well the policy net replicates stored SL behavior.
        Returns:
            float: Proportion of correctly predicted actions.
        """
        if len(self.agent.sl_buffer.buffer) == 0:
            return 0.0

        correct = 0
        total = 0

        for state, true_action in self.agent.sl_buffer.buffer:
            with torch.no_grad():
                logits = self.agent.policy_net(state.unsqueeze(0))
                predicted_action = torch.argmax(logits).item()

            if predicted_action == int(true_action):
                correct += 1
            total += 1

        return correct / total
    
    #Uses the Q-network to select an action, then maps index to name.
    def decide_action(self, state_tensor, can_check=False):
        self.last_state_tensor = state_tensor
        action_index = self.agent.select_action(state_tensor, use_avg_policy=False)
        return self.index_to_action(action_index, can_check)

    #Maps action index to string label.
    def index_to_action(self, index, can_check):
        mapping = ["fold", "call", "raise"]
        action = mapping[index]
        if can_check and action == "call":
            return "check"
        return action
    
    #Stores both an RL tuple and a supervised (state, action) snapshot.
    def store_experience(self, state, action, reward, next_state, done):
        self.agent.store_rl((state, action, reward, next_state, done))
        self.agent.store_sl(state, action)

    #Stores a (state, action) pair for SL imitation training.
    def store_imitation(self, state, action):
        self.agent.store_sl(state, action)

    #Updates the final stored transition with a terminal reward.
    def store_final_reward(self, final_reward):
        if not self.agent.rl_buffer.buffer:
            return

        state, action, _, next_state, _ = self.agent.rl_buffer.buffer[-1]
        self.agent.rl_buffer.buffer[-1] = (state, action, final_reward, next_state, True)

    #Loads past experiences from disk, trains both Q and policy networks.
    def train(self, batch_size=32, gamma=0.99):
        experiences = self.load_experiences_from_sqlite(limit=10000)
        if len(experiences) < batch_size:
            print(f"[TRAIN] Not enough data to train {self.name}.")
            return

        self.agent.rl_buffer.buffer.clear()
        for exp in experiences:
            self.agent.rl_buffer.push(exp)

        self.agent.train_rl(batch_size, gamma)
        self.agent.train_policy(batch_size)
        print(f"[TRAIN] {self.name} trained on {len(experiences)} samples.")

    def save_experiences_to_sqlite(self, win_type="unknown"):
        """
        Persists the current RL buffer to SQLite for long-term training use.
        """
        data = list(self.agent.rl_buffer.buffer)
        if not data:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for state, action, reward, next_state, done in data:
            cursor.execute("""
                INSERT INTO bot_experiences 
                (bot_name, personality, state, action, reward, next_state, done, win_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.name,
                self.style,
                json.dumps(state.tolist()),
                int(action),
                float(reward),
                json.dumps(next_state.tolist()),
                bool(done),
                win_type
            ))

        conn.commit()
        conn.close()
        print(f"[SQLITE] {self.name} stored {len(data)} experiences.")

    #initialises the local SQLite database for storing transitions.
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_name TEXT,
                personality TEXT,
                state TEXT,
                action INTEGER,
                reward REAL,
                next_state TEXT,
                done BOOLEAN,
                win_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def load_experiences_from_sqlite(self, limit=10000):
        """
        Loads past transitions for replay training.
        Returns:
            list of (state, action, reward, next_state, done) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state, action, reward, next_state, done
            FROM bot_experiences
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        experiences = []
        for state, action, reward, next_state, done in rows:
            try:
                experiences.append((
                    torch.tensor(json.loads(state)),
                    int(action),
                    float(reward),
                    torch.tensor(json.loads(next_state)),
                    bool(done)
                ))
            except Exception:
                continue  # Skip bad data

        return experiences

    def update_opponent_profile(self):
        """
        Classifies each opponent into one of 4 profiles based on long-term stats:
        aggressive, tight, loose, or balanced.
        """
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
