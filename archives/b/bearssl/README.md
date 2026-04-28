# BearSSL — OpenHarmony 编译档案

## 软件简介
BearSSL 是优化的 SSL/TLS 库，专注于安全性和小代码体积。纯 C 实现无外部依赖，适合嵌入式系统。

## 功能概述
- TLS 1.0/1.1/1.2 支持
- 完整加密算法套件
- X.509 证书验证
- 静态链接为主

## OHOS 适配要点
- 自定义 Makefile 系统，无标准 configure/make install
- 需创建 conf/Ohos.mk 配置文件
- 编译命令: `make CONF=Ohos`
- 安装需手动复制 libbearssl.a 和头文件
- DLL 模式不推荐（API 不稳定）

## 依赖关系
- 无外部依赖（纯 C 实现）

## 参考资料
- [BearSSL 官网](https://www.bearssl.org/)
- [BearSSL GitHub](https://github.com/ctz/bearssl)
