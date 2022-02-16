FROM liziming/onceml-requirements:latest
COPY . /onceml/
WORKDIR /onceml/
# RUN apt install python3
RUN  pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && pip install -e .
EXPOSE 10086