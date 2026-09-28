# kubo-migration

kubo-migration 是 Alpine Linux kubo 0.42.0 的 `kubo-migration` 子包对应的
IPFS 仓库迁移工具 `fs-repo-15-to-16`：把 IPFS 仓库从 repo v15 迁移到 v16。

## 功能概述

- 在 IPFS 节点 config 的 `.Addresses`（Swarm / Announce / AppendAnnounce /
  NoAnnounce）中，为每个 `/udp/<port>/quic-v1` 监听追加同端口的
  `/udp/<port>/webrtc-direct` 监听（Kubo 0.42.0 新增 WebRTC 直连地址）
- 迁移前自动备份 `config.15-to-16.bak`，支持 `-revert` 完整回退到 v15
- 原子写：迁移过程通过 `atomicfile` 临时文件 + rename 保证 config 不出现中间态
- 纯 Go 静态 CLI，单文件可执行，无运行时依赖

## 使用方法

```bash
# 正向迁移（-path 为 IPFS 仓库路径）
fs-repo-15-to-16 -verbose -path=<ipfs-repo-path>

# 回退迁移
fs-repo-15-to-16 -verbose -revert -path=<ipfs-repo-path>

# 查看帮助
fs-repo-15-to-16 -help
```

## OHOS 适配要点

- 纯 Go，`CGO_ENABLED=0` + `GOOS=linux` + `GOARCH=arm64` 静态交叉编译
- OHOS/HMDFS 上 Go linker 对输出文件 mmap 失败，链接输出须放在可写本地文件系统
  后再复制回包目录（conan 配方内置）
- OHOS 上最终 ELF 须经 `binary-sign-tool` 签名才能执行（conan 配方内置）
- 依赖 `github.com/ipfs/fs-repo-migrations/tools` 已完整 vendor，构建离线

## 依赖关系

- 编译依赖：Go >= 1.22（本地使用 1.26.3）
- 运行依赖：无（静态二进制）

## 参考资料

- 上游仓库：https://github.com/ipfs/fs-repo-migrations
- 上游 tag：`fs-repo-15-to-16/v1.0.0`
- Alpine kubo APKBUILD（kubo-migration 子包定义）：https://gitlab.alpinelinux.org/alpine/aports

## 已编译版本

- 0.42.0（2026-09-21）
