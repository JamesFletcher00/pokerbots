from collections import deque
import random

"""
Run The GameVisuals Script To Run Project
"""

class ReplayBuffer:
    """
    A simple experience replay buffer supporting both:
    - Reinforcement Learning (RL)
    - Supervised Learning (SL)
    """
    
    #initialises the buffer with a maximum size.
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    #Adds a new experience tuple to the buffer.
    def push(self, item):
        self.buffer.append(item)

    #Randomly samples a batch of experiences.
    def sample(self, batch_size):
        return random.sample(self.buffer, min(len(self.buffer), batch_size))
    
    #Returns the current number of elements stored in the buffer.
    def __len__(self):
        return len(self.buffer)
