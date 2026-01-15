import math

class BurnFactors:
    def __init__(self, base_cost: int, model_multiplier: float, size_factor: float, risk_multiplier: float):
        self.BaseCost = base_cost
        self.ModelMultiplier = model_multiplier
        self.SizeFactor = size_factor
        self.RiskMultiplier = risk_multiplier

def compute_burn(b: BurnFactors) -> int:
    raw = float(b.BaseCost) * b.ModelMultiplier * b.SizeFactor * b.RiskMultiplier
    return int(math.ceil(raw))
