# buildah 1.44.0 — 编译笔记

## 基本信息
- **软件**: buildah 1.44.0 (Go 容器镜像构建工具)
- **源码**: https://api.github.com/repos/containers/buildah/tarball/v1.44.0
- **日期**: 2026-05-29

## 编译环境
- **平台**: HarmonyOS (OpenHarmony) arm64
- **Go**: 1.25.8 (/storage/Users/currentUser/usr/local/go/bin/go)
- **关键问题**: Go linker mmap 在 HMDFS 上失败，需设置 GOTMPDIR/TMPDIR 到 tmpfs

## 编译过程

### 问题1: Go linker "mapping output file failed: permission denied"
- **根因**: HMDFS 文件系统不支持 Go linker 所需的 mmap MAP_SHARED 操作
- **解决**: 设置 `GOTMPDIR=/data/storage/el2/base/haps/entry/files` 和 `TMPDIR=/data/storage/el2/base/haps/entry/files`
- **注意**: 此目录是 tmpfs 挂载，支持 mmap 操作

### 问题2: entrypoint_amd64.gz 交叉编译失败
- **根因**: Makefile 默认在 arm64 上交叉编译 amd64 entrypoint，Go linker mmap 问题
- **解决**: 修改 embed directive 从 entrypoint_amd64.gz 改为 entrypoint_arm64.gz
- **修改文件**: internal/mkcw/entrypoint.go 和 Makefile

### 编译命令
```bash
export PATH=/storage/Users/currentUser/usr/local/go/bin:$PATH
export GOCACHE=/data/storage/el2/base/haps/entry/files/go-build
export GOPATH=/storage/Users/currentUser/go
export TMPDIR=/data/storage/el2/base/haps/entry/files
export GOTMPDIR=/data/storage/el2/base/haps/entry/files
export GOPROXY=https://proxy.golang.org,direct
export CGO_ENABLED=1

# 先编译 entrypoint_arm64
GOOS=linux GOARCH=arm64 go build -ldflags "-E _start -s" -o internal/mkcw/embed/entrypoint_arm64 ./internal/mkcw/embed

# 编译主二进制
go build \
  -ldflags '-X main.GitCommit=v1.44.0 -X main.buildInfo=1747804800' \
  -tags "containers_image_openpgp exclude_graphdriver_btrfs exclude_seccomp exclude_apparmor no_libsubid no_systemd no_sqlite nolinkednet" \
  -o bin/buildah ./cmd/buildah
```

## Build Tags 说明
- `containers_image_openpgp`: 使用 OpenPGP 签名验证（必须）
- `exclude_graphdriver_btrfs`: 排除 btrfs 图驱动（不可用）
- `exclude_seccomp`: 排除 seccomp 支持（libseccomp 不可用）
- `exclude_apparmor`: 排除 apparmor 支持（libapparmor 不可用）
- `no_libsubid`: 不使用 libsubid
- `no_systemd`: 不使用 systemd
- `no_sqlite`: 不使用 sqlite 存储
- `nolinkednet`: 使用动态网络配置

## 安装产物
- bin/buildah (65MB, AArch64 ELF)
- share/bash-completion/completions/buildah

## 功能限制
- seccomp/apparmor/btrfs 等功能不可用（平台限制）
- mkcw (confidential workload) 仅支持 arm64 entrypoint
- buildah 运行需容器存储配置（storage-run 目录权限）

**编译结束**
**最终状态**: built
---

**编译结束**: 2026-05-29 11:22
**最终状态**: published
