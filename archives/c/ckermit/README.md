# C-Kermit

**软件名称**: C-Kermit
**分类**: 网络通信 / 文件传输
**官网**: https://kermitproject.org/

## 软件简介

C-Kermit 是一个多功能的终端仿真和文件传输程序，支持：
- Kermit 协议文件传输
- Telnet/SSH 远程连接
- FTP/HTTP 客户端
- 终端仿真与 pty 控制
- 脚本编程自动化

## 鸿蒙适配版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 302 | ✅ published | 2026-05-28 |

## 平台适配要点

### musl libc 兼容处理

| 问题 | 解决方案 |
|------|---------|
| getusershell 缺失 | 定义 `NOGETUSERSHELL` 禁用 |
| vhangup 缺失 | 使用 `HAVE_OPENPTY` 替代 |
| stdin->_cnt 访问 | 使用 `CMD_CONINC` 替代 |

### 编译要点

```bash
# 自定义 makefile，需指定目标平台
make linux
```

### 关键补丁

- `0001-ckcdeb.h.patch` - 禁用 getusershell
- `0003-ckucmd.c.patch` - FILE 结构适配
- `0004-ckupty.c.patch` - 禁用 vhangup，使用 openpty

## 功能验证

### 核心功能

| 功能 | 状态 |
|------|------|
| Kermit 协议传输 | ✅ 正常 |
| Telnet 连接 | ✅ 正常 |
| FTP 客户端 | ✅ 正常 |
| 终端仿真 | ✅ 正常 |
| pty 控制 | ✅ 正常 (HAVE_OPENPTY) |
| 脚本编程 | ✅ 正常 |

### 脚本变量语法

| 语法 | 用途 | 示例 |
|------|------|------|
| `\m(name)` | 宏变量 | `\m(testvar)` |
| `\v(name)` | 内置变量 | `\v(date)` |
| `\{text}` | 字符转义 | `\{brace}` |

## 测试评分

**98/100** - 功能完整，强烈推荐

详细测试报告见各版本目录下的 `reports/test-report.md`

## 依赖关系

- 无外部库依赖
- 需 gcc/clang 编译器

## 使用建议

1. 文件传输场景：Kermit/FTP/HTTP 协议
2. 远程连接：Telnet 连接远程主机
3. 自动化脚本：使用 `\m()` 变量语法
4. 终端仿真：交互式终端会话