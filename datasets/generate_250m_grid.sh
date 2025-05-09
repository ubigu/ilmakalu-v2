#!/bin/sh

set -e

xmin=61000
xmax=733000
ymin=6605000
ymax=7777000

# Generate 250m grid
output_dir="grid_1km"
grid1km_wfs_addr="https://geo.stat.fi/geoserver/tilastointialueet/wfs"
grid1km_wfs_layer="tilastointialueet:hila1km"
grid1km_shape="${output_dir}/grid_1km.shp"
grid1km_tiff="${output_dir}/grid_1km.tiff"
grid250m_tiff="${output_dir}/grid_250m.tiff"
grid250m_shape_temp="${output_dir}/grid_250m_temp.shp"
grid250m_shape="${output_dir}/grid_250m.shp"

python="../venv/bin/python"

if ! [ -d "$output_dir" ]; then
    mkdir "$output_dir"
fi

# obtain vector layer
echo "Obtaining 1km grid (WFS), output: $grid1km_shape"
ogr2ogr -f "ESRI Shapefile" $grid1km_shape WFS:"$grid1km_wfs_addr" "$grid1km_wfs_layer"

# rasterize grid
echo "Rasterizing grid, output: ${grid1km_tiff}"
gdal_rasterize -dialect sqlite -sql "SELECT nro, CENTROID(geometry) FROM grid_1km" -tr 1000 1000 -f GTiff -a nro "$grid1km_shape" "$grid1km_tiff"

# upsample
echo "Sampling up, obtaining 250m grid: ${grid250m_tiff}"
gdalwarp -overwrite -ot UInt32 -te $xmin $ymin $xmax $ymax -tr 250 250 -f GTiff "$grid1km_tiff" "$grid250m_tiff"

# generate artificial id:s (running number) to aviod combining polygons
echo "Tweak attributes (add monotonically increasing id to avoid combination of polygons in polygonizing)"
$python raster_attribute_tweak.py

# polygonize (features are not important at this stage)
echo "Polygonize, result: $grid250m_shape_temp"
gdal_polygonize.py ${output_dir}/grid_250m_consecutive.tiff $grid250m_shape_temp

# label cells with "xyind" -attribute
echo "Add required attributes. Output: $grid250m_shape"
ogr2ogr -f "ESRI Shapefile" $grid250m_shape \
    -dialect sqlite \
    -sql 'select printf("%06i%07i", st_x(centroid(geometry)), st_y(centroid(geometry))) as xyind, st_x(centroid(geometry)) as xind, st_y(centroid(geometry)) as yind, geometry from grid_250m_temp' \
    $grid250m_shape_temp

# check result
echo "Verifying result (takes some time)"
ogrinfo -dialect sqlite -sql 'select distinct area(geometry) from grid_250m' $grid250m_shape grid_250m
