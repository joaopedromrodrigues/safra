"""DAG do Airflow: mesmo pipeline da CLI, uma task por etapa.

Roda mensal, nao diario: a PAM e anual e o POWER publica serie historica revisada,
entao o custo de rodar toda hora e download sem mudanca. O mes de fevereiro e o que
interessa (fecha a janela critica dez-jan das duas ultimas safras).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

# Em producao o pacote pode nao estar instalado no venv do scheduler; a DAG usa o
# que existe no repo montado.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from safra import pipeline  # noqa: E402

default_args = {
    "owner": "joao.rodrigues",
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(hours=2),
}

with DAG(
    dag_id="safra_soja_clima_pr",
    description="PAM/IBGE + NASA POWER -> rendimento da soja por municipio no PR",
    schedule="0 6 1 2 *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["agro", "ibge", "nasa-power", "duckdb"],
    doc_md=__doc__,
) as dag:
    pam = PythonOperator(task_id="ingerir_pam", python_callable=pipeline.ingerir_pam)
    malhas = PythonOperator(task_id="ingerir_malhas", python_callable=pipeline.ingerir_malhas)
    silver = PythonOperator(task_id="silver_pam_centroides",
                            python_callable=pipeline.montar_silver_parcial)
    clima = PythonOperator(
        task_id="ingerir_clima",
        python_callable=pipeline.ingerir_clima,
        op_kwargs={"cobertura": 0.85},
        execution_timeout=timedelta(hours=2),
    )
    gold = PythonOperator(task_id="gold_warehouse", python_callable=pipeline.montar_warehouse)
    qualidade = PythonOperator(task_id="validar", python_callable=pipeline.validar)
    publicar = PythonOperator(task_id="publicar", python_callable=pipeline.publicar)

    [pam, malhas] >> silver >> clima >> gold >> qualidade >> publicar
