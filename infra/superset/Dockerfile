FROM docker.io/apache/superset:6.0.0

USER root

ENV PIP_DEFAULT_TIMEOUT=300

COPY infra/superset/requirements.txt /tmp/superset-requirements.txt

RUN . /app/.venv/bin/activate && \
    uv pip install -r /tmp/superset-requirements.txt

COPY infra/superset/assets/ /app/superset/static/assets/images/analytics-copilot/
COPY infra/superset/theme.css /app/superset/static/assets/stylesheets/analytics-copilot-theme.css

COPY infra/superset/superset_config.py /app/superset_config.py
ENV SUPERSET_CONFIG_PATH=/app/superset_config.py

USER superset
