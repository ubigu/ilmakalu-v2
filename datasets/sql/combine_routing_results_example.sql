DROP TABLE IF EXISTS data.routes_635;
CREATE TABLE data.routes_635 AS
SELECT r.xyind, r.fi_center_id, r.beeline_dist, r.road_dist, g.wkb_geometry, c.geom,
    ST_MakeLine(ST_Centroid(g.wkb_geometry), c.geom) AS line_geom
FROM
    data.routing_results_635 AS r
JOIN
    data.fi_center_p AS c
ON r.fi_center_id = c.fi_center_ref
JOIN
    data.fi_grid_250m AS g
ON r.xyind = g.xyind;