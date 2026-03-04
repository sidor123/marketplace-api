.PHONY: install run migrate docker-up docker-down docker-build docker-logs docker-restart flyway-install generate-schemas

install:
	pip install -r requirements.txt
	@echo "Generating schemas from OpenAPI spec..."
	@./scripts/generate_schemas.sh

generate-schemas:
	@echo "Generating Pydantic schemas from OpenAPI spec..."
	@./scripts/generate_schemas.sh

flyway-install:
	@echo "Installing Flyway"
	@if command -v brew >/dev/null 2>&1; then \
		brew install flyway; \
	else \
		echo "Homebrew not found"; \
	fi

migrate:
	@echo "Running Flyway migrations (local)"
	flyway -configFiles=flyway.conf migrate

migrate-info:
	flyway -configFiles=flyway.conf info

run:
	python3 -m flask --app app.main run --host 0.0.0.0 --port 8000 --reload

docker-build:
	@echo "Building Docker images"
	docker-compose build

docker-up:
	@echo "Starting all services (postgres, flyway, api)"
	docker-compose up -d

docker-down:
	@echo "Stopping all services"
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-logs-api:
	docker-compose logs -f api

docker-logs-postgres:
	docker-compose logs -f postgres

docker-logs-flyway:
	docker-compose logs flyway

docker-restart:
	@echo "Restarting all services"
	docker-compose restart

docker-restart-api:
	@echo "Restarting API service"
	docker-compose restart api

docker-clean:
	@echo "Stopping and removing all containers, networks, and volumes"
	docker-compose down -v

setup: install docker-up
	@echo "Docker setup complete! Services are running:"
	@echo "  - PostgreSQL: localhost:5433"
	@echo "  - API: http://localhost:8000"
	@echo "  - Migrations: completed automatically"
	@echo ""
	@echo "Use 'make docker-logs' to view logs"

setup-local: install docker-up
	@echo "Waiting for database to be ready"
	@sleep 3
	@$(MAKE) migrate
	@echo "Local setup complete, run 'make run' to start application"
