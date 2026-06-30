# duf

Disk Usage/Free utility - a better `df` alternative

duf 是一个用 Go 编写的磁盘使用/空闲空间查看工具，类似于 `df` 命令但输出更加美观直观。

## 版本

- 0.9.1 (2026-06-01) - built ✅

## 描述

duf 显示磁盘使用情况，支持：
- 彩色输出
- 多种排序方式
- 文件系统类型识别
- 设备过滤/隐藏

## 关键编译信息

- 构建系统: Go (custom)
- 无 configure/make 流程，直接 go build
- CGO_ENABLED=0 静态编译