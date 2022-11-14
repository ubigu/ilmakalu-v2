# main database

...

# secondary database

...

# Development cycle (case: user_database)

If there is a need to completely drop database and re-initialize it, do the following

```sh
$ docker-compose stop user_database
# remove container
$ docker-compose rm user_database
# remove volume
$ docker volume rm ilmakalu_ilmakalu-user-data
# re-initialize user database
$ docker-compose up -d user_database
```


