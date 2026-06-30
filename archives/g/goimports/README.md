# goimports

Go import 格式化工具，自动管理和排序 Go 源文件中的 import 语句。

## 简介

goimports 是 golang.org/x/tools 的一部分，用于：
- 自动添加缺失的 import 包
- 自动删除未使用的 import 包
- 按 Go 标准格式排序 import 语句
- 将 import 分为标准库、第三方库和本地包三个区域

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.32.0 | built | 2026-06-08 |

## 编译说明

goimports 使用 Go 编译系统（非 autotools/cmake），编译命令：
```bash
CGO_ENABLED=0 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o goimports ./cmd/goimports/
```

## 依赖

- Go 1.26.4+
- golang.org/x/mod (自动下载)