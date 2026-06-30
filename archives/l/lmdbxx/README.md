# lmdbxx - C++11 wrapper for LMDB

## 软件简介

lmdbxx 是一个轻量级、高效的 C++11 封装库，为 LMDB（Lightning Memory-Mapped Database）提供面向对象的接口。它采用 RAII 语义管理资源，提供错误检查的程序式接口和资源接口。

### 主要功能

- **RAII 语义**：自动管理 LMDB 资源（环境、事务、数据库、游标）
- **异常安全**：所有操作都有错误检查和异常处理
- **零开销**：header-only 设计，无额外运行时开销
- **现代 C++**：使用 C++11 特性（auto、range-based for 等）

## OHOS 适配

### 适配要点

1. **Header-only 库**：只需安装头文件，无需编译
2. **标准 C++11**：无平台特定代码，直接可用
3. **无编译依赖**：编译 lmdbxx 本身不需要 LMDB
4. **运行时依赖**：使用 lmdbxx 的程序需要链接 LMDB 库

### 已知问题

- 无已知鸿蒙平台兼容性问题

## 依赖关系

### 编译依赖

- 无（header-only 库）

### 运行依赖

- **LMDB**：提供 lmdb.h 头文件和 liblmdb 库
- C++11 编译器（clang++ / g++）

## 版本信息

### 当前版本

- **0.9.14.0**（2025-04-22 发布）
- 兼容 LMDB 0.9.x 系列（至少到 0.9.14）

### 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.9.14.0 | built | 2026-06-15 |

## 参考资料

- **官网**：http://lmdbxx.sourceforge.net/
- **源码**：https://github.com/drycpp/lmdbxx
- **API 文档**：http://lmdbxx.sourceforge.net/0.9.14/
- **LMDB 官网**：http://symas.com/mdb/

## 使用示例

```cpp
#include <lmdb++.h>

int main() {
    // 创建并打开 LMDB 环境
    auto env = lmdb::env::create();
    env.open("./example.mdb", 0, 0664);

    // 写事务中插入数据
    auto wtxn = lmdb::txn::begin(env);
    auto dbi = lmdb::dbi::open(wtxn, nullptr);
    dbi.put(wtxn, "key", "value");
    wtxn.commit();

    // 读事务中查询数据
    auto rtxn = lmdb::txn::begin(env, nullptr, MDB_RDONLY);
    std::string value;
    dbi.get(rtxn, "key", value);

    return 0;
}
```

编译命令：
```bash
clang++ -std=c++11 -llmdb example.cc -o example
```