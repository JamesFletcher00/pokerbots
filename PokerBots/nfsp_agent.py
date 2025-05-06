import torch 
import torch.nn as nn
import torch.optim as optim
import random
from Experience import ReplayBuffer

"""
Run The GameVisuals Script To Run Project
"""

class SimpleMLP(nn.Module):
    """
    A basic Multi-Layer Perceptron (MLP) with one hidden layer.
    Used for both Q-network (RL) and policy network (SL).
    """
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
    """
    Implements a Neural Fictitious Self-Play (NFSP) agent with:
    - Q-learning for reinforcement learning (RL)
    - Supervised learning (SL) to imitate average strategies
    - Experience replay for both RL and SL
    """
    def __init__(self, name, state_size, action_size, rl_buffer_size=50000, sl_buffer_size=50000, epsilon=0.1):
        self.name = name
        self.state_size = state_size
        self.action_size = action_size
        self.epsilon = epsilon  # Exploration rate for epsilon-greedy RL

        # RL Q-network
        self.q_net = SimpleMLP(state_size, action_size)
        self.q_optimiser = optim.Adam(self.q_net.parameters(), lr=1e-3)

        # SL policy network
        self.policy_net = SimpleMLP(state_size, action_size)
        self.policy_optimiser = optim.Adam(self.policy_net.parameters(), lr=1e-3)

        # Replay buffers for RL and SL experiences
        self.rl_buffer = ReplayBuffer(rl_buffer_size)
        self.sl_buffer = ReplayBuffer(sl_buffer_size)

        # Loss functions
        self.loss_fn = nn.MSELoss()             # RL: value prediction
        self.ce_loss = nn.CrossEntropyLoss()    # SL: policy classification

    def initialise_with_style(self, style):
        """
        Optionally bias the Q-network's output layer to simulate initial playstyle tendencies.
        """
        with torch.no_grad():
            if style == "novice":
                self.q_net.net[-1].bias[0] += 0.5  
            elif style == "aggressive":
                self.q_net.net[-1].bias[2] += 0.5  
            elif style == "conservative":
                self.q_net.net[-1].bias[1] += 0.5  
            elif style == "strategist":
                pass  

    def select_action(self, state, use_avg_policy=False):
        """
        Selects an action based on either:
        - epsilon-greedy exploration over Q-values
        - sampling from policy network distribution
        """
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
        """
        Stores a (state, action, reward, next_state, done) tuple in the RL replay buffer.
        """
        self.rl_buffer.push(transition)

    def store_sl(self, state, action):
        """
        Stores a (state, action) pair in the SL buffer for imitation learning.
        """
        self.sl_buffer.push((state, action))
        print(len(self.sl_buffer.buffer))  # Debug: monitor SL buffer growth

    def train_rl(self, batch_size=8, gamma=0.99):
        """
        Trains the Q-network on a mini-batch of experience using the Bellman equation.
        """
        batch = self.rl_buffer.sample(batch_size)
        if len(batch) < batch_size:
            return
        
        # Unpack and preprocess batch
        states, actions, rewards, next_states, dones = zip(*batch)
        states = torch.stack(states)
        actions = torch.tensor(actions)
        rewards = torch.tensor(rewards, dtype=torch.float32)
        next_states = torch.stack(next_states)
        dones = torch.tensor(dones, dtype=torch.float32)

        # Compute Q-learning targets
        q_values = self.q_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        next_q_values = self.q_net(next_states).max(1)[0].detach()
        targets = rewards + gamma * next_q_values * (1 - dones)

        # Backpropagate loss
        loss = self.loss_fn(q_values, targets)
        self.q_optimiser.zero_grad()
        loss.backward()
        self.q_optimiser.step()

    def train_policy(self, batch_size=8):
        """
        Trains the policy network to imitate stored (state, action) pairs via cross-entropy loss.
        """
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
