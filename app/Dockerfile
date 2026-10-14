# python:3.13-slim, pinned by digest so a rebuild gets the exact same base.
ARG BASE=python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

FROM ${BASE} AS build
RUN python -m venv /venv
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt \
 && /venv/bin/pip uninstall -y pip

FROM ${BASE}
ARG APP_VERSION=1.3
ENV APP_VERSION=${APP_VERSION} \
    DATA_DIR=/data \
    PATH=/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# pip is only needed at build time; its vendored libraries are the image's
# only known CVEs.
RUN python -m pip uninstall -y pip \
 && useradd --system --uid 10001 --user-group --no-create-home appuser \
 && mkdir -p /data \
 && chown appuser:appuser /data

COPY --from=build /venv /venv
WORKDIR /app
COPY app.py store.py ./
COPY templates templates
COPY static static

USER 10001
EXPOSE 8080
VOLUME /data

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", \
     "--access-logfile", "-", "--no-control-socket", "app:create_app()"]
