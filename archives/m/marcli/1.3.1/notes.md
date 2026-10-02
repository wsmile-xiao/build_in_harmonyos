# marcli 1.3.1 适配笔记 (HarmonyOS PC / OpenHarmony aarch64)

## 任务类型
积分赛：marcli 1.3.1 向 OpenHarmony / HarmonyOS PC (aarch64) 的 conan 适配与打包。

## 上游实体核验
- 上游：`https://github.com/hectorcorrea/marcli`，tag `v1.3.1`（release 2025-08-10）。
- 版本判定证据：GitHub 上 59 个同名/近名仓库中，实测仅 `hectorcorrea/marcli` 存在版本 1.3.1
  （`git ls-remote --tags` 精确命中 `f4ef6c3d56d5e330cb874707f13c08b72bb7ae55 refs/tags/v1.3.1`）；
  其余同名工程（Oeditus/bartikowskiw/Marlee-Project/marcy-cloud）最高版本均 < 1.3.1，已排除。
- 源码归档（官方 tag 归档）：`https://github.com/hectorcorrea/marcli/archive/refs/tags/v1.3.1.tar.gz`
  - sha256=**944c7c389d384a9515799bb688cb9ced80344709758a42c714f726957785a1c4**，tar 条目 42。
  - 顶层目录 `marcli-1.3.1/`，配方 `source()` 用 `strip_root=True`。
- 模块/入口：`module github.com/hectorcorrea/marcli`，`go 1.14`，主程序在 `cmd/marcli`（`go build ./cmd/marcli`）。
- 版本注入：`-X main.Version=v1.3.1`（上游 `cmd/marcli/compile_all.sh` 同款变量；`cmd/marcli/main.go:20` `var Version = ""`）。

## W0 依赖核验结论
- **零 conan 第三方依赖**：`go.mod` 仅声明 1 个模块 `github.com/google/go-cmp v0.5.9`，
  且该模块**仅被 `pkg/marc/*_test.go` 引用（测试期）**，经 **GOPROXY** 消费，**不是 conan 包**
  （以 conan ref 探测 `go-cmp/0.5.9` → rc=1）。
- 其传递依赖 = 0（go-cmp v0.5.9 的 go.mod 仅 `module` + `go 1.13`，无 require，无 go.sum）。
- 无 CGO / 无系统 C 库依赖（`CGO_ENABLED=0`）；构建期唯一外部需求是 **Go 工具链**，
  按本仓 Go 先例由配方 `_ensure_go_toolchain()` 自举下载 + 自签名，**不立 conan 包**。

## 构建与 OHOS 平台适配要点
1. **Go 工具链自签名 + 权限位**：`binary-sign-tool sign` 后文件**丢失执行位**，直接构建报
   `fork/exec .../pkg/tool/linux_arm64/compile: permission denied`。配方在签名后统一 `chmod 755`
   （`_ensure_executable()`）。
2. **链接输出落 ext2 工作区**：OHOS/HMDFS 下 Go link 的 mmap 写输出会
   `mapping output file failed: permission denied`，配方把 `-o` 指向
   `/data/storage/el2/base/haps/entry/files/marcli-1.3.1-go/link-out/`，构建后再拷回 build folder。
3. **上游测试执行方式**：OHOS 上自签名进程**不能 execve 另一 ELF**，故 `go test` 不可用。
   配方逐包 `go test -c` 编译测试二进制 → 自签名 → **从各包自身目录直接运行**
   （相对 testdata 才能解析），多线程并行。
4. **GOPROXY（worker 网络）**：本机 Go 的纯 Go resolver 直连 `114.114.114.114` / `8.8.8.8` 超时
   （系统解析器/curl 正常），默认 `https://goproxy.cn,direct` 会失败。配方允许通过
   `OHC_GOPROXY` / `GOPROXY` 环境变量覆盖，本地测试用 `file://` 本地 proxy 兜底。

## 上游测试入口与实测统计（独立口径）
- 上游入口：`go test ./...`（Go modules 原生；无 Makefile/ctest/pytest 注册清单）。
- 上游测试资产：5 个 `*_test.go`，全部位于 `pkg/marc/`：
  `field_test.go`、`filters_test.go`、`leader_test.go`、`marcfile_test.go`、`record_test.go`。
- 实测（OHOS：逐包 `go test -c` → 自签名 → 直接运行）：**55/55 通过（25 顶层 Test* + 30 子测试），
  0 失败 0 跳过**；每项用例清单见 `reports/upstream-test-cases.txt`，完整日志见构建日志
  `upstream_test_full.log`。

## 源码修改
无（`patches_applied: []`，`conandata.yml` 的 patches 映射为空）。

## 交付物
| 文件 | 说明 |
|---|---|
| `conanfile.py` | Go 配方（工具链自举 + ext2 link-out + ELF 自签名 + 上游测试） |
| `conandata.yml` | 官方源 + sha256 |
| `test_package/` | 消费者测试（5 用例，含 1 条鸿蒙特有 `.codesign`） |
| `commands.json`（软件级） | CLI 声明（R38），type=tool |

## 注意事项
- 本库为零依赖纯 Go 目标，无任何 conan 依赖缺口，可直接适配。
- OHOS 上执行任何新构建的 ELF 前，必须确保已 `binary-sign-tool` 签名且执行位为 755。
---

**编译结束**: 2026-09-30 12:31
**最终状态**: built
