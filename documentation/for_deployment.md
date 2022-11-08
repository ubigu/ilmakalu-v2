# Quickstart

In order to test approach described here, script `prepare_gis_materials.sh` is
current development platform.

Developed script will try to run all documented data preparation steps.

Some error handling is implemented.

## Prerequisites

* install `yq`
* copy (or symlink) files to directory `external` (see script)
* development database is up and running
* it might be a good idea to have database dump already imported to database

# Notes for deployment

# Minimize run time and time used to download materials

After initial set up, try to reduce time spent in manual tasks.

One possible approach would be:
* first phase: document all setup operations meticulously (ongoing)
* second phase: automatize previous step (with script)
* third phase: save results to files from the second phase to be uploaded (and not generated) for the next time.
* fourth phase: automatize third phase (possibly already in docker setup)
* fifth phase: prepare separate material enhancement process and production setup processes

Keep documentation up to date for each step!

## Static external materials

Copy deployment wide materials to separate [directory](https://drive.google.com/drive/folders/1VwqIB9lnApUohYG3UoQ-9oowBiPHnEgz?usp=share_link)

* Municipality division
* YKR related
  * centers and commercial centers (keskustat ja kaupan alueet)
  * YKR urban-rural
  * YKR urban zones

## Self-created static materials

Create and export materials and save to external directory.

* Corine (clc)
* 250m grid
* [list continues]

# Future processing paths

_Here is listed future processing path contents_

## Data processing

Database processing:
* data.clc

File processing:
* grid_250m.shp

## Deployment

Data population during or immediately after deployment.