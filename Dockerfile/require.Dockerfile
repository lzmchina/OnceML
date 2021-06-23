FROM python:3.8
COPY . /onceml/
WORKDIR /onceml/
# RUN apt install python3
RUN  pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple & pip install -r requirements.txt
EXPOSE 8080