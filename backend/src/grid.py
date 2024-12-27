import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import requests.auth
from fiona.io import ZipMemoryFile
from shapely import distance
from shapely.geometry import MultiPolygon
from shapely.ops import nearest_points

zone_mappings = {
    "keskustan jalankulkuvyöhyke": 1,
    "keskustan reunavyöhyke": 2,
    "intensiivinen joukkoliikennevyöhyke": 3,
    "joukkoliikennevyöhyke": 4,
    "autovyöhyke": 5,
    "alakeskuksen jalankulkuvyöhyke": 10,
    "alakeskuksen jalankulkuvyöhyke/joukkoliikennevyöhyke": 11,
    "alakeskuksen jalankulkuvyöhyke/intensiivinen joukkoliikennevyöhyke": 12,
    "keskustan reunavyöhyke/joukkoliikennevyöhyke": 40,
    "keskustan reunavyöhyke/intensiivinen joukkoliikennevyöhyke": 41,
    "sisempi kaupunkialue": 81,
    "ulompi kaupunkialue": 82,
    "kaupungin kehysalue": 83,
    "maaseudun paikalliskeskukset": 84,
    "kaupungin läheinen maaseutu": 85,
    "ydinmaaseutu": 86,
    "harvaan asuttu maaseutu": 87,
}
crs = "EPSG:3067"
crs_url = "http://www.opengis.net/def/crs/EPSG/0/3067"


def __point_to_multipolygon(x: float, y: float) -> MultiPolygon:
    """Convert the bottom-left corner to a 250x250-square

    :param x: X-coordinate of the bottom-left corner
    :param y: Y-coordinate of the bottom-left corner
    :returns: A multipolygon object determining the square"""
    return MultiPolygon([(((x, y), (x, y + 250), (x + 250, y + 250), (x + 250, y)), [])])


def __import_ykr_zones(df: gpd.GeoDataFrame, dataset: str, target_col: str) -> gpd.GeoDataFrame:
    """Import a zip dataset from ymparisto.fi and insert it to the dataframe received as a parameter

    :param df: The target dataframe
    :filename: The name of the YKR dataset to be imported
    :target_col: The name of the column to be imported from the YKR dataset
    :returns: The target dataframe with the YKR data inserted"""
    r = requests.get(f"https://wwwd3.ymparisto.fi/d3/gis_data/spesific/{dataset}.zip")
    if not r.ok:
        return df

    with ZipMemoryFile(r.content) as memfile:
        with memfile.open() as src:
            df = df.sjoin(
                gpd.GeoDataFrame.from_features(src, crs=crs)[["geometry", target_col]], how="left", predicate="within"
            ).drop(columns=["index_right"])
    df[target_col] = df[target_col].str.lower()
    return df


def __import_holiday_houses(bbox: list[float]) -> gpd.GeoDataFrame:
    """Import holiday houses data within the bounding box received as a parameter

    :bbox: The bounding box as a list of the x and y coordinates of the bottom-left
    corner and the x and y coordinates of the upper-right corner, respectively
    :returns: The building data as a GeoDataFrame"""
    bbox_str = ",".join(str(x) for x in bbox)
    url = f"https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1/collections/rakennus/items?kohdeluokka=42230,42231,42232&limit=10000&crs={crs_url}&bbox={bbox_str}&bbox-crs={crs_url}"

    buildings = gpd.GeoDataFrame(columns=["geometry"])
    while url is not None:
        r = requests.get(url, auth=requests.auth.HTTPBasicAuth("fcd382c7-6e0c-44bc-9a54-f6406f36196e", ""))
        if not r.ok:
            raise Exception("Failed to import the building data")
        data = r.json()
        buildings = gpd.GeoDataFrame(pd.concat([buildings, gpd.GeoDataFrame.from_features(data, crs=crs)]), crs=crs)  # type: ignore
        url = next((link for link in data["links"] if link["rel"] == "next"), {"href": None})["href"]
    return buildings


def import_grid(mun: int, centroids: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Generate a 250x250 grid with additional information for the municipality

    :param mun: The municipality code of the target municipality
    :param centroids: The GeoDataFrame specifying the points of the centrums in Finland
    :returns: The generated grid data as a GeoDataFrame"""
    mun_col = "kunnro2024"
    geom_col = "geom"
    columns = [geom_col, "xyind", "mun", "zone", "centdist", "holidayhouses"]

    try:
        grid = pd.read_csv(  # type: ignore
            f"https://geo.stat.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=tilastointialueet:hila250m_linkki&outputFormat=csv&cql_filter={mun_col}={mun}"
        ).drop_duplicates(subset=["euref_x", "euref_y"])

        if grid.empty:
            raise Exception

        grid[geom_col] = grid.apply(lambda g: __point_to_multipolygon(g["euref_x"], g["euref_y"]), axis=1)
        grid: gpd.GeoDataFrame = gpd.GeoDataFrame(grid, geometry=geom_col, crs=crs).rename(columns={mun_col: "mun"})  # type: ignore

        # Generate xyind by concatenating the x and y coordinates of the square's centroid (EUREF-FIN EPSG:3067)
        grid["xyind"] = grid[geom_col].centroid.apply(lambda c: str(round(c.x)) + str(round(c.y)))

        # Calculate the squares' distances to the nearest centroids in the centroids table in kilometers
        grid["centdist"] = grid[geom_col].centroid.apply(
            lambda c: round(distance(c, nearest_points(c, centroids.geom.union_all())[1]) * 0.001)
        )

        # Try to generate a zone from the YKRVyohykkeet2022 data. If the zone is not found, use YKRKaupunkiMaaseutuLuokitus2018
        grid = __import_ykr_zones(grid, "YKRVyohykkeet2022", "vyohselite")
        grid = __import_ykr_zones(grid, "YKRKaupunkiMaaseutuLuokitus2018", "Nimi")
        grid["zone"] = grid.apply(
            lambda g: zone_mappings[g["vyohselite"] if isinstance(g["vyohselite"], str) else g["Nimi"]], axis=1
        )

        # Calculate a number of holiday buildings within each square
        houses = __import_holiday_houses(list(grid.total_bounds))
        grid["holidayhouses"] = grid[geom_col].apply(lambda g: np.sum(houses["geometry"].intersects(g)))  # type: ignore

        return grid[columns]  # type: ignore
    except Exception:
        return gpd.GeoDataFrame(columns=columns, geometry=geom_col)  # type: ignore
