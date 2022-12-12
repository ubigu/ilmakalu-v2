FROM kartoza/postgis:13.0

COPY ./dump/emissiontest_stripped.sql /dump/emissiontest_stripped.sql
COPY ./dump/alter-schema-rights.sql /dump/

COPY init/00-init-user-db.sh /docker-entrypoint-initdb.d/
COPY init/01-init.sh /docker-entrypoint-initdb.d/
COPY init/02-init-users.sql /docker-entrypoint-initdb.d/
COPY init/10-restore-database.sh /docker-entrypoint-initdb.d/
