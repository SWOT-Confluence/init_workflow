# Stage 0 - Create from Python3.12 image
FROM python:3.12-slim-bookworm as stage0
# FROM python:3.12-slim-bookworm

# Stage 1 - Copy and execute module
FROM stage0 as stage1
COPY requirements.txt /app/requirements.txt
RUN /usr/local/bin/python -m venv /app/env \
        && /app/env/bin/pip install -r /app/requirements.txt
COPY ./init_workflow.py /app/init_workflow.py

LABEL version="1.0" \
        description="Containerized init_workflow module."
ENTRYPOINT ["/app/env/bin/python3", "/app/init_workflow.py"]