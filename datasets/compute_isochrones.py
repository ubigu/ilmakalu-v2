"""Prototype script to run router and isochrone computations"""

import json
from pathlib import Path


from modules.isochrone import Point, IsochroneCalc, IsochroneConfig, RouteConfig, RouteCalc
from modules.centers import UrbanCenters, IsochroneResult
from modules.config import Config
from tqdm import tqdm

if __name__ == "__main__":
    
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

    cfg = Config("local_dev")
    uc = UrbanCenters(cfg.db_url())

    isochrone_result = IsochroneResult(cfg.db_url())

    # Compute isochrones for centers
    isochrone_cfg = IsochroneConfig("graphhopper")
    isochrone = IsochroneCalc(isochrone_cfg)

    distances = range(1000, 20000, 500)
    for distance in tqdm(distances):
        for _, cnt in tqdm(uc.df().iterrows(), total=uc.df().shape[0], leave=False):
            id = cnt.get("fi_center_ref")
            point = cnt.get("geom")
            p = Point(point.y, point.x)
            result = isochrone.calc(distance, p)
            isochrone_result.add_row(id, distance, result)

        isochrone_result.persist(distance)