# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS wheel-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt requirements-torch.txt ./

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel \
        --wheel-dir=/wheelhouse \
        --index-url=https://download.pytorch.org/whl/cpu \
        --requirement requirements-torch.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel \
        --wheel-dir=/wheelhouse \
        --requirement requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/app/.cache/huggingface

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

WORKDIR /app

COPY --from=wheel-builder /wheelhouse /wheelhouse
COPY requirements.txt requirements-torch.txt ./

RUN pip install \
        --no-cache-dir \
        --no-index \
        --find-links=/wheelhouse \
        --requirement requirements-torch.txt \
        --requirement requirements.txt \
    && rm -rf /wheelhouse

COPY --chown=app:app app ./app

RUN mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
