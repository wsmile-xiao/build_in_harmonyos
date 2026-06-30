# Memcached

Memcached 是一个高性能的分布式内存对象缓存系统。

## 功能概述
- 内存缓存服务
- 减少数据库负载
- 加速动态Web应用

## OHOS 适配要点
- config.guess 需要更新支持 HarmonyOS
- mremap syscall 在 OHOS 上不支持

## 依赖关系
- libevent

## 参考资料
- 官网: https://memcached.org
- 源码: https://github.com/memcached/memcached
