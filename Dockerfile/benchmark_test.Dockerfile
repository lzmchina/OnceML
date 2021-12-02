FROM python:3.8.12
COPY singleNode.py requirements.txt /codes/
WORKDIR /codes
RUN env && apt update