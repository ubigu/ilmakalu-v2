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
crs = 3067
crs_url = f"http://www.opengis.net/def/crs/EPSG/0/{crs}"


def __point_to_multipolygon(x, y):
    """Convert the bottom-left coordinate to a 250x250-square"""
    return MultiPolygon([(((x, y), (x, y + 250), (x + 250, y + 250), (x + 250, y)), [])])


def __import_ykr_zones(df, filename, target_col):
    r = requests.get(f"https://wwwd3.ymparisto.fi/d3/gis_data/spesific/{filename}.zip")
    if not r.ok:
        return df

    with ZipMemoryFile(r.content) as memfile:
        with memfile.open() as src:
            df = df.sjoin(
                gpd.GeoDataFrame.from_features(src, crs=crs)[["geometry", target_col]], how="left", predicate="within"
            ).drop(columns=["index_right"])
    df[target_col] = df[target_col].str.lower()
    return df


def __import_buildings(bbox):
    url = f"https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1/collections/rakennus/items?kohdeluokka=42230,42231,42232&limit=10000&crs={crs_url}&bbox={bbox}&bbox-crs={crs_url}"

    buildings = gpd.GeoDataFrame()
    while url is not None:
        r = requests.get(url, auth=requests.auth.HTTPBasicAuth("fcd382c7-6e0c-44bc-9a54-f6406f36196e", ""))
        data = r.json()
        buildings = pd.concat([buildings, gpd.GeoDataFrame.from_features(data, crs=crs)])
        url = next((link for link in data["links"] if link["rel"] == "next"), {"href": None})["href"]
    return buildings


def generate_grid(mun, centroids):
    mun_col = "kunnro2024"
    geom_col = "geom"

    grid = pd.read_csv(
        f"https://geo.stat.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=tilastointialueet:hila250m_linkki&outputFormat=csv&cql_filter={mun_col}={mun}"
    ).drop_duplicates(subset=["euref_x", "euref_y"])

    grid[geom_col] = grid.apply(lambda g: __point_to_multipolygon(g["euref_x"], g["euref_y"]), axis=1)
    grid = gpd.GeoDataFrame(grid, geometry=geom_col, crs=crs).rename(columns={mun_col: "mun"})

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
    buildings = __import_buildings(",".join(str(x) for x in grid.total_bounds))
    grid["holidayhouses"] = grid[geom_col].apply(lambda g: np.sum(buildings["geometry"].intersects(g)))

    return grid[[geom_col, "xyind", "mun", "zone", "centdist", "holidayhouses"]]
