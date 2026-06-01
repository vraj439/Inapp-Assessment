.PHONY: up down logs build health

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api-gateway

build:
	docker compose build

health:
	curl -s http://localhost:8080/health | python3 -m json.tool
