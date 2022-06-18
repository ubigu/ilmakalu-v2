"""Prototype script to run router and isochrone computations"""

import json
from pathlib import Path
import pyjq

from modules.isochrone import Point, IsochroneCalc, IsochroneConfig, RouteConfig, RouteCalc

if __name__ == "__main__":
    router_cfg = RouteConfig("graphhopper")
    point1 = Point(61.2337397064611, 24.201125316882337)
    point2 = Point(60.906906611698275, 21.483723561909205)
    router = RouteCalc(router_cfg)
    res = router.dist_km(router.calc(point1, point2))

    pass

    isoc_cfg = IsochroneConfig("graphhopper")
    point = Point(61.691795, 24.443093)
    isoc = IsochroneCalc(isoc_cfg)
    res = isoc.calc(10000, point)
    outfile = Path(__file__).parent / "output/isoc_result.json"
    with open(outfile, "w") as file:
        json.dump(res, file)
    pass