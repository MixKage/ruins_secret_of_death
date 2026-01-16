FROM ubuntu:20.04 AS build-env

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-distutils \
        python3.11-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m ensurepip --upgrade \
    && python3.11 -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY requirements.txt /app/
RUN python3.11 -m pip install --no-cache-dir --prefix=/usr/local -r requirements.txt

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-env /usr/local /usr/local

WORKDIR /app
COPY . /app/

CMD ["python3.11", "-m", "bot.main"]
