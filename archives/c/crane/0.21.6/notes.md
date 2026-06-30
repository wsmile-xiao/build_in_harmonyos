# crane 0.21.6 编译笔记

## 编译策略

**预编译二进制方案**：Go语言在HMDFS上无法编译（SELinux+mmap限制），使用官方预编译二进制 + ohc sign-elf签名的方式部署。与grype的解决方案完全一致。

## 编译步骤

1. 从GitHub Releases下载 `go-containerregistry_Linux_arm64.tar.gz`（通过gh-proxy.com镜像）
2. 解压获得 `crane` 预编译二进制（aarch64/ARM64）
3. 使用 `ohc sign-elf` 签名（解决HMDFS执行权限问题）
4. 安装到 staging 目录和本地安装目录

## 验证结果

- `crane version` 输出 `0.21.6` ✅
- 注意：`crane --version` 不支持，使用 `crane version` 代替

## 构建系统

- build_system: custom（预编译二进制方案，非源码编译）
- 构建依赖：无（直接使用官方预编译二进制）

## 关键发现

- Go语言编译在OpenHarmony HMDFS上受限（SELinux+mmap），无法从源码编译
- crane使用 `version` 子命令而非 `--version` flag
- gh-proxy.com镜像可用于下载GitHub Release资产
---

**编译结束**: 2026-05-26 22:38
**最终状态**: built
