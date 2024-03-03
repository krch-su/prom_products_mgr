from dataclasses import dataclass
from typing import List


@dataclass
class ProductFeatures:
    title: str
    features: List[str]
