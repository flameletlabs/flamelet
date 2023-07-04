.ONESHELL:
.PHONY: clean venv tests build

ACTIVATE_VENV:=. venv/bin/activate

setup: venv install
    
venv:
	@echo "Creating python virtual environment in 'venv' folder..."
	@python3 -m venv venv

install:
	@echo "Installing python packages..."
	@$(ACTIVATE_VENV)
	@pip install -r requirements.txt

clean:
	@echo "Cleaning previous python virtual environment..."
	@rm -rf venv

build:
	@$(ACTIVATE_VENV)
	@mkdocs build -f flamelet/mkdocs.yml

serve:
	@$(ACTIVATE_VENV)
	@mkdocs serve -f flamelet/mkdocs.yml
