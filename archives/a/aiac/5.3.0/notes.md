# aiac v5.3.0 — 编译适配笔记

## 软件简介

aiac（Artificial Intelligence Infrastructure-as-Code Generator）—— 纯 Go 编写的 CLI，
通过 LLM 后端（OpenAI / Azure OpenAI / Amazon Bedrock / Ollama）生成基础设施即代码模板。
源码: https://github.com/gofireflyio/aiac

## 上游真实技术事实

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/gofireflyio/aiac |
| 上游 tag | v5.3.0 |
| 源码 URL | https://github.com/gofireflyio/aiac/archive/refs/tags/v5.3.0.tar.gz |
| 源码 SHA256 | `45e48cd8958d835b402e0e68d7aa8b9642deb535464dad5d6b83fb8f8ed3d79e` |
| 上游语言 | Go（纯 Go，无 `import "C"`，无 cgo 指令） |
| 构建系统 | Go modules（`go.mod`/`go.sum`） |
| go.mod | `module github.com/gofireflyio/aiac/v5`，`go 1.19` |
| 命令入口 | 根包 `github.com/gofireflyio/aiac/v5`（main.go 在仓库根，**不是** ./cmd 子目录） |
| `*_test.go` 数量 | **0** |
| `TestXxx` / `BenchmarkXxx` / `ExampleXxx` 数量 | **0** |
| CI workflow | `.github/workflows/release.yaml`（GoReleaser 发布）+ `codesee-arch-diagram.yml`（代码图）——**无任何测试 step** |
| `go test -v -count=1 ./...` 实测 | 每包 `[no test files]`，退出码 0，真实测试数 = **0** |
| **上游真实测试统计** | **0（no_tests）** |
| CGO 依赖 | 无 |
| license | Apache-2.0 |

## 直接依赖（go.mod）

| 模块 | 版本 | 用途 |
|---|---|---|
| github.com/BurntSushi/toml | v1.4.0 | 配置解析 |
| github.com/adrg/xdg | v0.4.0 | XDG 配置路径 |
| github.com/alecthomas/kong | v0.7.1 | CLI 参数解析 |
| github.com/atotto/clipboard | v0.1.4 | 剪贴板 |
| github.com/aws/aws-sdk-go-v2 | 全家 | Bedrock 后端 |
| github.com/briandowns/spinner | v1.19.0 | 交互 spinner |
| github.com/fatih/color | v1.7.0 | 彩色输出 |
| github.com/ido50/requests | v1.5.0 | HTTP 客户端 |
| github.com/manifoldco/promptui | v0.9.0 | 交互提示 |

> ⚠️ 注意：`atotto/clipboard` 在 Linux 下依赖 X11/cgo，但 **CGO_ENABLED=0 下不影响编译**——
> aiac 仅在用户显式 `--clipboard` 时调用 clipboard 包，且该包有 CGO 关闭时的 fallback 实现（noop），
> 编译期不触发。本地 `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build` 已验证成功。

## 编译环境

- **平台**: HarmonyOS (OHOS) linux/arm64
- **Go版本**: go1.26.5（SDK 自动下载 bootstrap，`GOTOOLCHAIN=local`）
- **CGO_ENABLED=0**: 铁律遵守（Go 项目纯静态编译）
- **GOPROXY**: `https://goproxy.cn,https://proxy.golang.org,direct`
- **编译命令**:
  ```
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  GOPROXY=https://goproxy.cn,direct \
  GOTOOLCHAIN=local \
  go build -trimpath \
    -ldflags "-s -w -X github.com/gofireflyio/aiac/v5/libaiac.Version=v5.3.0" \
    -o aiac .
  ```

## 关键问题与解决方案

### P1: 源码归档下载
- **问题**: GitHub 443 端口从本机直接下载不稳定
- **解决**: conandata.yml 写官方 URL，CI 的 mirror fallback 会自动加 `gh-proxy.com` 前缀
  作为镜像回退；本地分析用 ghfast.top/gh-proxy.com 代理下载，sha256 交叉验证一致。

### P2: Go linker mmap 在 HMDFS 上失败
- **问题**: Go linker 用 mmap 写输出文件，在 HMDFS 上 `mapping output file failed: permission denied`
- **解决**: 链接输出路径放到 ext2 可写分区 `/data/storage/el2/base/haps/entry/files`（有 write 探测回退到 cache），
  与 argo/spicedb 经验一致。

### P3: OHOS ELF 自签名
- **问题**: OHOS 上每个被 fork/exec 的 ELF 必须携带 `.codesign` section，否则执行时 permission denied
- **解决**: 用 `binary-sign-tool sign -selfSign 1 ... -signAlg SHA256withECDSA` 对 aiac 二进制
  及 Go SDK 工具链（bin/go、bin/gofmt、pkg/tool/linux_arm64/*）全部签名。

### P4: 上游无测试 → 补全消费者测试
- **问题**: 上游 5.3.0 无任何 `*_test.go` 文件，CI 只有 goreleaser 发布流，无测试入口
- **解决**: `go test -v -count=1 ./...` 作为机器证据输出 `[no test files]`（HMBS no_tests），
  另在 test_package 提供消费者冒烟测试（test.sh）：`--version` 断言 v5.3.0、`--help` 核心标志、
  无默认后端时 `--list-models` 失败闭合诊断。

## 测试验证

- **aiac --version**: 输出 `aiac version v5.3.0`（正确）
- **aiac --help**: 输出全部子命令与标志（--list-models、--backend 等）
- **aiac --list-models**（无默认后端配置）: 非零退出 + `backend not selected and no default configured` 诊断
- **上游 go test ./...**: 每包 `[no test files]`，0 断言执行（计为 no_tests，不计为通过）

## 编译产物

- aiac (约 11MB, ELF static arm64, stripped)
- 本地验证用 x86_64/amd64 交叉编译的二进制行为一致

**编译开始**: 2026-09-03
**最终状态**: built
