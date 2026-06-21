import logging

import mlflow

from app.core.config import settings


logger = logging.getLogger(__name__)


def configure_mlflow() -> None:
    if not settings.mlflow_enabled:
        logger.info("MLflow tracing is disabled")
        return

    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        mlflow.langchain.autolog()
        logger.info(
            "MLflow tracing enabled for experiment %s",
            settings.mlflow_experiment_name,
        )
    except Exception:
        logger.exception("MLflow initialization failed; tracing is disabled")
