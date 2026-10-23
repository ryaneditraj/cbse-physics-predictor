.PHONY: install test demo

install:
	python -m pip install -e ".[dev]"

test:
	pytest

demo:
	cbse-physics demo --out out/report.html --svg out/demo.svg
