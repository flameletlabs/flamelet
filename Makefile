.ONESHELL:
.PHONY: clean venv tests build

ACTIVATE_DOCS_VENV:=. venv/bin/activate

setup: venv install
    
venv:
	@echo "Creating python virtual environment in 'venv' folder..."
	@python3 -m venv venv

install:
	@echo "Installing python packages..."
	@$(ACTIVATE_DOCS_VENV)
	@pip install -r requirements.txt

clean:
	@echo "Cleaning previous python virtual environment..."
	@rm -rf venv

build:
	@$(ACTIVATE_DOCS_VENV)
	@mkdocs build -f ../mkdocs.yml

serve:
	@$(ACTIVATE_DOCS_VENV)
	@mkdocs serve -f ../mkdocs.yml

deploy:
	@$(ACTIVATE_DOCS_VENV)
	@mkdocs gh-deploy -f ../mkdocs.yml
