# Default target
.DEFAULT_GOAL := build

# Clean stage: Removes the 'common' directory or symlink and the virtual environment
clean:
	bash -c -e '\
	rm -rf common/__pycache__ && \
	rm -rf __pycache__ && \
	deactivate 2>/dev/null || true && \
	rm -rf common venv .venv \
	rm -rf build_output.log \
	'

# Copy stage: Copies the 'common' directory from the parent directory
copy: clean
	cp -r ../../common .

# Build stage: Cleans and creates a symbolic link to the 'common' directory
build:
	@bash -ce "\
	ln -s ../../common common && \
	python -m venv .venv && \
	source ./.venv/bin/activate && \
	echo -e \"\\033[1;32mActivating virtual environment...\\033[0m\" && \
	pip install --index-url https://pypi.org/simple google-cloud-artifact-registry keyring keyrings.google-artifactregistry-auth  >> build_output.log 2>&1 && \
	pip install -r requirements.txt  >> build_output.log \
	"

debug:
	@bash -ce "\
	if [ ! -d \".venv\" ]; then \
	echo -e \"\\033[1;33mVirtual environment '.venv' not found. Running make build...\\033[0m\"; \
	make build; \
	fi && \
	source .venv/bin/activate && \
	PYTHONUNBUFFERED=1 FORCE_COLOR=1 python main.py --debug \
	"

run:	
	@bash -ce "\
	if [ ! -d \".venv\" ]; then \
	echo -e \"\\033[1;33mVirtual environment '.venv' not found. Running make build...\\033[0m\"; \
	make build; \
	fi && \
	source .venv/bin/activate && \
	PYTHONUNBUFFERED=1 FORCE_COLOR=1 python main.py \
	"

# Deploy stage: Cleans, copies, echoes a message, and builds
deploy: clean copy
deploy: clean copy
	echo -e "\033[1;34mPreparing deployment...\033[0m" && \
	{ \
		bash -c -e '\
			gcloud functions deploy post_prices \
				--gen2 \
				--runtime python312 \
				--source . \
				--region us-central1 \
				--trigger-http \
				--memory 512M \
				--set-env-vars DEPLOYED_VERSION_NAME=1.0.GIT_SHA,FUNCTION_NAME=post_prices,LOG_FILE_NAME="pricing-service",LOG_SERVICE_NAME=pricing-service,LOG_FUNCTION_NAME=post_prices,ENVIRONMENT=dev-test-staging \
				--entry-point handler \
				--allow-unauthenticated \
		' || true; \
	} && \
	make build

# Phony targets to ensure proper behavior
.PHONY: clean copy build run debug deploy