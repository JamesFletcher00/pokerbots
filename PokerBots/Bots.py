import torch
from nfsp_agent import NFSPAgent

class BotWrapper:
    def __init__(self, name, style="default", state_size=4, action_size=3):
        self.agent = NFSPAgent(name, state_size, action_size)

    def decide_action(self, state_tensor, can_check=False):
        action_index = self.agent.select_action(state_tensor, use_avg_policy=False)
        return self.index_to_action(action_index, can_check)
    
    def index_to_action(self,index, can_check):
        mapping = ["fold", "call", "raise"]
        if can_check and index ==1:
            return "check"
        return mapping[index]

    def store_experience(self, state, action, reward, next_state, done):
        self.agent.store_rl((state, action, reward, next_state, done))
        self.agent.store_sl(state, action)

    def train(self, batch_size=32, gamma=0.99):
        self.agent.train_rl(batch_size, gamma)
        self.agent.train_policy(batch_size)