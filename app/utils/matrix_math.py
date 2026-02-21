from typing import List


def mod_distance(a: int, b: int, mod: int) -> int:
    return (b - a) % mod


def rotate(values: List[int], steps: int) -> List[int]:
    if not values:
        return values
    steps %= len(values)
    return values[-steps:] + values[:-steps]
