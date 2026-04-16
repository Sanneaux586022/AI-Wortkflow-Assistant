#!/bin/bash
set -e
flask db upgrade 

exec gunicorn --bind 0.0.0.0:10000 --workers 4 "main:app"