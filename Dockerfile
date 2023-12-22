FROM python:3
WORKDIR /app
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt install -y wget
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb

# Pip reqs
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt