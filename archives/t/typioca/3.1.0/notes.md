# typioca 3.1.0 适配笔记

## 项目信息

- **软件**: typioca (纯 Go CLI，bubbletea TUI)
- **版本**: 3.1.0
- **模块**: `github.com/bloznelis/typioca` (go.mod 声明 `go 1.22.1`)
- **构建系统**: Go (Makefile `make build` 的等价命令)
- **目标平台**: HarmonyOS PC (aarch64, 静态 musl/ohos libc)

## 编译环境

- **Go**: go1.26.5 linux/arm64（设备自带 `/storage/Users/currentUser/sdk/go1.26.5`，已签名）
- **GOOS**: linux
- **GOARCH**: arm64
- **CGO_ENABLED**: 0（静态编译）
- **GOTOOLCHAIN**: local
- **工作目录**: `/data/storage/el2/base/haps/entry/files`（ext2 可写，规避 HMDFS fallocate 限制）

## 编译命令

```bash
export GOROOT=/storage/Users/currentUser/sdk/go1.26.5
export PATH=$GOROOT/bin:$PATH
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local
export GOPROXY=<https://goproxy.cn | file:///.../typioca-goproxy>
export GOSUMDB=off
export GOMODCACHE=$W/typioca-gomodcache GOCACHE=$W/typioca-gocache
export TMPDIR=$W/typioca-tmp GOTMPDIR=$W/typioca-tmp
cd typioca-3.1.0.work
go build -trimpath -ldflags "-s -w -X github.com/bloznelis/typioca/cmd.Version=3.1.0" -o $W/typioca-build/typioca .
```

等价于上游 `Makefile` 的 `make build`（去掉 `-a` 全量重编译）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go build` 报 `dial tcp: lookup goproxy.cn on 8.8.8.8:53: i/o timeout` | Go 的 netgo 解析器只读 `/etc/resolv.conf`（本机 114.114.114.114 / 8.8.8.8 均不可达）；`GODEBUG=netdns=cgo` 对静态 netgo 构建无效 | 用系统解析（Python/curl，可解析）预取全部 go.sum 模块到本地 `file://` 模块代理，`GOPROXY` 用环境变量覆盖指向该代理；CI 环境保留公共代理默认值 |
| 2 | `link: mapping output file failed: permission denied` | Go 链接器对输出文件调用 `fallocate()`，HMDFS/tmpfs 返回 `EACCES`（知识 E523/E134） | 链接输出放到 ext2 可写分区 `/data/storage/el2/base/haps/entry/files`（`_go_workspace()/link-out`），完成后再复制回 build_folder |
| 3 | 构建产物 `fork/exec ...: permission denied` | OHOS 上未签名的 ELF 不可执行 | 构建后用 `binary-sign-tool sign -selfSign 1 ... SHA256withECDSA` 自签名（含 `.codesign` section） |
| 4 | 版本号输出为 `dev` | 上游 Makefile 用 `git describe --abbrev=0 --tags` 取版本，tarball 无 .git | 配方 ldflags 显式注入 `-X github.com/bloznelis/typioca/cmd.Version=3.1.0` |
| 5 | `go mod download` 首次报 DNS 失败 | Go 工具链在网络获取模块时使用 netgo 解析器 | 同 #1，模块经 `file://` 代理预取后再 `go mod download` |

## 源码修改

无源码补丁。typioca 3.1.0 在 OHOS 上属于**纯构建级适配**（交叉编译 + HMDFS 链接规避 + ELF 签名），不涉及源码平台分支（R8/R40：无 UI/多媒体/系统底层深度适配需求）。

## 依赖版本

- **编译依赖**: Go 1.26.5 SDK（tool_requires 语义，配方内 bootstrap）
- **Go 模块依赖**: 52 个模块（charmbracelet/bubbletea v1.1.1、lipgloss v0.13.0、cobra v1.8.1 等），全部来自 goproxy.cn，go.sum 校验
- **运行依赖**: 无

## 验证结果

```bash
$ typioca --version
typioca  3.1.0
$ typioca --help          # 列出 serve/completion/help
$ typioca serve --help    # 列出 -k/-b/-p
$ typioca definitely-not-a-command ; echo $?
1
$ file typioca
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
```

## 上游测试

- typioca 3.1.0 **无任何自动化测试**：`find . -name '*_test.go'` 为空；Makefile 无 test/check 目标；`.github/workflows/ci.yml` 只有 `make build-all`。
- 执行 `go test -v -count=1 ./...` 作为机器证据：每个包输出 `[no test files]`，PASS=0 FAIL=0 SKIP=0 → `HMBS_UPSTREAM_TEST_RESULT=no_tests`。
- 补充消费者冒烟测试（test_package）：`typioca --version/--help/serve --help`、未知命令非零退出，共 6 条；另加 1 条**鸿蒙特有**断言（产物 ELF 含 `.codesign` 签名段）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/typioca` | 静态链接的 aarch64 ELF（已签名） |
| `licenses/LICENSE` | MIT 许可证 |
| `res/README.md` | 上游 README |

## 注意事项

1. Go 模块必须在可解析域名的方式下获取（file:// 代理或可用 DNS）；Go 内置解析器在本机不可用
2. 链接必须发生在非 HMDFS 分区，否则 fallocate EACCES
3. 产物必须签名，否则 OHOS 拒绝执行
---

**编译结束**: 2026-10-12 16:39
**最终状态**: built
