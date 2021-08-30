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
docker build . -f Dockerfile/require.Dockerfile  --build-arg "HTTPS_PROXY=114.212.80.19:21087" -t liziming/onceml-requirements:latest

docker build . -f Dockerfile/require.Dockerfile   -t liziming/onceml-requirements:latest
docker push liziming/onceml-requirements
### 测试镜像
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=114.212.80.19:21087" -t liziming/onceml:0.0.1
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=172.27.135.233:7890" -t liziming/onceml:0.0.1
### NFS server
https://hub.docker.com/r/itsthenetwork/nfs-server-alpine