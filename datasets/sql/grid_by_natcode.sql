-- pick relevant grid cells for one municipality
-- use this result later on as a separate custom grid
SELECT
    m.natcode,
    m.namefin,
    g.xyind,
    g.wkb_geometry
FROM
    data.fi_municipality_2022_10k AS m
JOIN data.fi_grid_250m AS g
ON ST_Intersects(m.geom, g.wkb_geometry) WHERE m.natcode='635';