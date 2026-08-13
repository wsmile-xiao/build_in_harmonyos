# algolia (algolia/cli) 1.14.0 适配笔记

## 概述

**软件**: Algolia CLI 1.14.0（管理 Algolia 应用/索引/记录/API Key 的官方命令行工具）
**上游**: https://github.com/algolia/cli（tag v1.14.0）
**语言/构建**: Go（go.mod go 1.23.0 + toolchain go1.23.4）
**状态**: built

## 依赖分析

| 依赖 | 说明 |
|------|------|
| Go 工具链 | 1.23.x 必需（go.mod 要求）；配方内自举下载 go1.23.8 linux-arm64 SDK（参考 aicommit 0.6.5 先例） |
| Go 模块 | cobra/viper/algoliasearch-client-go/v4/survey 等纯 Go 依赖，`go mod download` 经 goproxy.cn 获取 |
| C 依赖 | 无（CGO_ENABLED=0 纯静态） |

无第三方 C 库依赖，依赖链已全部可获取，无需等待未合入依赖。

## 上游测试（本地实测）

```
go test -exec <sign-wrapper> -v ./... -p 1 -count=1
```

- **测试包**: 91 个包 ok（40 个包无测试文件）
- **用例数**: 457 个通过（`--- PASS` 计数），**0 FAIL，0 SKIP**
- **通过率**: 457/457 = 100%（本地 OHOS 实测）
- e2e 目录有 `//go:build e2e` 标签，默认排除（需 testscript 环境）
- 日志: `reports/upstream-tests.md` 附 go test -v 实测日志

## 关键适配点

### 1. Go SDK 自举（配方内下载）

go1.23.8.linux-arm64.tar.gz（sha256=9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992），
下载源：golang.google.cn（主）→ mirrors.aliyun.com → dl.google.com（兜底）。
下载到 `_go_workspace()/go-sdk/go1.23.8-arm64/go`。

### 2. OHOS ELF 签名（必须）

OHOS 上**未签名 ELF 无法执行**（fork/exec: permission denied）。需要：
1. Go 工具链二进制签名：`bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*`（共 20 个 ELF）
2. 最终产物 algolia 签名
签名方式：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1 -inFile X -outFile Y -signAlg SHA256withECDSA`

### 3. HMDFS 链接限制（E051/E046）

go link 在 hmdfs 上 mmap 输出文件失败（`mapping output file failed: permission denied`）。
解法：链接输出目录 + GOCACHE + GOTMPDIR + GOMODCACHE 指向 `/data/storage/el2/base/haps/entry/files/algolia-conan-go/`（ext2 风格工作区，可写可执行）。

### 4. go test 测试二进制签名包装器

go test 每次生成新的测试二进制（未签名），OHOS 上无法直接 fork/exec。
解法：`go test -exec <sign-exec.sh>`，包装器先对测试二进制签名再 exec。
sign-exec.sh 与配方 `_sign_elf_if_ohos` 逻辑一致（objcopy 去 codesign → binary-sign-tool 签名 → chmod）。

### 5. 版本注入

上游 GoReleaser 构建时用 `-X=github.com/algolia/cli/pkg/version.Version` 注入版本，
源码默认 `var Version = "main"`。配方 ldflags：
```
-s -w -X=github.com/algolia/cli/pkg/version.Version=v1.14.0
```
使 `algolia --version` 输出 `algolia version 1.14.0`。

## 构建步骤（本地验证通过）

1. `generate()`：下载/定位 Go 1.23.8 SDK（含签名），设置 GOOS=linux/GOARCH=arm64/CGO_ENABLED=0/GOPROXY
2. `build()`：`go build -trimpath -ldflags "..." -o <link-out>/algolia ./cmd/algolia`
3. 签名 algolia ELF → 复制到 build_folder/bin/
4. `package()`：bin/algolia + licenses/LICENSE + res/README.md

## 验证结果

- 编译状态：通过（本地 go1.23.8 构建 + 签名，`algolia --version` → `algolia version 1.14.0`）
- 上游测试用例通过率：457/457 = 100%（本地实测，0 FAIL）
- test_package：--version / --help / auth --help 冒烟通过
- 依赖：Go 1.23.8 SDK（自举下载）+ 纯 Go 模块（goproxy.cn）

---

**编译验证**: 2026-08-13
**最终状态**: built
