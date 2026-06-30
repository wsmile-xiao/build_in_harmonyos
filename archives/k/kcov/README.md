# kcov - 代码覆盖率工具

## 简介

kcov 是一个代码覆盖率收集工具，支持多种编程语言和输出格式。它使用 ptrace 和 DWARF 调试信息来跟踪代码执行路径，生成详细的覆盖率报告。

## 主要功能

- **多语言支持**: C/C++, Bash, Python 等脚本语言
- **多种输出格式**: JSON, HTML, Cobertura, SonarQube XML
- **动态跟踪**: 使用 ptrace 实时跟踪进程执行
- **调试信息解析**: 基于 libdw (elfutils) 解析 DWARF 信息

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 38 | published | 2026-05-27 | musl libc 适配，禁用 Coveralls 上报 |

## 平台支持

- ✅ OpenHarmony (aarch64)
- ✅ musl libc 环境

## 依赖

- elfutils (libdw, libelf) - DWARF/ELF 解析
- zlib - 压缩支持
- libintl - 国际化

## 使用示例

```bash
# 基本用法
kcov /path/to/output /path/to/program

# 测试脚本
kcov /path/to/output /bin/bash /path/to/script.sh

# Python 程序
kcov /path/to/output /usr/bin/python3 /path/to/script.py
```

## 注意事项

### OpenHarmony 特殊配置

- **ptrace 权限**: kcov 需要 ptrace 权限跟踪进程
  - 可能需要 root 权限
  - 或使用 capabilities: `sudo setcap cap_sys_ptrace+ep kcov`

- **Coveralls 上报**: 已禁用（因 libcurl 兼容性问题）
  - 不影响本地覆盖率收集
  - 仍可生成 JSON/HTML 报告

## 相关链接

- 官方网站: https://github.com/SimonKagstrom/kcov
- 文档: https://github.com/SimonKagstrom/kcov/wiki

---

*归档时间: 2026-05-27*
*编译器: clang/clang++*