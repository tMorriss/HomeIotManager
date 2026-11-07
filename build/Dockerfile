FROM python:3.12-slim

ENV TZ=Asia/Tokyo

WORKDIR /app

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        iputils-ping \
        curl \
        tzdata && \
    ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo 'Asia/Tokyo' > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/requirements.txt /app/requirements/requirements.txt
RUN pip install --no-cache-dir -r requirements/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

CMD ["python", "-m", "homeiot.cli", "web"]
