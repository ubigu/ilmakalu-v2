from osgeo import gdal
import numpy as np

infile="grid_1km/grid_250m.tiff"
in_ds = gdal.Open(infile)

in_band = in_ds.GetRasterBand(1)

gtiff_driver = gdal.GetDriverByName('GTiff')
out_ds = gtiff_driver.Create('grid_1km/grid_250m_consecutive.tiff', in_band.XSize, in_band.YSize, 1, in_band.DataType)
out_ds.SetProjection(in_ds.GetProjection())
out_ds.SetGeoTransform(in_ds.GetGeoTransform())

in_data = in_band.ReadAsArray()

# obtain data and nodata
ndv = 0
in_masked = np.ma.masked_where(in_data == ndv, in_data)

in_ones = np.ma.array(np.ones(in_masked.shape), mask=in_masked.mask, fill_value=ndv)

in_ones_normal = np.ma.getdata(in_ones)

# set nodata values in ones array
in_ones_normal[in_ones.mask] = ndv

# compute cumulative attribute and set nodata where necessary
in_ones_cumulative = np.reshape(np.cumsum(in_ones_normal), in_ones_normal.shape)
in_ones_cumulative[in_ones.mask] = ndv

# put pieces together, i.e. create output layer
out_band = out_ds.GetRasterBand(1)
out_band.SetNoDataValue(ndv)
out_band.WriteArray(in_ones_cumulative)
out_band.FlushCache()
out_band.ComputeStatistics(False)
del out_ds