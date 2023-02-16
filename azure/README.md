# Background

Generate Azure database resource (flexible server), and
populate contents with compute database and user database dumps.

# Quickstart

## Azure login

Scripts will try to utilize latest Azure login.

If unsure, login manually before running scripts.

```sh
$ az login
```

## Edit configuration

Add configuration `ilmakalu_azure.yaml`. See supported fields from `ilmakalu_azure_template.yaml`.

## Initialize resources

Run provided shell script:

```sh
$ sh create_flexible_server_from_scratch.sh
```

## Initialize users

Initialize compute database user, if required.

```sh
$ sh compute_db_create_users.sh
```

Initialize user database user, if required.

```sh
$ sh user_db_create_users.sh
```

## Fetch dump

From copute database:

```sh
$ sh take_compute_database_dump.sh
```

From user database:

```sh
$ sh take_user_database_dump.sh
```

## Initialize databases

Create extension(s) and (re)-initialize database:

```sh
$ sh compute_db_init.sh
```

(Re)-initialize userdata database

BEWARE: existing database is dropped!

```sh
# BEWARE: USER data is dropped!
$ sh user_db_init.sh
# BEWARE: USER data is dropped!
```

## Remove users from compute database

Remove user(s), if required.

N.b. compute database must be dropped before script is run.

```sh
$ sh compute_db_drop_users.sh
```

# Debugging

Initialize variables from provided init file

```sh
$ . ./azure_variables.sh
```

After init, you can utilize variables:

```sh
$ psql $conn_string_ilmakalu
```

See rest of connection string variable names from variable init file (`azure_variables.sh`).

## Test dblink-connection:

```sh
$ . ./azure_variables.sh
$ psql $conn_string_ilmakalu_data
psql (14.3, server 13.9)
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

ilmakalu_data=> select * from dblink('ubicompute', 'select xyind, zone from delineations.grid limit 4;') as grid(xyind varchar(80), zone bigint);
     xyind     | zone 
---------------+------
 3328756928875 |   87
 3331256928625 |   87
 3348756928625 |   87
 3338756928375 |   87
(4 rows)
```

## Verify function run

Following call from user database should process some time (minute or two), and produce sensible result:

```sql
SELECT * FROM dblink('ubicompute', 'SELECT * FROM CO2_CalculateEmissions(
    array[837],
    NULL::regclass);') AS TULOS(
    geom geometry(MultiPolygon, 3067),
    xyind varchar(13),
    mun int,
    zone bigint,
    year date,
    floorspace int,
    pop smallint,
    employ smallint,
    tilat_vesi_tco2 real,
    tilat_lammitys_tco2 real,
    tilat_jaahdytys_tco2 real,
    sahko_kiinteistot_tco2 real,
    sahko_kotitaloudet_tco2 real,
    sahko_palv_tco2 real,
    sahko_tv_tco2 real,
    liikenne_as_tco2 real,
    liikenne_tp_tco2 real,
    liikenne_tv_tco2 real,
    liikenne_palv_tco2 real,
    rak_korjaussaneeraus_tco2 real,
    rak_purku_tco2 real,
    rak_uudis_tco2 real,
    sum_yhteensa_tco2 real,
    sum_lammonsaato_tco2 real,
    sum_liikenne_tco2 real,
    sum_sahko_tco2 real,
    sum_rakentaminen_tco2 real
);
```

# Possible pitfalls

## Connection strings

Regarding generating connection strings in `azure_variables.sh`:

String replace with `sed` can fail, if passwords contain characters that confuse `sed`.

It is then safe to either make script more robust (possibly start using
use URL encoding for passwords), or avoid problematic characters.
