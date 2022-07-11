"""Prototype script to run router (and isochrone) computations"""

import json
import sys
from pathlib import Path


from modules.isochrone import DistanceSolver, RouteConfig
from modules.centers import RoutingResult, UrbanCenters, GridCells
from modules.config import Config
from tqdm import tqdm
import logging

logging.basicConfig(filename="isochrone_computation.log", level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_distance_to_urban_center(cfg : Config) -> None:
    """Compute distance to nearest urban center (via road network).
    
    Perform computation for all grid cells within given municipality.
    Examine results in QGIS or similar, for possible faults in snapping
    to road network. Visualization of beeline distance would reveal
    possible problems (search for un-explainable results)."""

    municipality = cfg.target_municipality()
    uc = UrbanCenters(cfg.db_url())
    
    gc = GridCells(cfg.db_url(), municipality)
    dsc = DistanceSolver(gc, uc, RouteConfig())

    # obtain grid ids
    grid_ids = dsc.grid_ids()

    # loop all grid cells
    logger.info("Processing cells")
    for g_id in tqdm(grid_ids):
        logger.debug("Processing grid: {}".format(g_id))
        nsc = dsc.nearest_centers_beeline(g_id, 10)
        candidate = nsc.pop(0)
        candidate.set_dist_road(dsc.calc_route(candidate))
        result = dsc.compute_min_distance(candidate, nsc)
        dsc.save_route(result)

    df = dsc.routing_results()
    logger.info("Saving results to database")
    routing_result = RoutingResult(cfg.db_url())
    routing_result.persist(df, "data", "routing_results_{}".format(municipality))

if __name__ == "__main__":
    cfg = Config("local_dev")
    compute_distance_to_urban_center(cfg)
