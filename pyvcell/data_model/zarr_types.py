from dataclasses import dataclass


@dataclass
class Channel:
    index: int
    label: str
    domain_name: str
    mean_values: list[float]
    min_values: list[float]
    max_values: list[float]
