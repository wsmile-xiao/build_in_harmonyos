# MariaDB Connector/C

MariaDB Connector/C 是 MariaDB 的 C 语言客户端库。

## 功能概述
- 连接 MariaDB/MySQL 数据库
- 支持异步操作
- 认证插件支持

## OHOS 适配要点
- X18 寄存器在 HarmonyOS 上是保留寄存器
- 需要使用 -fPIC 编译选项

## 依赖关系
- OpenSSL
- zlib

## 参考资料
- 官网: https://mariadb.com
- 源码: https://github.com/mariadb-corporation/mariadb-connector-c
