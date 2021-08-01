# OnceML

Add a short description here!


## Description

A longer description of your project goes here...


<!-- pyscaffold-notes -->

## Note

This project has been set up using PyScaffold 4.0.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.

## docker镜像制作
### pip依赖基础镜像
docker build . -f Dockerfile/require.Dockerfile  --build-arg "HTTPS_PROXY=114.212.84.223:8889" -t liziming/onceml-pip:latest
docker push liziming/onceml-pip
### 测试镜像
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=114.212.84.223:8889" -t liziming/onceml
docker push liziming/onceml
### NFS server
https://hub.docker.com/r/itsthenetwork/nfs-server-alpine