import io

import fiona
import geopandas as gpd
import pandas as pd
import requests
from shapely import distance
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


def __import_ykr_zones(df, filename, target_col):
    r = requests.get(f"https://wwwd3.ymparisto.fi/d3/gis_data/spesific/{filename}.zip")
    if not r.ok:
        return df

    with fiona.BytesCollection(io.BytesIO(r.content).read()) as src:
        df = df.sjoin(
            gpd.GeoDataFrame.from_features(src, crs=3067)[["geometry", target_col]], how="left", predicate="within"
        ).drop(columns=["index_right"])
    df[target_col] = df[target_col].str.lower()
    return df


def generate_grid(mun, centroids):
    mun_col = "kunnro2024"
    hila250m_link = pd.read_csv(
        f"https://geo.stat.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=tilastointialueet:hila250m_linkki&outputFormat=csv&cql_filter={mun_col}={mun}"
    ).drop_duplicates(subset=["euref_x", "euref_y"])
    hila250m = gpd.read_file("data/hila250m_kaikki.gpkg")

    grid = pd.merge(hila250m_link, hila250m, how="left", on=["euref_x", "euref_y"])[["geometry", mun_col]].rename(
        columns={"geometry": "geom", mun_col: "mun"}
    )
    grid = gpd.GeoDataFrame(grid, geometry="geom", crs="epsg:3067")

    # Generate xyind by concatenating the x and y coordinates of the square's centroid (EUREF-FIN EPSG:3067)
    grid["xyind"] = grid["geom"].centroid.apply(lambda c: str(round(c.x)) + str(round(c.y)))

    # Calculate the squares' distances to the nearest centroids in the centroids table in kilometers
    grid["centdist"] = grid["geom"].centroid.apply(
        lambda c: round(distance(c, nearest_points(c, centroids.geom.union_all())[1]) * 0.001)
    )

    # Try to generate a zone from the YKRVyohykkeet2022 data. If the zone is not found, use YKRKaupunkiMaaseutuLuokitus2018
    grid = __import_ykr_zones(grid, "YKRVyohykkeet2022", "vyohselite")
    grid = __import_ykr_zones(grid, "YKRKaupunkiMaaseutuLuokitus2018", "Nimi")
    grid["zone"] = grid.apply(
        lambda g: zone_mappings[g["vyohselite"] if isinstance(g["vyohselite"], str) else g["Nimi"]], axis=1
    )

    return grid[["geom", "xyind", "mun", "zone", "centdist"]]
