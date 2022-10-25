from pathlib import Path
import yaml

class Config:
    def __init__(self, db_config: str = None):
        self.read_config()
        self._db_url = self._db_connection_url(db_config)
        self._db_connstring = self._db_connection_string(db_config)

    def read_config(self):
        filename = Path(__file__).parent.parent / "config" / 'config.yaml'
        with open(filename) as file:
            configuration = yaml.load(file, Loader=yaml.FullLoader)
        self._cfg = configuration


    # Graphopper methods
    def graphhopper_isochrone_url(self):
        gh = self._cfg.get("isochrones").get("graphhopper")
        port = gh.get("port")
        # unfortunate hack to preserve placeholders for later "format"
        return gh.get("base_url").format(port, "{}", "{}", "{}")

    def graphhopper_router_url(self):
        gh = self._cfg.get("routing").get("graphhopper")
        port = gh.get("port")
        # unfortunate hack to preserve placeholders for later "format"
        return gh.get("base_url").format(port, "{}", "{}", "{}", "{}")


    # Postgres methods
    def chosen_database(self):
        return self._cfg.get("chosen_database")

    def db_url(self):
        return self._db_url

    def db_conn_string(self):
        return self._db_connstring

    def _db_connection_url(self, db_config: str = None) -> str:
        if db_config is None:
            db_config = self.chosen_database()

        db_details = self._cfg.get("database").get(db_config)
        return "postgresql://{}:{}@{}:{}/{}".format(
            db_details.get("user"),
            db_details.get("pass"),
            db_details.get("host"),
            db_details.get("port"),
            db_details.get("database")
            )

    def _db_connection_string(self, db_config: str = None) -> str:
        if db_config is None:
            db_config = self.chosen_database()

        db_details = self._cfg.get("database").get(db_config)
        return "host='{host}' port='{port}' dbname='{dbname}' user='{user}' password='{password}'".format(
            host=db_details.get("host"),
            port=db_details.get("port"),
            dbname=db_details.get("database"),
            user=db_details.get("user"),
            password=db_details.get("password")
            )


    # WFS methods
    def wfs_url(self):
        return self._cfg.get("wfs").get("url")

    def wfs_version(self):
        return self._cfg.get("wfs").get("version")

    def wfs_layer(self):
        return self._cfg.get("wfs").get("layer")

    def floor_area_attribute(self):
        return self._cfg.get("wfs").get("floor_area_attribute")

    def fuel_attribute(self):
        return self._cfg.get("wfs").get("fuel_attribute")

    def building_code_attribute(self):
        return self._cfg.get("wfs").get("building_code_attribute")

    def year_attribute(self):
        return self._cfg.get("wfs").get("year_attribute")

    def wfs_properties(self):
        return f"{self._cfg.get('wfs').get('floor_area_attribute')}, {self._cfg.get('wfs').get('fuel_attribute')}, {self._cfg.get('wfs').get('building_code_attribute')}, {self._cfg.get('wfs').get('year_attribute')}"

    def wfs_params(self):
        return dict(service='WFS', version=self.wfs_version(), 
            request='GetFeature', typeName=self.wfs_layer(),
            propertyName=self.wfs_properties(),
            srsName=3067)


    # co2data.fi methods
    def co2dataurl(self):
        return self._cfg.get('co2data.fi').get('url')


    # Methods specifying dataset targets
    def target_municipality(self) -> str:
        return self._cfg.get("target").get("municipality")

    def num_nearest_centers(self) -> int:
        return self._cfg.get("target").get("num_nearst_centers")

if __name__ == "__main__":
    cfg = Config()
    print(cfg.chosen_database())