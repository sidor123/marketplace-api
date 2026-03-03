.PHONY: install run migrate docker-up docker-down flyway-install

install:
	pip install -r requirements.txt

flyway-install:
	@echo "Installing Flyway"
	@if command -v brew >/dev/null 2>&1; then \
		brew install flyway; \
	else \
		echo "Homebrew not found"; \
	fi

migrate:
	@echo "Running Flyway migrations"
	flyway -configFiles=flyway.conf migrate

migrate-info:
	flyway -configFiles=flyway.conf info

run:
	python3 -m flask --app app.main run --host 0.0.0.0 --port 8000 --reload

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

setup: install docker-up
	@echo "Waiting for database to be ready"
	@sleep 3
	@$(MAKE) migrate
	@echo "Setup complete, run 'make run' to start application"
