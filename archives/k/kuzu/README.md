# kuzu — OpenHarmony 预编译包

[kuzu](https://kuzudb.com/) 是一个嵌入式图数据库引擎，支持 Cypher 查询语言。

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.11.3 | published | 2026-06-03 | OHOS aarch64 预编译，含 FTS/JSON/Vector/Algo 扩展 |

## 编译要点

- 构建系统: cmake
- 编译器: Clang 15.0.4 (aarch64-unknown-linux-ohos)
- 主要适配: C++20 ranges→std 等价替换、typename 修复、simsimd NEON-only stub、移除 -latomic