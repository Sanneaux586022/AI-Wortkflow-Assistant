#!/bin/bash
# set -e
# flask db upgrade 

# exec gunicorn --bind 0.0.0.0:80 --workers 4 "main:app"

#!/bin/bash
set -e

echo "PORT value: ${PORT}"
echo "Starting flask db upgrade..."
# export FLASK_APP=main.py
flask db upgrade

echo "Starting gunicorn on port ${PORT:-5000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --log-level debug "main:app"