.PHONY: up down build logs seed clean dbt-test

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

seed:
	docker compose exec batch-ingest python -c "from main import fetch_and_store; fetch_and_store()"

dbt-test:
	docker compose exec batch-ingest dbt test --project-dir /app/dbt --profiles-dir /app/dbt

dbt-build:
	docker compose exec batch-ingest dbt build --project-dir /app/dbt --profiles-dir /app/dbt

clean:
	docker compose down -v
	rm -f data/pipeline.duckdb
