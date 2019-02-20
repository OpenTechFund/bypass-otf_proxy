Python App to set up and maintain mirrors.

# Setup 

export PIPENV_VENV_IN_PROJECT=1
pipenv install
pipenv shell

# Usage

## Initial mirror setup
python mirror.py --config=<name of config file>

## Cron setup

use crontab file either globally or with single user

# Serving Mirror

## Docker

mkdir -r <path-to-docker-project>/production
cp ./docker-compose.yml <path-to-docker-project>/production
cp ./production.conf <path-to-docker-project>/production

cd <path-to-docker-project>/production
docker-compose up -d

Check server URL for mirror