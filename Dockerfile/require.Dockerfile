FROM python:3.8
COPY requirements.txt /requirements.txt
WORKDIR /
RUN  apt update && apt-cache search openjdk && apt install -y openjdk-11-jre-headless
RUN   pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple &&  pip install -r requirements.txt
EXPOSE 8080