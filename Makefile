SAFRA_ANOS ?= 2016-2024
SAFRA_COB  ?= 0.85

.PHONY: install demo run test lint dag-test clean

install:
	uv venv --python 3.12 .venv
	uv pip install -e ".[dev]"

# Baixa o que falta (usa cache local), monta silver/gold, roda os checks e gera dist/.
demo:
	.venv/bin/python -m safra --anos $(SAFRA_ANOS) --cobertura $(SAFRA_COB) run

run:
	.venv/bin/python -m safra --municipios all run

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/python -m ruff check src tests dags

# A DAG so importa onde o airflow existe; na CI o teste e pulado.
dag-test:
	.venv-airflow/bin/python -m pytest tests/test_dag.py -q

clean:
	rm -rf data dist
