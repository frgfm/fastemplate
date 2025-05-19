BACKEND_DIR = ./backend
DOCKERFILE_PATH = ${BACKEND_DIR}/Dockerfile
BACKEND_CONFIG_FILE = ${BACKEND_DIR}/pyproject.toml
PYTHON_REQ_FILE = /tmp/requirements.txt
BACKEND_TEST_DIR = ${BACKEND_DIR}/tests
COMPOSE_FILE = ./docker-compose.yml
COMPOSE_FILE_TEST = ./docker-compose.test.yml
DOCKER_NAMESPACE ?= ghcr.io/frgfm
DOCKER_REPO ?= fastemplate
DOCKER_TAG ?= latest

########################################################
# Code checks
########################################################


install-quality: ${PYTHON_CONFIG_FILE}
	uv export --no-hashes --locked --only-dev -o ${PYTHON_REQ_FILE} --project ${BACKEND_DIR}
	uv pip install --system -r ${PYTHON_REQ_FILE}

lint-check: ${BACKEND_CONFIG_FILE}
	ruff format --check . --config ${BACKEND_CONFIG_FILE}
	ruff check . --config ${BACKEND_CONFIG_FILE}

lint-format: ${BACKEND_CONFIG_FILE}
	ruff format . --config ${BACKEND_CONFIG_FILE}
	ruff check --fix . --config ${BACKEND_CONFIG_FILE}

precommit: ${PYTHON_CONFIG_FILE} .pre-commit-config.yaml
	pre-commit run --all-files

typing-check: ${BACKEND_CONFIG_FILE}
	mypy --config-file ${BACKEND_CONFIG_FILE}

deps-check: .github/verify_deps_sync.py
	uv run .github/verify_deps_sync.py

# this target runs checks on all files
quality: lint-check typing-check deps-check

style: lint-format precommit

########################################################
# Build
########################################################

lock-backend: ${PYTHON_CONFIG_FILE}
	uv lock --project ${BACKEND_DIR}

# Build the docker
build-backend: ${DOCKERFILE_PATH}
	docker build -f ${DOCKERFILE_PATH} -t ${DOCKER_NAMESPACE}/${DOCKER_REPO}:${DOCKER_TAG} ${BACKEND_DIR}

push-backend: build-backend
	docker push ${DOCKER_NAMESPACE}/${DOCKER_REPO}:${DOCKER_TAG}

########################################################
# Run
########################################################

# Run the docker
start-backend: ${COMPOSE_FILE}
	docker compose -f ${COMPOSE_FILE} up -d --wait

# Run the docker
stop-backend: ${COMPOSE_FILE}
	docker compose -f ${COMPOSE_FILE} down


########################################################
# Tests
########################################################

start-test: ${COMPOSE_FILE_TEST}
	docker compose -f ${COMPOSE_FILE_TEST} up -d --build --wait backend_test

start-dev: ${COMPOSE_FILE_TEST}
	docker compose -f ${COMPOSE_FILE_TEST} up -d --wait backend

stop-test: ${COMPOSE_FILE_TEST}
	docker compose -f ${COMPOSE_FILE_TEST} down

# Run tests for the library
test-backend: start-test ${COMPOSE_FILE_TEST} ${BACKEND_TEST_DIR}
	- docker compose -f ${COMPOSE_FILE_TEST} exec -T backend_test pytest --cov=app
	make stop-test

load-test: ${COMPOSE_FILE_TEST}
	docker compose -f ${COMPOSE_FILE_TEST} up -d --wait locust
	docker compose -f ${COMPOSE_FILE_TEST} exec -T locust locust --headless --users 200 --spawn-rate 10  -t 60 -H http://backend:5050 -f /mnt/locust/locustfile.py --only-summary
	make stop-test

########################################################
# Migrations
########################################################

revision:
	docker compose -f ${COMPOSE_FILE_TEST} up -d --wait db
	- docker compose -f ${COMPOSE_FILE_TEST} run --rm migrate sh -c "alembic revision --autogenerate -m '$(MESSAGE)'"
	make stop-test
