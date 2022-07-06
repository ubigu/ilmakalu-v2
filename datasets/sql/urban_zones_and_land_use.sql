-- urban/rural on a grid
DROP TABLE IF EXISTS data.fi_grid_250m_urban_rural;
CREATE TABLE data.fi_grid_250m_urban_rural AS
SELECT xyind, luokka, g.wkb_geometry
FROM
    data.fi_grid_250m AS g
    LEFT JOIN data.fi_urban_rural AS ur
    ON ST_Intersects(ST_Centroid(g.wkb_geometry), ur.wkb_geometry);

CREATE INDEX data_fi_grid_250m_urban_rural_xyind_index ON data.fi_grid_250m_urban_rural(xyind);
CREATE INDEX data_fi_grid_250m_urban_rural_geom_index ON data.fi_grid_250m_urban_rural USING GIST(wkb_geometry);

COMMENT ON TABLE data.fi_grid_250m_urban_rural IS 'Urban/rural typology in 250m grid.';

-- urban zones on a grid
DROP TABLE IF EXISTS data.fi_grid_250m_urban_zones;
CREATE TABLE data.fi_grid_250m_urban_zones AS
SELECT xyind, vyoh, g.wkb_geometry
FROM
    data.fi_grid_250m AS g
    LEFT JOIN data.fi_urban_zones AS uz
    ON ST_Intersects(ST_Centroid(g.wkb_geometry), uz.wkb_geometry);

CREATE INDEX data_fi_grid_250m_urban_zones_xyind_index ON data.fi_grid_250m_urban_zones(xyind);
CREATE INDEX data_fi_grid_250m_urban_zones_geom_index ON data.fi_grid_250m_urban_zones USING GIST(wkb_geometry);

COMMENT ON TABLE data.fi_grid_250m_urban_zones IS 'Urban zones in 250m grid.';

-- land use template table for the whole country
-- populate first with Urban/Rural typology
DROP TABLE IF EXISTS data.fi_grid_250m_landuse_template;
CREATE TABLE data.fi_grid_250m_landuse_template AS
SELECT
    ur.xyind,
    CASE
        WHEN ur.luokka = 'K1' THEN 81
        WHEN ur.luokka = 'K2' THEN 82
        WHEN ur.luokka = 'K3' THEN 83
        WHEN ur.luokka = 'M4' THEN 84
        WHEN ur.luokka = 'M5' THEN 85
        WHEN ur.luokka = 'M6' THEN 86
        WHEN ur.luokka = 'M7' THEN 87
        ELSE NULL
    END AS zone,
    ur.wkb_geometry
FROM data.fi_grid_250m_urban_rural AS ur;

CREATE INDEX data_fi_grid_250m_landuse_template_xyind_index ON data.fi_grid_250m_landuse_template(xyind);

COMMENT ON TABLE data.fi_grid_250m_landuse_template IS 'Template for gridded land use table.';

-- Add urban zones information to template table (where applicable)
UPDATE data.fi_grid_250m_landuse_template AS slu
SET zone = vyoh
FROM data.fi_grid_250m_urban_zones AS uz
WHERE uz.xyind=slu.xyind AND uz.vyoh IS NOT NULL;

-- Corine subset for Finland
DROP TABLE IF EXISTS data.fi_corine;
CREATE TABLE data.fi_corine AS
WITH extent_fi AS
    (
        SELECT ST_Transform(St_SetSRID(ST_Extent(wkb_geometry), 3067), 3035) AS geom
        FROM data.fi_grid_250m
    )
    SELECT objectid, code_18, remark, area_ha, id, ST_Transform(shape,3067) AS geom
    FROM
        data.corine_land_cover_2018_eu AS c, extent_fi AS g
    WHERE ST_Intersects(c.shape, g.geom);

CREATE INDEX data_fi_corine_geom_index ON data.fi_corine USING GIST(geom);

COMMENT ON TABLE data.fi_corine IS 'Corine land use data for Finnish extent, projected to EPSG:3067.';

-- compute corine data to grid
-- first step: subdivide Corine geometries to smaller ones
DROP TABLE IF EXISTS data.fi_corine_subdivided;
CREATE TABLE data.fi_corine_subdivided AS
SELECT code_18, st_subdivide(geom) AS geom
FROM data.fi_corine;

CREATE INDEX data_fi_corine_subdivided_geom_idx ON data.fi_corine_subdivided USING GIST(geom);

COMMENT ON TABLE data.fi_corine_subdivided IS 'Subdivided Corine geometries (for easier processing).';

-- compute land use areas from subdivided table
DROP TABLE IF EXISTS data.fi_corine_grid_intersection;
CREATE TABLE data.fi_corine_grid_intersection AS
SELECT ST_Area(ST_Intersection(g.wkb_geometry, c.geom)) AS area, xyind, code_18
FROM data.fi_corine_subdivided AS c, data.fi_grid_250m AS g
WHERE ST_Intersects(c.geom, g.wkb_geometry);

CREATE INDEX data_fi_corine_grid_intersection_xyind_index ON data.fi_corine_grid_intersection(xyind);

COMMENT ON TABLE data.fi_corine_grid_intersection IS 'Finnish Corine data mapped (bun unaggregated) to 250m grid cells.';

-- Alternative approach: municipality focused corine
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

-- Convert landuse data from tall to wide
DROP TABLE IF EXISTS data.fi_corine_areas;
CREATE TABLE data.fi_corine_areas AS
SELECT
    xyind,
    COALESCE(MAX(area) FILTER (WHERE main_class = '1'), 0) AS land_area_1,
    COALESCE(MAX(area) FILTER (WHERE main_class = '2'), 0) AS land_area_2,
    COALESCE(MAX(area) FILTER (WHERE main_class = '3'), 0) AS land_area_3,
    COALESCE(MAX(area) FILTER (WHERE main_class = '4'), 0) AS land_area_4,
    COALESCE(MAX(area) FILTER (WHERE main_class = '5'), 0) AS land_area_5
FROM (
    SELECT xyind, main_class, SUM(area) as area
    FROM (
        SELECT xyind, area, substring(code_18 , 1, 1) AS main_class
        FROM data.fi_corine_grid_intersection
        ) as main_classes
    GROUP BY xyind, main_class ORDER BY xyind
    ) AS areas GROUP BY areas.xyind;

COMMENT ON TABLE data.fi_corine_areas IS 'Corine land cover areas summed under main classes in 250m grid.';

-- combine: grid, zones and landuse to one table
DROP TABLE IF EXISTS data.fi_grid_250m_landuse;
CREATE TABLE data.fi_grid_250m_landuse AS
SELECT ca.*, gz.zone, g.wkb_geometry AS geom
FROM
    data.fi_corine_areas AS ca
LEFT JOIN data.fi_grid_250m AS g
ON g.xyind = ca.xyind
JOIN data.fi_grid_250m_landuse_template AS gz
ON g.xyind=gz.xyind;

CREATE INDEX data_fi_grid_corine_250m_landuse_xyind_idx ON data.fi_grid_250m_landuse(xyind);
CREATE INDEX data_fi_grid_corine_250m_landuse_geom_idx ON data.fi_grid_250m_landuse USING GIST(geom);

COMMENT ON TABLE data.fi_grid_250m_landuse IS 'Land use variables gathered into one table';
