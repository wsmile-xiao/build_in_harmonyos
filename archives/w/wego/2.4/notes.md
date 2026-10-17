# wego 2.4 适配笔记

## 编译环境
- 构建系统: custom (Go modules)
- 编译日期: 2026-08-04
- 编译器: Go 1.26.5 (linux/arm64, via goenv) / 1.24.0 SDK bootstrap fallback
- 状态: built

## 任务平台元数据纠偏

> ⚠️ 任务平台显示 wego 的语言为 **C++**，这是平台元数据错误。上游真实语言是 **Go**，
> 构建系统是 **Go modules**（`go.mod`/`go.sum`），不是 CMake/Autotools/Make。
> 本归档按 Go modules 真实情况编写配方，不沿用任何 C/C++ 案例的构建逻辑。

## 上游真实技术事实

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/schachmat/wego |
| 上游 tag | 2.4 |
| 源码 URL | https://github.com/schachmat/wego/archive/refs/tags/2.4.tar.gz |
| 源码 SHA256 | `5ae1c76a322ff2e295034a801755c42b0cb6bdef5ab205af42cf95dbf7c570f4` |
| 上游语言 | Go (纯 Go，无 `import "C"`，无 cgo 指令) |
| 构建系统 | Go modules (`go.mod`/`go.sum`) |
| 命令入口 | 根包 `github.com/schachmat/wego` (main.go 在仓库根，**不是** `./cmd/wego`) |
| `*_test.go` 数量 | **0** |
| `TestXxx` 数量 | **0** |
| `BenchmarkXxx` 数量 | **0** |
| `ExampleXxx` 数量 | **0** |
| CI `go test` 命令 | `.github/workflows/go-build-test.yml: go test -v ./...` |
| `go test -v ./...` 退出码 | 0（4 个包全部输出 `[no test files]`） |
| **上游真实测试统计** | **0**（`[no test files]` 不计为测试通过） |
| CGO 依赖 | 无（CGO_ENABLED=0 静态编译可行） |
| license | ISC |

## 直接依赖（go.mod）

| 模块 | 版本 | 类型 |
|---|---|---|
| github.com/mattn/go-colorable | v0.1.14 | direct |
| github.com/mattn/go-runewidth | v0.0.23 | direct |
| github.com/muesli/mango | v0.2.0 | direct |
| github.com/muesli/roff | v0.1.0 | direct |
| github.com/schachmat/ingo | v0.0.0-20170403011506-a4bdc0729a3f | direct |
| github.com/clipperhouse/uax29/v2 | v2.2.0 | indirect |
| github.com/mattn/go-isatty | v0.0.20 | indirect |
| golang.org/x/sys | v0.29.0 | indirect |

## 编译步骤

wego 是纯 Go CLI 工具（weather client for the terminal），不需要 configure/make/cmake 流程，直接使用 `go build` 编译：

```bash
# 1. 确保已签名的 Go 工具链可用（goenv 1.26.5 或自动 bootstrap 的 1.24.0 SDK）
# 2. 解压源码到工作目录
# 3. 配置 Go 环境（HMFS tmpfs workspace 必需，否则 Go linker mmap 报 permission denied）
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64
export GOPROXY=https://goproxy.cn,direct
export GOSUMDB=sum.golang.google.cn
export GOROOT=<实际选中的 Go 工具链根>
export TMPDIR=/data/storage/el2/base/haps/entry/files/wego-2.4-build/tmp
export GOTMPDIR=$TMPDIR
export GOCACHE=/data/storage/el2/base/haps/entry/files/wego-2.4-build/go-build-cache

cd wego-2.4
go mod download
go build -trimpath -ldflags="-s -w" -o wego .

# 4. 对生成的 wego ELF 执行签名（OHOS 平台要求）
#    python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf wego
#    或用 ohc/sign_elf.py.sign_single(Path("wego"))

# 5. 验证
./wego -h   # exit 0，输出完整 help（含 backend/frontend 列表）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go: command not found` 或 exit 126 Permission denied | Go 工具链二进制未 ELF 签名（OHOS 平台要求） | 用 `ohc/sign_elf.py.sign_single` 签名 Go 工具链全部 ELF（bin/go、bin/gofmt、pkg/tool/linux_arm64/{asm,cgo,compile,cover,fix,link,preprofile,vet}） |
| 2 | Go linker `mapping output file failed: permission denied` | 鸿蒙 /tmp 只读，Go linker 用 mmap 写输出需要可写 tmpfs | 将 TMPDIR/GOTMPDIR/GOCACHE/GOMODCACHE 设置到 HMFS（`/data/storage/el2/base/haps/entry/files/`） |
| 3 | 任务平台显示语言为 C++ | 平台元数据错误 | 按 Go modules 真实情况编写 conanfile.py，不沿用 C/C++ 模板逻辑；在 notes/报告/MANIFEST 中明确记录此纠偏 |
| 4 | 上游无测试文件但 CI 跑 `go test -v ./...` | 上游 2.4 真实无 `*_test.go` | 上游真实测试统计为 0；`[no test files]` 不计为测试通过；test_package 用消费者 smoke test（`wego -h` + 关键词断言）补全 |

## 源码修改

无补丁，无源码修改。wego 2.4 在本平台（linux/arm64，CGO_ENABLED=0）直接编译通过。

## 验证结果

```bash
$ ./wego -h
Usage of wego:
  -aat-compact        aat-frontend: Compact output
  -b BACKEND          BACKEND to be used (shorthand) (default "openweathermap")
  -backend BACKEND    BACKEND to be used (default "openweathermap")
  -d NUMBER           NUMBER of days of weather forecast (shorthand) (default 3)
  -f FRONTEND         FRONTEND to be used (shorthand) (default "ascii-art-table")
  -frontend FRONTEND  FRONTEND to be used (default "ascii-art-table")
  ...
Available backends: caiyunapp.com, json, openmeteo, openweathermap, smhi, weatherapi, worldweatheronline
Available frontends: ascii-art-table, emoji, json, markdown
$ echo $?
0
```

`wego -h` 退出码 0，输出包含全部 backend/frontend 关键词。

## test_package 消费测试

| 项 | 值 |
|---|---|
| 测试脚本 | `test.sh` |
| 命令 | `bash test.sh <bin/wego>` |
| 断言总数 | 6 |
| 断言内容 | (1) `wego -h` exit 0；(2-5) stdout 含 `openweathermap`/`weatherapi`/`ascii-art-table`/`markdown`；(6) 含 `Available backends:` |

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Go modules Conan 配方（CGO_ENABLED=0，非 PIE 静态构建） |
| `conandata.yml` | 源码 URL + SHA256 |
| `manifest.yaml` | 构建元数据（build_system=go） |
| `test_package/conanfile.py` | 消费者测试（运行 wego -h） |
| `test_package/test.sh` | smoke test 脚本（6 断言） |
| `test_package/MANIFEST.yml` | 测试声明（assertion_count=6） |
| `reports/test-report.md` | 测试报告 |

## 注意事项

- wego 命令入口是根包 main.go，**不是** `./cmd/wego`（与 chkbit/dbmate 等 Go CLI 不同）。
- 不要使用 `-buildmode=pie`（与 OHOS ELF 签名冲突，签名后 segfault）。
- Go 工具链二进制本身在 OHOS 上必须先签名才能执行（exit 126 Permission denied 是未签名的标志）。
- 任务平台语言元数据（C++）错误，真实语言是 Go；本归档已纠偏。

---
**编译结束**: 2026-08-04
**最终状态**: built
---

**编译结束**: 2026-08-04 13:26
**最终状态**: built
