import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import cast

import geopandas as gpd
import pandas as pd
from fastapi import HTTPException, Response
from pygeojson import FeatureCollection
from sqlalchemy import URL, sql
from sqlalchemy.engine import RowMapping
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine, text

from db import engine
from grid import import_grid
from ilmakalu_typing import (
    CO2Body,
    CO2CalculateEmissionsLoopParams,
    CO2CalculateEmissionsParams,
    CO2GridProcessingParams,
    CO2Headers,
)
from models import user_input, user_output

geom_col = "geom"
crs = "EPSG:3067"


class CO2Query(ABC):
    """An abstract class containing all the common steps of each calculation type.
    The child classes must implement the get_stmt method, calling the right SQL function
    in the database"""

    def __init__(
        self,
        params: CO2GridProcessingParams | CO2CalculateEmissionsParams | CO2CalculateEmissionsLoopParams,
        headers: CO2Headers | None = None,
        body: CO2Body | None = None,
    ):
        """Constructor

        :param params: The HTTP parameters associated with the query
        :param headers: The HTTP headers
        :param body: The body of the POST request. Is expected to contain input layers or
        connection parameters

        :attr params: The parameters received on initialization
        :attr headers: The headers received on initialization
        :attr layers: A dictionary of input layers received in a body. Each layer is
        expected to contain properties 'feature', 'base' and 'name'
        :attr db: A database instance. If connection parameters are provided, creates a
        new one, otherwise uses the default one
        """
        if params.baseYear is not None and params.targetYear is not None and params.targetYear <= params.baseYear:
            raise HTTPException(status_code=400, detail="The base year should be smaller than the target year")

        try:
            self.params = params
            self.headers = headers

            self.layers = [] if body is None or "layers" not in body else json.loads(body["layers"])
            self.db = (
                engine
                if body is None or "connParams" not in body
                else create_engine(
                    URL.create(**({"drivername": "postgresql"} | json.loads(body["connParams"]))), poolclass=NullPool
                )
            )
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=repr(e))

    def __generate_grid(self, session: Session):
        """Iterate over the municipality codes and generate a grid for the municipality if it does not exist

        :param session: The active database session"""
        centroids = None
        grid = pd.DataFrame()

        for mun in self.params.mun:
            stmt = text("SELECT COUNT(xyind) FROM delineations.grid WHERE mun = :mun").bindparams(mun=mun)
            # Do not generate a grid if it already exists
            if session.exec(stmt).one()[0] > 0:
                continue
            if centroids is None:
                centroids = gpd.GeoDataFrame.from_postgis(
                    "SELECT geom, id FROM delineations.centroids", self.db, crs=crs
                )
            grid = pd.concat([grid, import_grid(mun, centroids)])

        if not grid.empty:
            gpd.GeoDataFrame(grid, geometry=geom_col, crs=crs).to_postgis(  # type: ignore
                "grid", self.db, schema="delineations", if_exists="append"
            )

    def __upload_layers(self):
        """Upload the input layers received in a request body to the database"""
        for layer in self.layers:
            if "features" not in layer or "name" not in layer:
                continue

            features = layer["features"]

            if isinstance(features, FeatureCollection):
                features = features.features

            df: gpd.GeoDataFrame = gpd.GeoDataFrame.from_features(features, crs=crs).rename_geometry(geom_col)  # type: ignore
            df.to_postgis(layer["name"], self.db, schema=user_input.schema, if_exists="replace")

    def __execute(self, session: Session) -> Response:
        """Execute the SQL statement defined by the get_stmt method and return the
        mappings as a Response object

        :param session: The active database session
        :returns: A Response object with the returned rows in a desired format
        """
        result = session.exec(self.get_stmt()).mappings().all()

        return Response(**self.__get_response_params(result))

    def __clean_up(self, session: Session):
        """Clean up the database after a successful calculation. That is,
        drop the inserted tables in the user_input schema

        :param session: The active database session
        """
        for layer in self.layers:
            if "name" not in layer:
                continue
            session.exec(text(f'DROP TABLE IF EXISTS {user_input.schema}."{layer["name"]}"'))

    def __get_response_params(self, result: list[RowMapping]) -> dict:
        """Construct the content and media_type parameters based on the desired output format.
        Possible formats are XML, GeoJSON or JSON (as a default)

        :param result: A list of mappings of the calculation result rows
        :returns: A dictionary containing the parameters
        """
        format = "json" if not isinstance(self.params.outputFormat, str) else self.params.outputFormat.lower()
        df = pd.DataFrame.from_records(result)

        match format:
            case "xml":
                return {"content": df.to_xml(index=False), "media_type": "application/xml"}
            case "geojson":
                if geom_col in df.columns:
                    df[geom_col] = gpd.GeoSeries.from_wkt(df[geom_col])
                else:
                    df.insert(0, geom_col, [])
                content = gpd.GeoDataFrame(df, geometry=geom_col, crs=crs).to_json(drop_id=True)  # type: ignore
                return {"content": content, "media_type": "application/geojson"}
            case _:
                return {"content": df.to_json(orient="records"), "media_type": "application/json"}

    def get_table_name(self, base: str, default: str | None) -> str | None:
        """Return the name of the input table associated with the base

        :param base: The name of the base (either aoi, plan_areas, plan_transit or plan_centers)
        :param default: The default name if the table was not found in the input_tables dictionary
        :returns: The name if found, otherwise the default
        """
        next_layer = next((layer for layer in self.layers if layer["base"] == base), None)
        return default if next_layer is None else user_input.schema + "." + next_layer["name"]

    def execute(self) -> Response:
        """Execute a CO2 calculation. Firstly, generate grids for the municipalities
        if they do not exist. Then, insert input layers to the database. Finally,
        execute the SQL statement defined in the get_stmt function of the child class.
        If successful, write session info, clean up and commit, otherwise rollback

        :returns: The result of the calculation as a response object
        """
        result = None
        try:
            with Session(self.db) as session:
                session.begin()
                try:
                    self.__generate_grid(session)
                    self.__upload_layers()
                    result = self.__execute(session)
                except Exception:
                    session.rollback()
                    raise
                else:
                    self.write_session_info(session)
                finally:
                    self.__clean_up(session)
                    session.commit()
            return result
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=str(e))

    @abstractmethod
    def get_stmt(self) -> sql.expression.TextClause:
        """An abstract method that should return a SQL statement corresponding the API
        endpoint. Is currently implemented by the CO2CalculateEmissions, CO2CalculateEmissionsLoop
        and CO2GridProcessing child classes at the routers subdirectory

        :returns: The SQL statement as a literal SQL text fragment
        """
        pass

    def write_session_info(self, session: Session):
        """Write the session info to the database. Should be implemented by the child class

        :param session: The active database session
        """
        pass


class CO2CalculateEmissionsBase(CO2Query):
    """A base class for the CO2CalculateEmissions and CO2CalculateEmissionsLoop classes.
    Inherits the methods from CO2Query and implement the write_session_info method that the
    children is expected to have in common
    """

    def write_session_info(self, session: Session):
        """Write the session info to the database if writeSessionInfo is true and
        headers are provided
        """

        p = cast(CO2CalculateEmissionsParams | CO2CalculateEmissionsLoopParams, self.params)
        if not p.writeSessionInfo or self.headers is None or self.headers.uuid is None or self.headers.user is None:
            return

        session.add(
            user_output.sessions(
                uuid=self.headers.uuid,
                user=self.headers.user,
                startTime=datetime.now().strftime("%Y%m%d_%H%M%S"),
                baseYear=p.calculationYear if p.baseYear is None else p.baseYear,
                targetYear=p.targetYear,
                calculationScenario=p.calculationScenario,
                method=p.method,
                electricityType=p.electricityType,
                geomArea=p.mun,
            )
        )
