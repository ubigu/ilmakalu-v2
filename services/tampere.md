# Tampere specific image preparation

- create stripped dump (see `restore_dump.md`)
- copy stripped dump `../datasets/dump_data/emissiontest_stripped.sql` to `tampere/dump`
- build database `docker-compose build tampere`
- start services `docker-compose up tampere_user tampere`

## How to verify data and computation

See variable details from `.env` -file and `docker-compose.yml`.

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