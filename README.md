# OnceML

Add a short description here!


## Description

A longer description of your project goes here...


<!-- pyscaffold-notes -->

## Note

This project has been set up using PyScaffold 4.0.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
## 测试安装
pip install -e .
## docker镜像制作
### pip依赖基础镜像
docker build . -f Dockerfile/require.Dockerfile  --build-arg "HTTPS_PROXY=114.212.80.19:21087" -t liziming/onceml-requirements:latest
docker build . -f Dockerfile/require.Dockerfile  --build-arg "HTTPS_PROXY=172.27.128.186:7890" -t liziming/onceml-requirements:latest
docker build . -f Dockerfile/require.Dockerfile   -t liziming/onceml-requirements:latest
docker push liziming/onceml-requirements
### 测试镜像
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=114.212.80.19:21087" -t liziming/onceml:0.0.1

docker build . -f Dockerfile/test.Dockerfile   -t liziming/onceml:0.0.1

sudo docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=172.27.156.240:7890" -t liziming/onceml
docker build . -f Dockerfile/test.Dockerfile  --build-arg "HTTPS_PROXY=114.212.80.19:21087" -t liziming/onceml
docker push  liziming/onceml:latest
### NFS server
https://hub.docker.com/r/itsthenetwork/nfs-server-alpine

### 数据文件读写镜像
docker build ./benchmarks/IO/NFS/ -f Dockerfile/benchmark.Dockerfile  -t registry.cn-hangzhou.aliyuncs.com/liziming/oncemlio --build-arg HTTPS_PROXY=http://114.212.80.19:21087 
docker build ./benchmarks/IO/NFS/ -f Dockerfile/benchmark_test.Dockerfile  --build-arg http_proxy=http://114.212.80.19:21087 --build-arg https_proxy=http://114.212.80.19:21087