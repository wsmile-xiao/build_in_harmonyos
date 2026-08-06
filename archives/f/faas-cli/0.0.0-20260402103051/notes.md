# faas-cli 编译笔记

## 基本信息

- 软件名: faas-cli
- 版本: 0.0.0-20260402103051
- 类型: go 命令行工具
- 上游仓库: https://github.com/openfaas/faas-cli
- 上游 commit: bf309592e77386f69cada2f4ceecac9f35f6d206
- 编译日期: 2026-08-06
- 最终状态: published

## 编译过程

### 构建系统

Go 项目，使用 vendored 依赖（-mod=vendor），CGO 禁用。

### 编译方式

使用 Go SDK 1.24.0 直接编译：
- GOOS=linux GOARCH=arm64 CGO_ENABLED=0
- GOFLAGS=-mod=vendor
- ldflags: `-s -w -X github.com/openfaas/faas-cli/version.GitCommit=bf309592 -X github.com/openfaas/faas-cli/version.Version=0.0.0-20260402103051`

### 鸿蒙平台适配要点

1. **Go SDK 签名**: 鸿蒙平台要求所有 ELF 二进制文件签名才能执行。Go SDK 的所有二进制文件（go, gofmt, pkg/tool/linux_arm64/*）需要使用 `binary-sign-tool` 签名。
2. **链接器输出路径**: Go 链接器在 HMDFS 上 mmap 输出文件失败。需要将输出目录设为 `/data/storage/el2/base/haps/entry/files/` 下的沙箱目录（OHOS_GO_WORKDIR）。
3. **临时目录**: 使用 `/data/storage/el2/base/haps/entry/files/faas-cli-conan-go` 作为 Go 工作空间，包含 tmp、cache、link-out、test-out 等子目录。
4. **构建产物签名**: 编译出的 faas-cli 二进制需要使用 `binary-sign-tool` 签名后才能在鸿蒙平台执行。

### 测试

上游测试通过 8/9 个包：
- PASS: faas-cli (root), builder, config, flags, proxy, schema, version, versioncontrol
- SKIP: exec, schema/knative/v1, schema/openfaas/v1, schema/store/v2, test, util (无测试文件)
- FAIL: commands.Test_templatePull (git 集成测试，在 OHOS 沙箱中 git commit 失败因无文件可提交)

### 验证

- 二进制文件: `bin/faas-cli`
- 功能验证: `faas-cli version` 输出正确的版本和 commit 信息 ✅
- 帮助验证: `faas-cli --help` 正常输出 ✅

## 制品信息

- 构建产物: `bin/faas-cli` (ELF aarch64, ~11MB)
- 类型: 命令行工具 (application)

## 备注

此软件为 Go 语言编写的命令行工具，使用 vendored 依赖模式构建，无需网络下载依赖。
---

**编译结束**: 2026-08-06 10:30
**最终状态**: published
