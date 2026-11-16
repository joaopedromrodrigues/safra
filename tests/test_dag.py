"""A DAG precisa importar no Airflow.

Na CI o airflow nao esta instalado e o teste e pulado; localmente ele pega erro de
import, mudanca de API de operator e task esquecida. Foi assim que a migracao para
`airflow.providers.standard` apareceu.
"""

from pathlib import Path

import pytest

pytest.importorskip("airflow")

DAGS = Path(__file__).resolve().parents[1] / "dags"
TASKS = {
    "ingerir_pam",
    "ingerir_malhas",
    "silver_pam_centroides",
    "ingerir_clima",
    "gold_warehouse",
    "validar",
    "publicar",
}


def test_dag_importa_e_tem_as_tasks():
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(DAGS), include_examples=False)
    assert bag.import_errors == {}
    dag = bag.dags["safra_soja_clima_pr"]
    assert {t.task_id for t in dag.tasks} == TASKS
    assert dag.max_active_runs == 1
