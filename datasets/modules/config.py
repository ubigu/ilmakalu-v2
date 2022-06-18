from pathlib import Path
import yaml

class Config:
    def __init__(self, db_config : str = "local_dev"):
        self.read_config()
        self._db_url = self._db_connection_url(db_config)

    def read_config(self):
        filename = Path(__file__).parent.parent / "config" / 'config.yaml'
        with open(filename) as file:
            configuration = yaml.load(file, Loader=yaml.FullLoader)
        self._cfg = configuration

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

    def db_url(self):
        return self._db_url

    def _db_connection_url(self, db_config) -> str:
        db_details = self._cfg.get("database").get(db_config)
        return "postgresql://{}:{}@{}:{}/{}".format(
            db_details.get("user"),
            db_details.get("pass"),
            db_details.get("host"),
            db_details.get("port"),
            db_details.get("database")
            )