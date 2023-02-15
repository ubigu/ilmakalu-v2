# Background

Generate Azure database resource (flexible server), and
populate contents with compute database dump.

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

```sh
$ sh take_compute_database_dump.sh
```

## Initialize databases

Create extension(s) and load dump:

```sh
$ sh compute_db_init.sh
```

Initialize userdata database

```sh
$ sh user_db_init.sh
```

## Remove user

Remove user(s), if required.

N.b. compute database must be dropped before script is run.

```sh
$ sh compute_db_drop_users.sh
```

# Debugging

Test connection:

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

Initialize variables from provided init file

```sh
$ . ./azure_variables.sh
```

After init, you can utilize variables:

```sh
$ psql $conn_string_ilmakalu
```

See rest of connection strings from variable init file.
