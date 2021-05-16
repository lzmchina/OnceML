FROM demisto/sklearn:1.0.0.19770
COPY . /onceml/
WORKDIR /onceml/
RUN  pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple & pip install -e .
EXPOSE 8080