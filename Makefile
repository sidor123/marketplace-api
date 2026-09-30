.PHONY: install generate-schemas run build release start stop logs test archive
PYTHON ?= python3
COMPOSE ?= docker compose
ENV_FILE ?= .env
RELEASE_ID ?= hw1-r1
APP_IMAGE ?= marketplace-api:hw1-r1
RELEASE_ENV = artifacts/releases/$(RELEASE_ID).env

install:
	$(PYTHON) -m pip install -r requirements-build.txt
	sh scripts/generate_schemas.sh

generate-schemas:
	sh scripts/generate_schemas.sh

run:
	gunicorn --config gunicorn.conf.py app.main:app

build:
	$(COMPOSE) --env-file $(ENV_FILE) build api

release:
	$(PYTHON) scripts/release.py $(RELEASE_ID) --env-file $(ENV_FILE) --image $(APP_IMAGE)
	$(COMPOSE) --env-file $(RELEASE_ENV) up -d --wait postgres
	$(COMPOSE) --env-file $(RELEASE_ENV) run --rm migrate

start:
	$(COMPOSE) --env-file $(RELEASE_ENV) up -d --no-build --wait api

stop:
	$(COMPOSE) --env-file $(RELEASE_ENV) down

logs:
	$(COMPOSE) --env-file $(RELEASE_ENV) logs -f api

test:
	$(PYTHON) -m unittest discover -s tests -v

archive:
	$(PYTHON) scripts/package.py
