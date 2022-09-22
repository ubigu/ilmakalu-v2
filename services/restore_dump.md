# intro

## strip dump
```
sh strip_dump.sh
```

## users
```
sh create_users_from_dump.sh abcdef | psql -U docker -h localhost -p 5435 ilmakalu
```

## tables
```
psql -U docker -h localhost -p 5435 ilmakalu -f ../datasets/dump_data/emissiontest_stripped.sql
```

## functions
```
sh co2_functions_init.sh | sh
```

# cleanup

In order to clean up, remove database
```sql
DROP DATABASE ilmakalu;
```
