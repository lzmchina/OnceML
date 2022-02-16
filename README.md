# OnceML
OnceML是一个用于部署端到端的模型迭代、模型服务的ML pipeline框架

## Description

> 1. 目前已经有TFX、kubeflow pipeline这一类的框架了，为什么还要做一个pipeline框架呢？

目前的ML pipeline框架总体而言是将pipeline的每个组件当作一个job，通过组件之间的先后执行顺序，用kubernetes、apache beam、apache airflow等编排框架将这些任务按序执行。但是针对一个模型的生命周期而言，应当是训练——部署——迭代——训练……这样一个反复的过程。

ML pipeline也是提供一种devops的方式，能让ai开发者自己就能参与模型的开发、运维过程——当某一组件的代码逻辑变更，能够迅速地将新版本的ML pipeline部署上线。

OnceML框架同样也是出于减轻ai开发人员的运维负担，能够提供比较轻量、简化的工具，帮助快速上线一个模型。

从功能上来看，本框架聚焦于以下功能：
1. 一个pipeline负责持续地迭代ML Model，包括不断地获得数据、





<!-- pyscaffold-notes -->

## Note

This project has been set up using PyScaffold 4.0.1. For details and usage
information on PyScaffold see https://pyscaffold.org/.