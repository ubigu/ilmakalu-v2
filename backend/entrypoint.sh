#!/bin/sh
alembic upgrade head
fastapi run src/main.py --port 4000