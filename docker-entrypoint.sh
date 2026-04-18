#!/bin/bash
# set -e
# flask db upgrade 

# exec gunicorn --bind 0.0.0.0:80 --workers 4 "main:app"

#!/bin/bash
set -e

echo "PORT value: ${PORT}"
echo "Starting flask db upgrade..."
flask db upgrade

echo "Starting gunicorn on port ${PORT:-10000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 4 --log-level debug "main:app"