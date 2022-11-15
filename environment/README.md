# Quickstart

## build

```sh
docker-compose build
```


## run

```sh
docker-compose run --rm devenv
```

## Python development environment

While running just created container, test Python 3.10 `pyjq` installation

```
root@4f5c896f1ec4:/# python3.10 -m venv venv
root@4f5c896f1ec4:/# source venv/bin/activate
(venv) root@4f5c896f1ec4:/# pip install pyjq
```