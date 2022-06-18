"""Module to handle isochrone calculation"""

from __future__ import annotations
from modules.config import Config
import requests
import pyjq


class Point:
    def __init__(self, lat, lon):
        self._lat = lat
        self._lon = lon

    def lat(self):
        return self._lat

    def lon(self):
        return self._lon

class RouteConfig:
    """Handle router specific configurations."""
    def __init__(self, worker : str = "graphhopper"):
        # ensure context aware processing later on
        self._worker = worker
        cfg = Config()

        if worker == "graphhopper":
            self._url = cfg.graphhopper_router_url()
        elif worker == "here":
            self._url = None
        else:
            self._url = None

    def url(self):
        return self._url

class RouteCalc:
    """Handle routing computation assignments with GraphHopper."""
    def __init__(self, router_config : IsochroneConfig = None):
        self._url = router_config.url()
        self._result = None

        # set postprocessing function
        # later on other engines should have their own postprocessing functions implemented
        if router_config._worker == "graphhopper":
            self._postprocess = self._graphhopper_postprocess
            self.dist_km = self._graphhopper_dist_km

    def calc(self, start_point : Point, end_point : Point):
        """Main workhorse for route calculation."""
        router_addr = self._fill_url(start_point, end_point)
        return self._execute_routing(router_addr)._postprocess()

    def _execute_routing(self, router_addr : str) -> RouteCalc:
        """Call routing engine"""
        req = requests.get(router_addr)
        if req.status_code == 200:
            self._result = req.json()
        return self

    def _fill_url(self, start_point, end_point) -> str:
        """Place point and distance to URL template."""
        return self._url.format(
            start_point.lat(),
            start_point.lon(),
            end_point.lat(),
            end_point.lon())

    # service provide specific functionality
    def _graphhopper_dist_km(self, data):
        """Return distance in kilometers"""
        return pyjq.first(".paths[].distance", data) / 1000.0

    def _graphhopper_postprocess(self):
        """Reservation for further postprocessing requirement"""
        return self._result

class IsochroneConfig:
    """Handle isochrone computation specific configurations."""
    def __init__(self, worker : str = "graphhopper"):
        # ensure context aware processing later on
        self._worker = worker
        cfg = Config()

        if worker == "graphhopper":
            self._url = cfg.graphhopper_isochrone_url()
        elif worker == "here":
            self._url = None
        else:
            self._url = None

    def url(self):
        return self._url

class IsochroneCalc:
    """Handle routing and isochrone computation assignments with GraphHopper (and Here later on)"""

    def __init__(self, isoc_config : IsochroneConfig = None):
        self._url = isoc_config.url()
        self._result = None

        # set postprocessing function
        # later on other engines should have their own postprocessing functions implemented
        if isoc_config._worker == "graphhopper":
            self._postprocess = self._graphhopper_postprocess

    def calc(self, distance : float = None, point : Point = None):
        """Main workhorse for isochrone calculation."""
        isochrone_addr = self._fill_url(point, distance)
        return self._execute_isochrone(isochrone_addr)._postprocess()

    def _execute_isochrone(self, isochrone_addr) -> IsochroneCalc:
        """Call isochrone computation."""
        req = requests.get(isochrone_addr)
        if req.status_code == 200:
            self._result = req.json()
        return self

    def _fill_url(self, point, distance) -> str:
        """Place point and distance to URL template."""
        return self._url.format(point.lat(), point.lon(), distance)

    # service provide specific functionality
    def _graphhopper_postprocess(self):
        """Return GeoJSON result from (possibly) proprietary format."""
        result = pyjq.first(".polygons[]", self._result)
        return result
