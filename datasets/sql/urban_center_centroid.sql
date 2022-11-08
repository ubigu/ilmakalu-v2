DROP TABLE IF EXISTS data.fi_center_p;
CREATE TABLE data.fi_center_p AS
SELECT
    ogc_fid AS fi_center_ref,
    ST_Centroid(wkb_geometry) AS geom
FROM data.fi_centers;
