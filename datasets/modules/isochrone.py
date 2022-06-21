"""Module to handle isochrone calculation"""

from __future__ import annotations
from modules.centers import GridCells, UrbanCenters
from modules.config import Config
from haversine import haversine
import pandas as pd
import requests
import pyjq
import itertools

class Point:
    def __init__(self, lat, lon):
        self._lat = lat
        self._lon = lon

    def lat(self):
        return self._lat

    def lon(self):
        return self._lon

    def coords (self):
        """Obtain coordinate tuple"""
        return (self.lon(), self.lat())

    def __repr__(self):
        return "Point({})".format(self.coords())

    def __str__(self):
        self.__repr__()
class Route:
    def __init__(self, from_point : Point, to_point : Point, beeline_dist : float = None):
        self._from_point = from_point
        self._to_point = to_point
        self._dist_beeline = beeline_dist
        self._from_id = None
        self._dest_id = None
        # distance computed
        self._dist_road = None

    def with_source_id(self, id):
        self._from_id = id
        return self

    def with_dest_id(self, id):
        self._dest_id = id
        return self

    def dist_beeline(self) -> float:
        return self._dist_beeline

    def dist_road(self) -> float:
        return self._dist_road

    def __repr__(self):
        if self.dist_road() is None:
            return "Route(beeline: {0:.1f})".format(self.dist_beeline())
        else:
            return "Route(beeline: {0:.1f}, road: {1:.1f})".format(self.dist_beeline(), self.dist_road())

    def __str__(self):
        self.__repr__()

class DistanceSolverConfig:
    """DistanceSolver configuration module"""
    def __init__(self):
        pass

class DistanceSolver:
    """DistanceSolver handles distance calculation between grid cells and center points."""
    def __init__(
        self,
        grid : GridCells = None,
        centers : UrbanCenters = None,
        routerconfig : RouteConfig = None
        ):

        self._grid = grid
        self._centers = centers
        self._rt_config = routerconfig
        self._router = RouteCalc(self._rt_config)
        g_head = grid.df().head()
        u_head = centers.df().head()
        pairs = itertools.product(g_head['geom'], u_head['geom'])
        pass

    def nearest_centers_beeline(self, xyind : str = None, num_routes : int = 10) -> pd.DataFrame:
        df =self.grid().df()
        # find one specific grid cell
        g = df[df['xyind'] == xyind]

        # find distance to urban centers

        from_point = Point(g["geom"].y.iat[0], g["geom"].x.iat[0])
        ## construct ordered list (decreasing beeline)
        router_points = []
        for _, cnt_p in self.centers().df().iterrows():
            to_point = Point(cnt_p["geom"].y, cnt_p["geom"].x)
            beeline_dist = haversine(from_point.coords(), to_point.coords())
            r = Route(from_point, to_point, beeline_dist).with_source_id(xyind).with_dest_id(cnt_p["fi_center_ref"])

            router_points.append(r)

        router_points.sort(key=lambda r: r.dist_beeline())

        return router_points[:num_routes]

    def grid(self):
        return self._grid

    def centers(self):
        return self._centers

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
    def __init__(self, router_config : RouteConfig = None):
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

    # service provider specific functionality
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

    # service provider specific functionality
    def _graphhopper_postprocess(self):
        """Return GeoJSON result from (possibly) proprietary format."""
        result = pyjq.first(".polygons[]", self._result)
        return result
