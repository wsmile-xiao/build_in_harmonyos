# gopass

gopass 是一个基于 Go 语言编写的命令行密码管理器，是标准 Unix 密码管理器 pass 的重新实现。它支持 GPG 加密、Git 版本控制、多收件人密码管理等功能。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.16.0 | published | 2026-06-17 |

## 构建说明

gopass 是 Go 项目，使用 `go build` 编译，不使用 autotools/configure。

关键构建参数：
- `CGO_ENABLED=0` - 静态编译
- `-tags=netgo` - 纯 Go 网络实现
- `-trimpath` - 清除路径信息
- 不使用 `-buildmode=pie`（鸿蒙上 PIE 模式会 segfault）
