from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class CameraFrame:
    data: np.ndarray
    width: int
    height: int
    image_format: str
    id: int # UNIQUE (used for invalidation etc..)