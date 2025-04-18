import torch

class BotA:
    def __init__(self,name = "BotA"):
        self.name = name

    def decide_action(self, state_tensor):
        hand_strength = state_tensor[0].item()

        if hand_strength > 0.8:
            return "raise"
        elif hand_strength > 0.4:
            return "call"
        else:
            return "fold"
        
class BotB:
    def __init__(self, name="BotB"):
        self.name = name

    def decide_action(self, state_tensor):
        hand_strength = state_tensor[0].item()
        position_index = state_tensor[1].item()  # 0 = dealer, higher = early position

        # Position-aware thresholds
        if position_index >= 2:  # Early position (e.g., SB or BB)
            if hand_strength > 0.85:
                return "raise"
            elif hand_strength > 0.6:
                return "call"
            else:
                return "fold"
        else:  # Late position
            if hand_strength > 0.7:
                return "raise"
            elif hand_strength > 0.3:
                return "call"
            else:
                return "fold"
