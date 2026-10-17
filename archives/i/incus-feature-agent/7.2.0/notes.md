# incus-feature-agent 7.2.0 适配笔记

## 编译环境
- 构建系统: custom（Go toolchain / `go build`）
- 编译日期: 2026-10-10
- 编译器: Go 1.25.10（`CGO_ENABLED=0`，无 C 编译器参与）
- 状态: built

## 编译步骤

上游目标（Makefile:52）：`CGO_ENABLED=0 go install -v -tags agent,netgo ./cmd/incus-agent`

本适配采用等价命令：

```bash
export GOROOT=<自举的 go1.25.10>  GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local
export GOFLAGS=-mod=mod GOPROXY=<go module proxy>
go build -toolexec <e523-wrapper> -trimpath -tags agent,netgo \
    -ldflags "-s -w" -o bin/incus-agent ./cmd/incus-agent
# 之后对产物做 OHOS 自签名（binary-sign-tool sign -selfSign 1）
```

- 源码：官方 GitHub tarball `v7.2.0.tar.gz`（5309904 B，
  sha256 `03c48d5fbd097c5e4ae16e96efa768a5f147b86adada7a824f15af017b075bf0`）。
- 全程只修改环境与构建参数（toolexec/签名），**未修改任何源码**，无补丁。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 自举的 Go SDK 无法执行（`permission denied`） | OHOS 内核拒绝执行未签名 ELF（E318） | 对 `bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*` 逐个 `binary-sign-tool sign -selfSign 1` 自签 |
| 2 | Go 链接器失败 `mapping output file failed` | HMDFS 上 `fallocate()=EACCES`，链接器不忽略该错误（E523） | `-toolexec` 包装器把链接器 `-o` 输出重定向到 `/dev/shm`，链接完再拷回 |
| 3 | `go test` 产出的测试二进制无法执行 | 链接后 go 会重写文件，签名须在最终拷贝之后（E318） | `go test -c` → 签名 → 直接执行 `./x.test -test.v` |
| 4 | Go 无法解析 DNS（`lookup ... i/o timeout`） | 本环境 Go pure resolver 使用 IPv4 DNS（不可达），公网经 IPv6；libc/netd 可解析 | 构建期使用可达的 module proxy（GOPROXY 环境变量覆盖；配方默认 `goproxy.cn`） |

## 源码修改

无（无补丁；OHOS 适配完全在环境变量 + toolexec + ELF 签名层面完成）。

## 依赖版本

- 上游 go.mod: `go 1.25.10`；直接 require 72 + indirect 107（全部纯 Go module）。
- 无第三方 C/C++ 库依赖（N=0，详见 `.dep2/reports/incus-feature-agent-7.2.0.md`）。
- Go 工具链 1.25.10 由配方自举（非 conan 依赖）。

## 验证结果

```bash
$ bin/incus-agent --version
7.2
$ bin/incus-agent --help
Description:
  Incus virtual machine agent
Usage:
  incus-agent [--debug] [flags]
# 产物：ELF64 AArch64，libraries static，含 .codesign 段
```

## 上游测试结果（R51）

上游入口：`go test ./...`（Makefile `unit-test`/`check`；`.github/workflows/tests.yml`）。
OHOS 适配环境（CGO_ENABLED=0）下**全仓 53 个含 *_test.go 的包全量尝试，不漏测**：

- **29 个纯 Go 包实际运行**：合计 450 PASS（当时 3 FAIL）。
- **21 个服务端 cgo 包 BUILD_FAIL**：`CGO_ENABLED=0` 下 cgo 源被排除
  （如 `internal/server/db/query` 的 `sqlite3.ErrLocked`、`internal/server/storage/quota`
  build constraints exclude 等），OHOS 不可构建，如实申报。
- **3 个包 SIGN_FAIL**：`internal/server/db`、`internal/server/seccomp`、`internal/server/sys`
  仅含 `//go:build linux && cgo && !agent` 的测试文件，`CGO_ENABLED=0` 下 `no test files`。
- 失败用例 3 例（均为环境限制，非适配缺陷）：
  - `internal/server/instance/drivers/qmp`：`TestConnectDisconnect`、`TestEvents`
    —— 测试在 `$TMPDIR` 创建 unix socket，HMDFS 上 `bind: operation not permitted`
    （`/dev/shm` 上 `mkdir: permission denied`）；该包不在 cmd/incus-agent 闭包内。
  - `shared/subprocess`：`TestSignalHandling` 首轮偶发失败，复跑 3/3 通过（非稳定复现）。

cmd/incus-agent **依赖闭包内 14 个纯 Go 包全部 PASS（228 用例）**，已集成进配方
`build()`（`HMBS_UPSTREAM_TEST_RESULT` 结构化输出）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/incus-agent | ~25 MB | 静态 aarch64 ELF（已 OHOS 签名） |

## 注意事项

- 产物为纯静态二进制，无需 RPATH/动态库；仅需 OHOS ELF 签名。
- 服务端组件（incusd/incus-user/fuidshift 等）需 cgo + liblxc，不在本库范围。
- 同源先例：`archives/i/incus/7.1.0`、`archives/i/incus-user/7.0.1`。
---

**编译结束**: 2026-10-10 19:44
**最终状态**: built
