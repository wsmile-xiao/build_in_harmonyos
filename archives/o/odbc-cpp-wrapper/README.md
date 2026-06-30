# odbc-cpp-wrapper

## 简介

odbc-cpp-wrapper 是 SAP 开发的 ODBC C++ 包装库，提供面向对象的 API 来简化 ODBC 数据库访问。

## 特性

- 面向对象的 C++ API
- 封装 ODBC 复杂的 C API
- 支持连接管理、结果集处理、参数绑定等
- Apache 2.0 许可证

## 编译信息

- 最新版本: 1.6
- 构建系统: cmake
- 编译状态: built

## 依赖

- unixODBC 或 iODBC（必需）

## 使用方式

```cpp
#include <odbc/Environment.h>
#include <odbc/Connection.h>

// 创建环境
odbc::Environment env = odbc::Environment::create();

// 连接数据库
odbc::Connection conn = env.createConnection("DSN=mydb");
```

## 已编译版本

| 版本 | 状态 | 日期 | 产物 |
|------|------|------|------|
| 1.6 | built | 2026-06-02 | odbc-cpp-wrapper-1.6-ohos-aarch64.tar.gz |