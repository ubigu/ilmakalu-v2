import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import requests.auth
from fiona.io import ZipMemoryFile
from shapely import distance
from shapely.geometry import MultiPolygon
from shapely.ops import nearest_points


class Grid:
    ZONE_MAPPINGS = {
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
    CRS = "EPSG:3067"
    GEOM_COL = "geom"

    def __init__(self, mun: int, centroids: gpd.GeoDataFrame):
        """Generate a 250x250 grid with additional information for the municipality

        :param mun: The municipality code of the target municipality
        :param centroids: The GeoDataFrame specifying the points of the centrums in Finland
        """
        mun_col = "kunnro2024"
        columns = [self.GEOM_COL, "xyind", "mun", "zone", "centdist", "holidayhouses"]

        try:
            grid = pd.read_csv(  # type: ignore
                f"https://geo.stat.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=tilastointialueet:hila250m_linkki&outputFormat=csv&cql_filter={mun_col}={mun}"
            ).drop_duplicates(subset=["euref_x", "euref_y"])

            if grid.empty:
                raise Exception

            grid[self.GEOM_COL] = grid.apply(lambda g: self.__point_to_multipolygon(g["euref_x"], g["euref_y"]), axis=1)  # type: ignore
            self.grid = gpd.GeoDataFrame(grid, geometry=self.GEOM_COL, crs=self.CRS).rename(columns={mun_col: "mun"})  # type: ignore
            self.__generate_xyind()
            self.__generate_centdist(centroids)
            self.__generate_ykr_zones()
            self.__generate_holiday_houses()
            self.grid = self.grid[columns]
        except Exception as e:
            print(e)
            self.grid = gpd.GeoDataFrame(columns=columns, geometry=self.GEOM_COL)  # type: ignore

    def __point_to_multipolygon(self, x: float, y: float) -> MultiPolygon:
        """Convert the bottom-left corner to a 250x250-square

        :param x: X-coordinate of the bottom-left corner
        :param y: Y-coordinate of the bottom-left corner
        :returns: A multipolygon object determining the square"""
        return MultiPolygon([(((x, y), (x, y + 250), (x + 250, y + 250), (x + 250, y)), [])])

    def __generate_xyind(self):
        """Generate xyind by concatenating the x and y coordinates of the square's centroid (EUREF-FIN EPSG:3067)"""
        self.grid["xyind"] = self.grid[self.GEOM_COL].centroid.apply(lambda c: str(round(c.x)) + str(round(c.y)))

    def __generate_centdist(self, centroids: gpd.GeoDataFrame):
        """Calculate the squares' distances to the nearest centroids in the centroids table in kilometers
        :param centroids: The GeoDataFrame specifying the points of the centrums in Finland
        """
        self.grid["centdist"] = self.grid[self.GEOM_COL].centroid.apply(
            lambda c: round(distance(c, nearest_points(c, centroids.geom.union_all())[1]) * 0.001)
        )

    def __generate_ykr_zones(self):
        """Try to generate a zone from the YKRVyohykkeet2022 data. If the zone is not found,
        use YKRKaupunkiMaaseutuLuokitus2018
        """
        ykr_cols = ["vyohselite", "Nimi"]
        for dataset, col in zip(["YKRVyohykkeet2022", "YKRKaupunkiMaaseutuLuokitus2018"], ykr_cols):
            r = requests.get(f"https://wwwd3.ymparisto.fi/d3/gis_data/spesific/{dataset}.zip")
            if not r.ok:
                raise Exception("Failed to import the zone data")
            with ZipMemoryFile(r.content) as memfile:
                with memfile.open() as src:
                    # Pick the zone from the intersection with the largest area
                    intersections = gpd.overlay(
                        self.grid[["id", "geom"]],
                        gpd.GeoDataFrame.from_features(src, crs=self.CRS)[["geometry", col]],
                        how="intersection",
                        keep_geom_type=False,
                    )
                    if "geometry" in intersections.columns:
                        intersections = intersections.sort_values(
                            by="geometry", key=lambda col: np.array([x.area for x in col])
                        )
                    intersections = intersections.drop_duplicates(subset="id", keep="last")
                    intersections[col] = intersections[col].str.lower()
                    self.grid = self.grid.merge(intersections[["id", col]], on="id", how="left")  # type: ignore
        # Drop the rows with no zone found. Should only happen rarely, e.g. when the area is sea
        self.grid = self.grid.dropna(subset=ykr_cols, how="all")  # type: ignore

        self.grid["zone"] = self.grid.apply(
            lambda g: self.ZONE_MAPPINGS[g["vyohselite"] if isinstance(g["vyohselite"], str) else g["Nimi"]], axis=1
        )

    def __generate_holiday_houses(self):
        """Import holiday houses data within the bounding box of the grid"""
        bbox = ",".join(str(x) for x in self.grid.total_bounds)
        crs_url = "http://www.opengis.net/def/crs/EPSG/0/3067"
        url = f"https://avoin-paikkatieto.maanmittauslaitos.fi/maastotiedot/features/v1/collections/rakennus/items?kohdeluokka=42230,42231,42232&limit=10000&crs={crs_url}&bbox={bbox}&bbox-crs={crs_url}"

        houses = gpd.GeoDataFrame(columns=["geometry"])
        while url is not None:
            r = requests.get(url, auth=requests.auth.HTTPBasicAuth("fcd382c7-6e0c-44bc-9a54-f6406f36196e", ""))
            if not r.ok:
                raise Exception("Failed to import the holiday houses data")
            data = r.json()
            houses = gpd.GeoDataFrame(
                pd.concat([houses, gpd.GeoDataFrame.from_features(data, crs=self.CRS)]), crs=self.CRS
            )  # type: ignore
            url = next((link for link in data["links"] if link["rel"] == "next"), {"href": None})["href"]
        self.grid["holidayhouses"] = self.grid[self.GEOM_COL].apply(lambda g: np.sum(houses["geometry"].intersects(g)))  # type: ignore

    def get(self):
        return self.grid
