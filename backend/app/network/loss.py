"""Packet loss simulation for UDP transmission and reception."""

from dataclasses import dataclass, field
import random
from typing import Optional, Set


@dataclass
class PacketLossSimulator:
    """Simulates UDP packet loss with seeded PRNG and deterministic drop hooks."""

    loss_percentage: float = 0.0
    seed: Optional[int] = None
    drop_indices: Set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def should_drop(self, frame_index: Optional[int] = None) -> bool:
        """Determine whether to drop a packet.

        Args:
            frame_index: The absolute frame index, if known.

        Returns:
            True if packet should be dropped, False otherwise.
        """
        # 1. Deterministic drop hook
        if frame_index is not None and frame_index in self.drop_indices:
            self.drop_indices.remove(frame_index)
            return True

        # 2. Probabilistic loss
        if self.loss_percentage <= 0.0:
            return False
        if self.loss_percentage >= 100.0:
            return True

        return (self.rng.random() * 100.0) < self.loss_percentage

