# Tampere specific image preparation

- create stripped dump (see `restore_dump.md`)
- copy stripped dump `../datasets/dump_data/emissiontest_stripped.sql` to `tampere/dump`
- build database
```sh
     docker-compose build --no-cache \
          --build-arg EMISSIONTEST_USER_PW='abc123' \
          --build-arg INTERNAL_USER_PW='cde234' \
          --build-arg SCHEMACREATOR_USER_PW='efg345' \
          --build-arg TABLECREATOR_USER_PW='ghi567' \
          --build-arg CLOUDSQLADMIN_USER_PW='jkl543' \
          --build-arg CLOUDSQLSUPERUSER_USER_PW='lmn098' \
          tampere
```
- start services `docker-compose up tampere_user tampere`

## Clean up

- `docker-compose stop tampere` (Or CTRL-C)
- `docker-compose rm tampere`
- `docker rmi ilmakalu/tampere:latest`

## How to test

See exact details from `.env` -file.

### User database

Database is running on port 45435

User: $ILMAKALU2_USER

### Compute database

Database is running on port 35435

User: $ILMAKALU_USER

### Connection

Start command line session at user database.

Compute service name is: $ILMAKALU_COMPUTE_SERVICE_NAME

```
ilmakalu_user=> select * from dblink('ubicompute', 'select xyind, zone from delineations.grid limit 4;') as grid(xyind varchar(80), zone bigint);
     xyind     | zone 
---------------+------
 3328756928875 |   87
 3331256928625 |   87
 3348756928625 |   87
 3338756928375 |   87
(4 rows)
```