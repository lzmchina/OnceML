FROM python:3.8.12
COPY singleNode.py requirements.txt /codes/
WORKDIR /codes
RUN export http_proxy=http://114.212.80.19:21087 && apt-get update && apt-get install ffmpeg libsm6 libxext6  -y && pip install -r requirements.txt