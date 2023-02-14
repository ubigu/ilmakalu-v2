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

## Initialize user

Initialize compute database user, if required.

```sh
$ sh compute_db_create_users.sh
```

## Initialize compute database

Create extension(s) and load dump:

```sh
$ sh compute_db_init.sh
```

## Remove user

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

See rest of connection strings from variable init file.
