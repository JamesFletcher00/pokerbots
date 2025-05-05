import torch
import torch.nn as nn
import torch.optim as optim
import random
from Experience import ReplayBuffer

class SimpleMLP(nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, output_size)
        )

    def forward(self, x):
        return self.net(x)
    
class NFSPAgent:
    def __init__(self, name, state_size, action_size, rl_buffer_size=50000, sl_buffer_size=50000, epsilon=0.1):
        self.name = name
        self.state_size = state_size
        self.action_size = action_size
        self.epsilon = epsilon

        self.q_net = SimpleMLP(state_size, action_size)
        self.q_optimiser = optim.Adam(self.q_net.parameters(), lr=1e-3)

        self.policy_net = SimpleMLP(state_size, action_size)
        self.policy_optimiser = optim.Adam(self.policy_net.parameters(), lr=1e-3)

        self.rl_buffer = ReplayBuffer(rl_buffer_size)
        self.sl_buffer = ReplayBuffer(sl_buffer_size)

        self.loss_fn = nn.MSELoss()
        self.ce_loss = nn.CrossEntropyLoss()

    def initialise_with_style(self, style):
        with torch.no_grad():
            if style == "novice":
                # Bias toward folding early on
                self.q_net.net[-1].bias[0] += 0.5  # Fold action
            elif style == "aggressive":
                # Bias toward raising
                self.q_net.net[-1].bias[2] += 0.5  # Raise action
            elif style == "conservative":
                # Bias toward calling or checking
                self.q_net.net[-1].bias[1] += 0.5  # Call action
            elif style == "strategist":
                # No strong bias — learns naturally
                pass

    def select_action(self, state, use_avg_policy=False):
        if use_avg_policy:
            with torch.no_grad():
                logits = self.policy_net(state.unsqueeze(0))
            probs = torch.softmax(logits, dim=1)
            return torch.multinomial(probs, num_samples=1).item()
        else:
            if random.random() < self.epsilon:
                return random.randint(0, self.action_size - 1)
            with torch.no_grad():
                q_values = self.q_net(state.unsqueeze(0))
            return q_values.argmax(dim=1).item()
        
    def store_rl(self, transition):
        self.rl_buffer.push(transition)

    def store_sl(self, state, action):
        self.sl_buffer.push((state, action))
        print(len(self.sl_buffer.buffer))  # should be thousands by now

    def train_rl(self, batch_size=8, gamma=0.99):
        batch = self.rl_buffer.sample(batch_size)
        if len(batch) < batch_size:
            return
        
        states, actions, rewards, next_states, dones = zip(*batch)
        states = torch.stack(states)
        actions = torch.tensor(actions)
        rewards = torch.tensor(rewards, dtype=torch.float32)
        next_states = torch.stack(next_states)
        dones = torch.tensor(dones, dtype=torch.float32)

        q_values = self.q_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        next_q_values = self.q_net(next_states).max(1)[0].detach()
        targets = rewards + gamma * next_q_values * (1 - dones)

        loss = self.loss_fn(q_values, targets)
        self.q_optimiser.zero_grad()
        loss.backward()
        self.q_optimiser.step()

    def train_policy(self, batch_size=8):
        batch = self.sl_buffer.sample(batch_size)
        if len(batch) < batch_size:
            print("[TRAIN_POLICY] Skipped — not enough samples.")
            return
        
        states, actions = zip(*batch)
        states = torch.stack(states)
        actions = torch.tensor(actions)

        logits = self.policy_net(states)
        loss = self.ce_loss(logits, actions)

        self.policy_optimiser.zero_grad()
        loss.backward()
        self.policy_optimiser.step()
        
        print(f"[TRAIN_POLICY] Trained policy with loss: {loss.item():.4f}")
