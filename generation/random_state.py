"""
FinSight Enterprise — Deterministic Random State Manager
Ensures 100% reproducible contract generation across runs.
"""

import random
import numpy as np


class DeterministicRandomState:
    def __init__(self, seed: int = 20261006):
        self.seed = seed
        self.py_random = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

    def reset(self):
        """Resets the generators back to the initial seed state."""
        self.py_random = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

    def choice(self, seq):
        return self.py_random.choice(seq)

    def choices(self, population, weights=None, k=1):
        return self.py_random.choices(population, weights=weights, k=k)

    def uniform(self, a, b):
        return self.py_random.uniform(a, b)

    def randint(self, a, b):
        return self.py_random.randint(a, b)

    def gauss(self, mu, sigma):
        return self.py_random.gauss(mu, sigma)

    def sample(self, population, k):
        return self.py_random.sample(population, k)
