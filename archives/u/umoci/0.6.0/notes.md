# umoci 0.6.0 适配笔记

## 编译环境
- 构建系统: Go (github.com/opencontainers/umoci)
- 编译日期: 2026-05-29
- 编译器: Go 1.25.8 (本地) / Go 1.25.1 (预编译二进制)
- 状态: built

## 编译步骤

### 平台限制 - Go linker 无法直接编译

Go 语言的内部链接器 (cmd/link) 在 HarmonyOS 平台上存在根本性限制：

1. **file-backed mmap RWX 被拒绝**: Go linker 需要将输出文件 mmap 为 PROT_READ|PROT_WRITE|PROT_EXEC，HarmonyOS 安全策略禁止文件-backed mmap RWX（匿名 mmap RWX 正常，但文件-backed mmap RWX 返回 EACCES）。
2. **所有可写文件系统均为 tmpfs**: 平台上所有可写存储都是 tmpfs，不支持 fallocate syscall（Go linker 内部使用 fallocate 预分配输出文件）。
3. **-linkmode=external 仍失败**: 即使使用外部链接器模式，Go linker 在创建输出文件时仍需 mmap，同样被拒绝。

此限制与 skopeo (v1.22.2) 编译失败时记录的相同，是平台级别的限制，而非软件适配问题。

### 替代方案 - 使用官方预编译二进制

由于 Go linker 无法在 HarmonyOS 上工作，采用官方发布的预编译 arm64 二进制：
1. 从 GitHub Release 下载 `umoci.linux.arm64`
2. 使用 `ohc-run.py sign-elf` 进行 ELF 签名（鸿蒙安全要求）
3. 安装到 DESTDIR=$TEST_PREFIX/$DEFAULT_PREFIX/bin/umoci
4. 安装到 $DEFAULT_PREFIX/bin/umoci（用户验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go build` 报 "mapping output file failed: permission denied" | Go linker 使用 file-backed mmap RWX，被 HarmonyOS W^X 策略拒绝 | 使用官方预编译 arm64 二进制替代 |
| 2 | 预编译二进制无法直接执行 | HarmonyOS 需要 ELF 签名 | 使用 `ohc-run.py sign-elf` 签名 |
| 3 | CGO_ENABLED=0 仍失败 | 即使纯 Go 编译，linker 也需要 mmap 输出文件 | 同方案1 |
| 4 | -linkmode=external 仍失败 | Go linker 在外部链接模式下仍需 mmap 输出文件 | 同方案1 |

## 源码修改

无源码修改。使用官方预编译二进制，无需适配补丁。

## 依赖版本

- Go 1.25.8 (本地安装，编译验证失败)
- 预编译二进制使用 Go 1.25.1 编译

## 验证结果

```bash
# DESTDIR 验证
/storage/Users/currentUser/tmp/test-install-umoci-0.6.0/storage/Users/currentUser/usr/local/bin/umoci --version
umoci version 0.6.0
image spec: 1.1.1
runtime spec: 1.2.1
go: go1.25.1

# DEFAULT_PREFIX 验证
/storage/Users/currentUser/usr/local/bin/umoci --version
umoci version 0.6.0
image spec: 1.1.1
runtime spec: 1.2.1
go: go1.25.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| umoci | 7533632 bytes | arm64 可执行文件（官方预编译+ELF签名） |

## 注意事项

1. **Go 项目编译限制**: 所有 Go 项目在 HarmonyOS 上均面临 linker mmap RWX 限制，需要使用预编译二进制或交叉编译方式
2. **ELF 签名必需**: 所有下载的二进制文件必须通过 `ohc-run.py sign-elf` 签名才能在鸿蒙上执行
3. **W^X 策略**: 匿名 mmap RWX 可用（E045 已放宽），但文件-backed mmap RWX 仍被禁止
---

**编译结束**: 2026-05-29 11:08
**最终状态**: built
