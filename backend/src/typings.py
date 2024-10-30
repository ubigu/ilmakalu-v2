from typing import TypedDict

from pygeojson import Feature, FeatureCollection


class InputLayer(TypedDict):
    name: str
    base: str
    features: FeatureCollection | list[Feature]


class UserInput(TypedDict):
    layers: list[InputLayer]
