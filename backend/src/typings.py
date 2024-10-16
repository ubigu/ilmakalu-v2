from typing import Literal, NotRequired, TypedDict


class Point(TypedDict):
    type: Literal["Point"]
    coordinates: list[float]


class LineString(TypedDict):
    type: Literal["LineString"]
    coordinates: list[list[float]]


class Polygon(TypedDict):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]


class MultiPoint(TypedDict):
    type: Literal["MultiPoint"]
    coordinates: list[list[float]]


class MultiLineString(TypedDict):
    type: Literal["MultiLineString"]
    coordinates: list[list[list[float]]]


class MultiPolygon(TypedDict):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[list[float]]]]


class Feature(TypedDict):
    geometry: Point | LineString | Polygon | MultiPoint | MultiLineString | MultiPolygon
    id: NotRequired[str | int]
    properties: dict


class FeatureCollection(TypedDict):
    type: Literal["FeatureCollection"]
    features: list[Feature]


class UserInput(TypedDict):
    aoi: NotRequired[list[Feature] | FeatureCollection]
    plan_areas: NotRequired[list[Feature] | FeatureCollection]
    plan_transit: NotRequired[list[Feature] | FeatureCollection]
    plan_centers: NotRequired[list[Feature] | FeatureCollection]
