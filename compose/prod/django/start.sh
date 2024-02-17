#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python manage.py migrate
python manage.py collectstatic --no-input
gunicorn trade_harbor.wsgi:application --bind 0.0.0.0:8000
