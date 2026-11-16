SAFRA_ANOS  ?= 2016-2024
SAFRA_COB   ?= 0.85

.PHONY: install demo run test lint clean

install:
	uv venv --python 3.12 .venv
	uv pip install -e ".[dev]"

# Baixa o que falta (usa cache local), monta silver/gold, roda os checks e gera dist/.
demo:
	.venv/bin/python -m safra run --anos $(SAFRA_ANOS) --cobertura $(SAFRA_COB)

run:
	.venv/bin/python -m safra run --anos $(SAFRA_ANOS) --municipios all

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check src tests dags

clean:
	rm -rf data dist
