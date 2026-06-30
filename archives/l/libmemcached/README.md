# libmemcached

libmemcached 是 memcached 的 C 语言客户端库。

## 功能概述
- memcached 客户端 API
- 多种操作工具
- 异步和非阻塞模式

## OHOS 适配要点
- rindex 函数需要替换为 strrchr
- static environ 声明冲突

## 依赖关系
- memcached

## 参考资料
- 官网: https://libmemcached.org
