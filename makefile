# Makefile
.PHONY: help build up down logs clean test dev prod

help:
	@echo "ShortSync Pro Docker Commands:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start development environment"
	@echo "  make down      - Stop development environment"
	@echo "  make logs      - View logs"
	@echo "  make clean     - Remove containers and volumes"
	@echo "  make test      - Run tests in Docker"
	@echo "  make dev       - Start development with hot reload"
	@echo "  make prod      - Start production environment"

build:
	docker-compose -f docker-compose.yml build

up:
	docker-compose -f docker-compose.yml up -d

down:
	docker-compose -f docker-compose.yml down

logs:
	docker-compose -f docker-compose.yml logs -f

clean:
	docker-compose -f docker-compose.yml down -v
	docker system prune -f

test:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

dev:
	docker-compose -f docker-compose.dev.yml up --build

prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

restart:
	docker-compose -f docker-compose.yml restart

shell:
	docker-compose -f docker-compose.yml exec shortsync bash

backup:
	docker-compose -f docker-compose.yml exec shortsync python -m bot.utils.backup

deploy:
	@echo "Deploying to production..."
	git pull
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	docker system prune -f
