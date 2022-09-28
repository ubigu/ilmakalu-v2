# intro

## generate dump

See database credentials from a shared 1Password secret.
Create directory if it does not exist.

```sh
cd datasets/dump_data
PGPASSWORD="<password>" pg_dump -U <user> -h <host> <database> > emissiontest.sql
```
## strip dump

Strip unnecessary garbage from dump (cloudsql* users). These are
present in the dump due to cloud hosting and are unnecessary for
local deployment. Run strip each time when new dump is taken.

```sh
# Following commands are relative to 'services' -directory
sh strip_dump.sh
```

## start database service
```
docker-compose up database
```

## users

Create necessary users or roles, giving all users the same password.
Currently we create all users that are present (and not stripped) in the dump.
We do not care how many, and what particular users there are.

For deployment in actual target environment, user initialization has to
be handled differently. Docker database init functionality is a good alternative.

```sh
sh create_users_from_dump.sh <password> | psql -U <superuser> -h localhost -p <port> postgres
```

## tables

Create all necessary tables from stripped dump.

```sh
psql -U <superuser> -h localhost -p <port> <ilmakalu_db> -f ../datasets/dump_data/emissiontest_stripped.sql
```

## separate dumps

Verify manually from database which data has to be imported.
Data may already be included in the dump.

These are good candidates:

```sh
../testing/Espoo_districtheating.sql
```

## functions

Create functions.

```sh
sh co2_functions_init.sh | sh
```

# cleanup

In order to clean up, remove external volume, in order to force database init on next service start.
Volume removal will not succeed on the first try, but it will point to
container, which has to be removed first.

```
docker volume rm ilmakalu_ilmakalu-data
```

Dependent container is mentioned. Remove container

```
docker rm <container id>
```

After succesful container removal, volume can be removed.

It is also possible to remove database only, but this is not encouraged, since
docker-compose will not automatically create database again with correct setup.

```sql
DROP DATABASE ilmakalu;
```