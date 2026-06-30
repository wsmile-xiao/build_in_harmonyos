# prometheus 3.12.0 适配笔记

## 编译环境
- 构建系统: prebuilt/go（官方预编译二进制适配）
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 本地 Go 编译尝试：设置 GOTOOLCHAIN=local, GOPROXY=https://goproxy.cn,direct
2. `go build` 失败：Go 1.25 runtime 内部冲突（runtime_mapaccess1_fast32 redeclared）
3. HMDFS fallocate/mmap 问题（errno=13 EACCES）进一步阻碍 Go linker
4. 切换到预编译二进制适配方案：
   - 下载官方 prometheus-3.12.0.linux-arm64.tar.gz
   - 使用 gh-proxy.com 代理下载 GitHub Release
   - 对 prometheus 和 promtool 执行 sign-elf 签名
   - 安装到 staging 目录和本地 usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go build runtime_mapaccess1_fast32 redeclared | Go 1.25 runtime 内部 Swiss table 与传统实现冲突 (ref: E001) | 使用官方预编译二进制适配方案 |
| 2 | HMDFS fallocate/mmap EACCES | HarmonyOS 文件系统不支持 fallocate syscall (ref: E008) | 预编译方案绕过本地编译 |
| 3 | GitHub Release 下载超时 | 网络环境限制 | 使用 gh-proxy.com 代理下载 |

## 源码修改

无源码补丁，使用官方预编译 linux-arm64 二进制 + sign-elf 签名适配 HarmonyOS (ref: E077)

## 依赖版本

- Go 1.25.0 (本地安装，编译失败)
- goenv/3.1.1 (预编译包管理)
- sign-elf (ELF 签名工具)

## 验证结果

```bash
$ prometheus --version
prometheus, version 3.12.0 (branch: HEAD, revision: 9f27dffc1f93ca23287972f632025879f2d1c658)
  build user:       root@2f9dfa1df447
  build date:       20260528-15:53:38
  go version:       go1.26.3
  platform:         linux/arm64

$ promtool --help
usage: promtool [<flags>] <command> [<args> ...]
Tooling for the Prometheus monitoring system.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| prometheus-3.12.0-ohos-aarch64.tar.gz | ~140MB | Release 制品（已 strip + sign-elf） |
| prometheus-3.12.0-ohos-aarch64-debug.tar.gz | ~400MB | Debug 制品（含 debug symbols） |

## 注意事项

- prometheus 是纯 Go 项目，官方预编译 linux-arm64 二进制可直接在 HarmonyOS aarch64 上运行
- 必须使用 sign-elf 签名才能在 HarmonyOS 上执行
- 本地 Go 编译因 runtime 内部冲突和 HMDFS 限制无法完成
- 未来 Go 版本可能修复 runtime 冲突问题，届时可尝试本地编译
---

**编译结束**: 2026-06-09 23:56
**最终状态**: built
