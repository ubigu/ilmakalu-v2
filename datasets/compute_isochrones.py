"""Prototype script to run router and isochrone computations"""

import json
import sys
from pathlib import Path


from modules.isochrone import DistanceSolver, Point, IsochroneCalc, IsochroneConfig, RouteConfig, RouteCalc
from modules.centers import RoutingResult, UrbanCenters, IsochroneResult, GridCells
from modules.config import Config
from tqdm import tqdm
import logging

logging.basicConfig(filename="isochrone_computation.log", level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # read grid cells
    cfg = Config("local_dev")
    uc = UrbanCenters(cfg.db_url())
    municipality = "049"
    gc = GridCells(cfg.db_url(), municipality)
    dsc = DistanceSolver(gc, uc, RouteConfig())

    grid_ids = dsc.grid_ids()
    # debug Pirkkala case
    #grid_ids = ['3466256798375']
    # index is 289
    #grid_ids=grid_ids[280:300]
    for g_id in tqdm(grid_ids):
        logger.debug("Processing grid: {}".format(g_id))
        nsc = dsc.nearest_centers_beeline(g_id, 10)
        candidate = nsc.pop(0)
        candidate.set_dist_road(dsc.calc_route(candidate))
        result = dsc.compute_min_distance(candidate, nsc)
        dsc.save_route(result)

    df = dsc.routing_results()
    routing_result = RoutingResult(cfg.db_url())
    routing_result.persist(df, "data", "routing_results_{}".format(municipality))
    pass
    sys.exit()
    nsc_beeline = dsc.nearest_centers_beeline('3648756803125', 5)
    candidate = nsc_beeline.pop(0)
    candidate.set_dist_road(dsc.calc_route(candidate))
    result = dsc.compute_min_distance(candidate, nsc_beeline)
    pass

    # router configuration
    router_cfg = RouteConfig("graphhopper")
    point1 = Point(61.2337397064611, 24.201125316882337)
    point2 = Point(60.906906611698275, 21.483723561909205)
    router = RouteCalc(router_cfg)
    res = router.dist_km(router.calc(point1, point2))

    pass

    isoc_cfg = IsochroneConfig("graphhopper")
    point = Point(61.38871,24.183655)
    isoc = IsochroneCalc(isoc_cfg)
    res = isoc.calc(8000, point)
    outfile = Path(__file__).parent / "output/isoc_result.json"
    with open(outfile, "w") as file:
        json.dump(res, file)
    pass

    isochrone_result = IsochroneResult(cfg.db_url())

    # Compute isochrones for centers
    isochrone_cfg = IsochroneConfig("graphhopper")
    isochrone = IsochroneCalc(isochrone_cfg)

    #distances = range(1000, 20000, 500)
    distances = range(20000, 100000, 1000)
    for distance in tqdm(distances):
        for _, cnt in tqdm(uc.df().iterrows(), total=uc.df().shape[0], leave=False):
            id = cnt.get("fi_center_ref")
            point = cnt.get("geom")
            p = Point(point.y, point.x)
            result = isochrone.calc(distance, p)
            isochrone_result.add_row(id, distance, result)

        isochrone_result.persist(distance)