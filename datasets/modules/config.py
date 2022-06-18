from pathlib import Path
import yaml

class Config:
    def __init__(self):
        self.read_config()

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
