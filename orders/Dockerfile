# FROM python:3.10

# WORKDIR /usr/src/app

# COPY requirements.txt ./

# RUN pip install -r requirements.txt


FROM python:3.10
WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
    PYTHONUNBUFFERED=1
COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

