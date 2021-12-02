查看教程：https://jimmysong.io/kubernetes-handbook/practice/using-glusterfs-for-persistent-storage.html
https://developer.aliyun.com/article/618056

https://www.cnblogs.com/ssgeek/p/11725648.html#311%E3%80%81%E6%89%80%E6%9C%89%E8%8A%82%E7%82%B9%E5%AE%89%E8%A3%85glusterfs%E5%AE%A2%E6%88%B7%E7%AB%AF

有个包需要手动下载：https://packages.efficios.com/rhel/7/x86_64/old/userspace-rcu/0.10/
https://packages.efficios.com/rhel/7/x86_64/old/userspace-rcu/0.10/userspace-rcu-0.10.0-1.el7.x86_64.rpm
1. sudo yum update
2. sudo yum install centos-release-gluster9
3. sudo yum install -y glusterfs glusterfs-server 
4. sudo yum install -y glusterfs-fuse glusterfs-rdma
5. sudo systemctl start glusterd.service && systemctl enable glusterd.service

主节点上（n167）：
1. sudo gluster peer probe n170
2. sudo gluster volume create k8s-volume  n167:/data/glusterfs-storage n168:/data/glusterfs-storage n169:/data/glusterfs-storage n170:/data/glusterfs-storage force
3. sudo gluster volume start k8s-volume      sudo gluster volume stop k8s-volume sudo gluster volume delete k8s-volume 
4. sudo gluster volume info

现在gluster集群配置好了

下一步安装heketi

参考链接：https://computingforgeeks.com/configure-kubernetes-dynamic-volume-provisioning-with-heketi-glusterfs/
1. 下载heketi-v10.4.0-release-10.linux.amd64.tar.gz
2. 将解压出来的heketi、heketi-cli放在可执行目录里sudo cp heketi/{heketi,heketi-cli} /usr/local/bin
3. sudo groupadd --system heketi
4. sudo useradd -s /sbin/nologin --system -g heketi heketi
5. sudo mkdir -p /var/lib/heketi /etc/heketi /var/log/heketi
6. sudo cp heketi/heketi.json /etc/heketi
7. 再编辑/etc/heketi/heketi.json文件
8.  sudo ssh-keygen -f /etc/heketi/heketi_key -t rsa -N ''
9.  sudo chown heketi:heketi /etc/heketi/heketi_key*
8. sudo vim /etc/systemd/system/heketi.service

9. sudo cp heketi.env /etc/heketi/heketi.env

10. sudo chown -R heketi:heketi /var/lib/heketi /var/log/heketi /etc/heketi
11. sudo systemctl daemon-reload
12.  sudo systemctl start heketi
13.  sudo systemctl status heketi
14.  heketi-cli topology load --user admin --secret 123456 --json=/home/lzm/OnceML/benchmarks/IO/clusterFS/heketi-client/share/heketi/topology-sample.json
15. 再创建storage-class: kubectl apply -f benchmarks/IO/clusterFS/storage-class.yaml
16. 测试一下：kubectl apply -f benchmarks/IO/clusterFS/glusterfs-pvc.yaml
    kubectl apply -f benchmarks/IO/clusterFS/gluster-pod.yaml



太麻烦了，还是用k8s的方式部署

1. cat heketi-service-account.json 
2. kubectl apply -f heketi-service-account.json 
3. kubectl get sa

   kubectl apply -f deploy-heketi-clusterrole.yaml
   kubectl apply -f deploy-heketi-gluster-admin.yaml

5. kubectl create secret generic heketi-config-secret --from-file=./heketi.json 
6. kubectl create -f heketi-bootstrap.json 
7. kubectl apply -f heketi-deployment.json(这一步可以放在第9步后面执行)
8. kubectl get pods
9. 现在开始创建gfs集群，，要使用上面的heketi-cli
    - 首先修改topology-sample.json文件，目的是让heketi发现gluster集群
    - 获取deploy-heketi的clutserIP： kubectl get svc|grep heketi
    - kubectl port-forward deploy-heketi-6c687b4b84-l7lws 8080:8080进行端口转发
    - 测试端口 curl http://127.0.0.1:8080/hello
    - 最后，为Heketi CLI客户端设置一个环境变量，以便它知道Heketi服务器的地址。
        export HEKETI_CLI_SERVER=http://127.0.0.1:8080
    - 再将拓扑结构提交上去heketi-cli --user admin --secret 'My Secret' topology load --json=topology-sample.json
失败了。。。。。。


-----
静态pv的操作：
见https://jimmysong.io/kubernetes-handbook/practice/using-glusterfs-for-persistent-storage.html
1. kubectl apply -f benchmarks/IO/clusterFS/gluster-endpoints.yaml
2. kubectl apply -f benchmarks/IO/clusterFS/gluster-svc.yaml
2. kubectl apply -f benchmarks/IO/clusterFS/gluster-pod.yaml

上面测试了下，发现是正常的，下面创建pv、pvc
1. kubectl apply -f benchmarks/IO/clusterFS/gluster-pv.yaml
2. kubectl apply -f benchmarks/IO/clusterFS/glusterfs-pvc.yaml

kubectl apply -f benchmarks/IO/clusterFS/job.yaml
