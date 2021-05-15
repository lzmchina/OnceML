FROM demisto/sklearn:1.0.0.19770
COPY src/onceml /onceml
RUN pip install -e /onceml
WORKDIR /project