PYTHON = python

all:
	$(PYTHON) pac-man.py config.json

lint:
	flake8 src

mypy:
	mypy src

check: lint mypy
