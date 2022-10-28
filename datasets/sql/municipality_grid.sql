DROP TABLE IF EXISTS data.fi_grid_municipalities;

CREATE TABLE IF NOT EXISTS data.fi_grid_municipalities (
    fid SERIAL PRIMARY KEY,
    xyind CHAR(13),
    mun CHAR(3),
    zone BIGINT,
    centdist INTEGER,
    geom Geometry(Polygon, 3067)
);

INSERT INTO data.fi_grid_municipalities(
    xyind,
    mun,
    geom
)
SELECT
    g.xyind,
    m.natcode,
    g.wkb_geometry
FROM
    data.fi_grid_250m AS g,
    data.fi_municipality_2022_10k AS m
WHERE ST_Intersects(g.wkb_geometry, m.geom);

CREATE INDEX fi_grid_municipalities_geom_idx ON data.fi_grid_municipalities USING GIST (geom);
