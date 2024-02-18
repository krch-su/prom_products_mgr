#!/bin/bash

set -o errexit
set -o nounset

celery -A trade_harbor worker -l INFO --