"""Module to perform interpolation."""
from dataclasses import dataclass
from functools import partial

@dataclass
class Point:
    """Helper class for interpolator."""
    time_as_year: int
    value: float

class Interpolation:
    """Class to perform interpolation.
    
    Initialize either with two points or with coefficient and intercept."""
    def __init__(self, p_0: Point = None, p_1: Point = None, k: float = None, b: float = None):
        self.interpolate = None
        match (p_0, p_1, k, b):
            case (p_0, p_1, None, None) if p_0 is not None and p_1 is not None:
                self.interpolate = self._interpolator(p_0, p_1)
            case (None, None, k, b) if k is not None and b is not None:
                self.interpolate = partial(self._interpolate, k, b)
            case _:
                raise ValueError("Wrong parameters")

    def _interpolate(self, k: float, b: float, x: float) -> float:
        return k * x + b

    def _interpolator(self, p_0: Point, p_1: Point):
        k = (p_1.value - p_0.value) / (p_1.time_as_year - p_0.time_as_year)
        # y = kx + b
        # b = y - kx
        b = p_1.value - k * p_1.time_as_year
        return partial(self._interpolate, k, b)