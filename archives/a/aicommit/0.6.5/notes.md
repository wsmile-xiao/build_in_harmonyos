# aicommit 0.6.5 适配笔记

## 编译环境
- 构建系统: custom (Go 项目，go build ./cmd/aicommit)
- 编译日期: 2026-08-10
- 编译器: Go 1.23.8 (CGO_ENABLED=0 纯静态)
- 状态: built

## 编译步骤

1. 下载源码：从官方 GitHub tag `https://github.com/coder/aicommit/archive/refs/tags/v0.6.5.tar.gz`（SHA256 b89c00eabd881344a0e1ee3fe2d5bbf5005cfd19881f5d3a4b23bc8dd0a98a0b，两次下载一致）
2. 解压到 work 目录
3. 配置 Go 工具链（go1.23.8 linux-arm64 解压到工作区，ELF 用 binary-sign-tool 签名）
4. 编译命令：
```bash
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0
go mod download
go build -trimpath -ldflags "-s -w -X main.Version=v0.6.5" -o bin/aicommit ./cmd/aicommit
```
5. 链接输出重定向到非 hmdfs 工作区（/data/storage/el2/...），再复制回 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 工具链二进制 Permission denied | hmdfs 下无 .codesign 段 ELF 被 Seccomp 拦截 | binary-sign-tool 签名 go/gofmt/pkg/tool 全部 ELF 后执行 |
| 2 | Go linker 报 mapping output file failed | linker mmap 输出文件在 hmdfs 失败（E051） | 链接输出目录放到 el2 tmpfs 工作区（ain 同款先例） |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Go 1.23.8（go.mod: go 1.21.4）
- github.com/coder/pretty、github.com/coder/serpent v0.8.0、github.com/muesli/termenv v0.15.2
- github.com/go-git/go-git/v5 v5.12.0、github.com/sashabaranov/go-openai v1.29.0、github.com/tiktoken-go/tokenizer v0.1.1
- 无 C/C++ 依赖（CGO_ENABLED=0 纯静态）

## 上游测试情况

- `find . -name "*_test.go"`：仓库根目录与 cmd/aicommit/ 均无测试文件
- 上游无自动化测试用例（记 0），本包以 test_package 冒烟测试代替：`aicommit version` 断言 v0.6.5、`aicommit --help`、`aicommit version --help`

## 验证结果

```bash
$ ./bin/aicommit version
aicommit v0.6.5
```

编译产物：stripped ELF arm64，conan-verify G0-G4 + L2/L4/L5 全部通过。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/aicommit | aicommit 命令行工具 (stripped) |

## 注意事项

1. **Go 工具链签名**：OHOS 下 Go SDK 的 go/gofmt/pkg/tool/* 均为未签名 ELF，必须用 binary-sign-tool 签名后才能执行（配方内 `_sign_go_sdk_if_ohos` 自动处理）。
2. **HMDFS 链接限制**：Go linker 在 hmdfs 上 mmap 输出失败，链接输出目录必须放在非 hmdfs 工作区（OHOS 下默认 /data/storage/el2/base/haps/entry/files/aicommit-conan-go）。
3. **运行依赖**：aicommit 运行时需要 git 仓库和 OPENAI_API_KEY（或 --save-key 持久化）；测试仅覆盖不依赖外部服务的 version/--help 入口。
---

**编译结束**: 2026-08-10 10:34
**最终状态**: built
