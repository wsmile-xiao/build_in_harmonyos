# Kyoto Cabinet

**类别**: Key-Value Database
**官网**: http://fallabs.com/kyotocabinet/
**描述**: 高性能键值存储数据库，支持多种数据库类型

---

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.2.80 | published | 2026-05-29 | 功能测试通过 |

---

## 功能特性

- **HashDB**: 基于哈希表的键值存储
- **TreeDB**: 基于B+树的有序键值存储
- **PolyDB**: 多态数据库（自动适配类型）
- **ForestDB**: 文档数据库（支持分层结构）

---

## 使用场景

- 缓存系统
- 配置存储
- 会话管理
- 元数据索引

---

## 注意事项

1. ForestDB 数据库文件是目录结构，删除时需使用 `rm -rf`
2. 测试套件执行时间较长（约540秒）
3. 支持 C++ API 和命令行工具

---

## 相关链接

- [API 文档](http://fallabs.com/kyotocabinet/api/)
- [命令行工具](http://fallabs.com/kyotocabinet/cliapi.html)

---

*最后更新: 2026-05-30*