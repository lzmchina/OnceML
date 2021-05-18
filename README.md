# OnceML

Add a short description here!


## Description

A longer description of your project goes here...


<!-- pyscaffold-notes -->

## Note

This project has been set up using PyScaffold 4.0.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.

## docker镜像制作

### 测试镜像
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=114.212.84.223:8889" -t liziming/onceml:0.0.1
docker push liziming/onceml:0.0.1
