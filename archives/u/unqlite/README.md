# unqlite

unqlite 是 Symisc Systems 开发的事务型嵌入式 NoSQL 数据库引擎，以
self-contained ANSI C 库形式发布（amalgamation：unqlite.c + unqlite.h），
同时支持文档存储（类 MongoDB/CouchDB）与标准键值存储（类 BerkeleyDB/
LevelDB），零外部依赖、线程安全、可重入。

## OHOS 适配

- 使用上游 CMakeLists 构建静态库 `unqlite` 并安装 lib/include。
- 上游无测试套件；以真实 KV 引擎行为的消费者测试补验证（内存库打开、
  写入、取回、删除、NOTFOUND 共 6 项断言）。
- 零依赖，无补丁。

## 依赖

无。

## 参考

- https://unqlite.org
- https://github.com/symisc/unqlite
