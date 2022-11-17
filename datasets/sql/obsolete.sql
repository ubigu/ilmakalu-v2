-- currently obsolete
-- remove these if they are not used

-- Alternative approach: municipality focused corine
-- Use this instead of: data.fi_corine_grid_intersection, if this
-- seems more appropriate.
-- clip exactly according to municipality borders
-- This cannot be achieved by first creating country-wide representation
-- Generate this kind of table on-the-fly, when needed.
DROP TABLE IF EXISTS data.fi_corine_grid_intersection_mun;
CREATE TABLE data.fi_corine_grid_intersection_mun AS
SELECT
    ST_Area(ST_Intersection(g.wkb_geometry, ST_Intersection(c.geom, m.geom))) AS area,
    xyind,
    code_18
FROM data.fi_corine_subdivided AS c, data.fi_grid_250m AS g, data.fi_municipality_2022_10k AS m
WHERE ST_Intersects(m.geom, g.wkb_geometry) AND ST_Intersects(c.geom, m.geom) AND ST_Intersects(c.geom, g.wkb_geometry)
AND m.namefin='Tampere';

COMMENT ON TABLE data.fi_corine_grid_intersection_mun IS 'Example of limiting Corine with selected municipality border geometry.';
