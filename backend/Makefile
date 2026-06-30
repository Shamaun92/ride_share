.PHONY: up down logs migrate revision test fmt

up:            ## Build & start the full stack (api, db, redis, nginx)
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:       ## Apply migrations inside the api container
	docker compose exec api alembic upgrade head

revision:      ## Autogenerate a migration: make revision m="add rides"
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test:          ## Run the test suite locally
	pytest -q
