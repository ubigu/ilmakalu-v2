# Background

Generate Azure database resource (flexible server), and
populate contents with compute database and user database dumps.

# Quickstart

Instructions to init database either locally or to Azure.

## Edit configuration

Add configuration `ilmakalu_azure.yaml`. See supported fields from `ilmakalu_azure_template.yaml`.

Local configuration is written to: `ilmakalu_local.yaml`. Currently all data is parsed,
but only some really used. 

See also `dev-services` (especially admin credentials should be aligned)

## Local dev

### Start service in dev-services

```sh
# in dev-services -directory
$ docker-compose up
```

### Run init scripts
```sh
$ sh user_db_create_users.sh local # not needed after first run
$ sh user_db_init.sh local
$ sh compute_db_init.sh local
$ sh create_user_group_and_event_trigger local
$ sh create_end_users.sh local # List wanted end users to yaml. Copy user passwords from console output. Set search path for each user. 
```

Test connection and that everything is in place.
```sh
$ . azure_variables.sh local # init variables to current shell
$ psql "$conn_string_ilmakalu_data" # test connection
```

### clean up end users and their management
In order to quickly clean up end users. Note that this will leave user group role and event trigger in place. 
```sh
$ sh clean_up_end_users.sh local
```

## Azure login

Scripts will try to utilize latest Azure login.

If unsure, login manually before running scripts.

```sh
$ az login
```

## Installs

Install `az` extension *`rdbms-connect` if not yet installed.

See install status with e.g.

```sh
$ az extension list-available --output table
```

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

(Re)-initialize userdata database. This needs to be run before `compute_db_init.sh` since it creates the database.

BEWARE: existing database is dropped!

```sh
# BEWARE: USER data is dropped!
$ sh user_db_init.sh
# BEWARE: USER data is dropped!
```

Create extension(s) and (re)-initialize database:

```sh
$ sh compute_db_init.sh
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

ilmakalu_data=> SELECT xyind, zone FROM delineations.grid LIMIT 4;
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
SELECT * FROM CO2_CalculateEmissions(
    array[837],
    NULL::regclass);
```

# Possible pitfalls

## Connection strings

Regarding generating connection strings in `azure_variables.sh`:

String replace with `sed` can fail, if passwords contain characters that confuse `sed`.

It is then safe to either make script more robust (possibly start using
use URL encoding for passwords), or avoid problematic characters.
