# intro

## steps (when data is in other than SQL)

* for kartoza/postgis:13.0
* (debian bullseye)
* use multi stage build
* first stage:
  * install gdal-bin
  * as described: https://cadu.dev/creating-a-docker-image-with-database-preloaded/
* second stage: same kartoza image as first stage

Prerequisites:
* all required source files are in subdirectories of build directory

# idea

## db 1

work db to develop all data (current data schema)
* take dumps from critical tables
  * clc
  * grid
* convert schemas in dumps

## db 2

* build stage 1 database. Import whole tables from db 1
  * ubihub dump
  * clc
  * grid
* during build remove extra data (DELETE FROM IF NOT kunta IN(1,2,3))

## db 3

* copy data directory from db 2
