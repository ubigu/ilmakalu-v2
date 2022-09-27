# intro


## generate dump

See database credentials from a shared secret:

```sh
cd datasets/dump_data
PGPASSWORD="<password>" pg_dump -U <user> -h <host> <database> > emissiontest.sql
```
## strip dump

Strip unnecessary garbage from dump (cloudsql* users). Run if necessary.

```
sh strip_dump.sh
```

## start database service
```
docker-compose up database
```

## users

Create necessary users or roles, giving all users same password.

```
sh create_users_from_dump.sh abcdef | psql -U docker -h localhost -p 5435 postgres
```

## tables

Create all necessary tables from stripped dump.

```
psql -U docker -h localhost -p 5435 ilmakalu -f ../datasets/dump_data/emissiontest_stripped.sql
```

## separate dumps

Verify manually which data has to be imported. It may already be included in the dump.

These are good candidates:

```sh
../testing/Espoo_districtheating.sql
```

## functions

Create functions.

```
sh co2_functions_init.sh | sh
```

# cleanup

In order to clean up, remove database

```sql
DROP DATABASE ilmakalu;
```

Remove external volume, in order to force database init on next service start.
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