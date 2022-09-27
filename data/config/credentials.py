"""Configuration module for handling database credentials.
"""
import yaml
from pathlib import Path
from urllib.parse import quote_plus

class Config:
    def __init__(self):
        self._read_config()
        self._curr_creds = None

    def _read_config(self):
        filename = Path(__file__).parent / 'config.yaml'
        with open(filename) as file:
            db_credentials = yaml.load(file, Loader=yaml.FullLoader)
        self._db_creds = db_credentials

    def _db_credentials(self):
        return self._db_creds

    def _credentials(self, environ):
        return self._db_credentials().get(environ, None)

    def _host(self):
        return self._curr_creds.get('host')

    def _port(self):
        return self._curr_creds.get('port')

    def _database(self):
        return self._curr_creds.get('database')

    def _user(self):
        return self._curr_creds.get('user')

    def _password(self):
        return self._curr_creds.get('pass')

    def _encoded_password(self):
        """Encode password to be used in PostgreSQL URI"""
        return quote_plus(self.password())

    def list_credentials(self):
        """List keys of configured credentials"""
        return list(self.db_credentials().keys())

    def user_credentials(self, cred_key):
        self._curr_creds = self._credentials(cred_key)

    def postgresql_string(self):
        """Return PostgreSQL connect string."""
        return "host='{host}' port='{port}' dbname='{dbname}' user='{user}' password='{password}'".format(
            host=self._host(),
            port=self._port(),
            dbname=self._database(),
            user=self._user(),
# TODO: Password encoding? In case of conflicting characters in password.
            password=self._password()
            )

    def postgresql_uri(self):
        """Return PostgreSQL connect URI"""
        return "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
            host=self._host(),
            port=self._port(),
            dbname=self._database(),
            user=self._user(),
            password=self._encoded_password()
            )

    def get(self, key):
        return self._curr_creds.get(key, None)
if __name__ == "__main__":

    c = Config()

    print("Available credentials:")
    for cr in c.list_credentials():
        print(cr)

