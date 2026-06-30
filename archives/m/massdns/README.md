# massdns

**描述**: 高性能DNS stub resolver，支持批量DNS解析

**许可证**: GPL-3.0-only

**官网**: https://github.com/blechschmidt/massdns

## 编译版本

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|----------|----------|
| 1.1.0 | built | cmake | 2026-06-03 |

## 功能特性

- 高并发DNS查询（支持epoll）
- 批量域名列表解析
- 多种输出格式（简单文本、JSON、二进制、域名列表）
- 支持多种DNS记录类型（A、CNAME、MX等）
- 可配置resolver列表
- 多进程模式
- 非递归查询模式（DNS缓存窥探）

## OHOS平台注意事项

- lld链接器因缺少libxml2不可用，需使用 `-fuse-ld=bfd`
- `--version` 显示 "massdns ?"（非git仓库构建限制）
- CMakeLists.txt无install目标，需手动安装