FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/requirements.txt /app/requirements/requirements.txt
RUN pip install --no-cache-dir -r requirements/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

CMD ["python", "-m", "homeiot.cli", "web"]
