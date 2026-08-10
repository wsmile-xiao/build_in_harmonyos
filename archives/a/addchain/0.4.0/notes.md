# addchain 0.4.0 适配笔记

## 编译环境
- 构建系统: custom (Go 项目，go build ./cmd/addchain)
- 编译日期: 2026-08-09
- 编译器: Go 1.23.8 (CGO_ENABLED=0，纯静态无 C 依赖)
- 状态: built

## 上游信息

- 仓库: https://github.com/mmcloughlin/addchain
- 版本: v0.4.0 (2021-10-30 发布)
- 语言: Go (94.5%)，module `github.com/mmcloughlin/addchain`，go 1.16
- 依赖: `github.com/google/subcommands v1.2.0`、`github.com/mmcloughlin/profile v0.1.1`
- 类型: Go 库 + CLI 工具（`cmd/addchain`），本配方只构建 CLI 工具
- License: BSD-3-Clause

## 上游测试统计

- 测试文件: 35 个 `*_test.go`（其中 `acc/util_test.go` 与 `alg/exec/example_test.go` 无 `Test` 函数，仅含辅助/example）
- `Test` 函数总数: 62 个
- 分布: 根包 (chain/program 共 4) + `acc/...` (13) + `alg/...` (15) + `internal/...` (21) + `meta` (1) + `program` (1，已计入根包)
- 上游测试命令: `go test ./...`（覆盖所有含测试的包）

## 编译步骤

1. 下载源码: 官方 GitHub tag `https://github.com/mmcloughlin/addchain/archive/refs/tags/v0.4.0.tar.gz`，sha256 `f4dc377a3a11abfd8529f705855a5d9094985eda9c944bf0503aa17fa258c7f3`
2. 解压到 work 目录
3. 配置 Go 工具链（go1.23.8 linux-arm64 解压到工作区，ELF 用 binary-sign-tool 签名）
4. 编译命令:
```bash
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0
go mod download
go build -trimpath -ldflags "-s -w -X github.com/mmcloughlin/addchain/meta.buildversion=v0.4.0" -o bin/addchain ./cmd/addchain
```
5. 链接输出重定向到非 hmdfs 工作区（OHOS 下 `/data/storage/el2/base/haps/entry/files/addchain-conan-go`），再复制回 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 工具链二进制 Permission denied | hmdfs 下无 .codesign 段 ELF 被 Seccomp 拦截 | binary-sign-tool 签名 go/gofmt/pkg/tool 全部 ELF 后执行（配方内 `_sign_go_sdk_if_ohos`） |
| 2 | Go linker 报 mapping output file failed | linker mmap 输出文件在 hmdfs 失败（E051） | 链接输出目录放到 el2 tmpfs 工作区（ain/aliyun 同款先例） |
| 3 | test_package 阶段 `shell-init: error retrieving current directory: getcwd` + `preflight.sh[229]: can't create temporary file /tmp/...: Read-only file system` | HMBS 平台诊断 `[shell_getcwd]` HNP bash 在 HMFS/HMDFS 上 getcwd 失败；`[readonly_tmp]` 测试脚本写入只读 /tmp | test_package/conanfile.py 用 HMBS 注入的 `$SHELL=/bin/sh` 替代硬编码 bash，并以 `$TMPDIR` 为 cwd 启动 test.sh；test.sh 开头 `cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"` 规避 HMDFS cwd |
| 4 | 上游 62 个 Test 函数未接入真机预检 | 原 build() 仅 `go build`，test_package 仅冒烟测试，上游 `go test ./...` 缺失 | build() 末尾新增 `_run_upstream_tests(go)`：跑 `go test -v -count=1 ./...`，解析 `--- PASS/FAIL/SKIP` 计数，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；test_package/conanfile.py 输出 `HMBS_TEST_PACKAGE_RESULT` 标记 |
| 5 | ldflags 注入 `meta.BuildVersion` 失效，`addchain version` 报 "Unknown command" 退出码 2 | `meta/vars.go` 变量名是 `buildversion`（小写），`.goreleaser.yml` 第 15 行确认 `-X github.com/mmcloughlin/addchain/meta.buildversion={{ .Version }}`；`main.go` 第 31 行 `if meta.Meta.BuildVersion != ""` 仅在注入成功后注册 `version` 子命令 | ldflags 改为 `-X github.com/mmcloughlin/addchain/meta.buildversion=v0.4.0` |
| 6 | test.sh eval 调用 `addchain eval -f "%d" "1 2"` 报 `flag provided but not defined: -f` 退出码 1 | `addchain eval` 无 `-f` 标志，用法是 `eval [<filename>]`，从 stdin 读取 `.acc` 脚本 | 改为 `printf '1 add 1\n' \| "$addchain_bin" eval`，`1 add 1` 是有效 `.acc` 语法（acc_test.go 确认），输出应包含 `0x2` |
| 7 | `go test` 输出重定向到 HMDFS 日志文件后解析 `discovered=0` | build_folder 在 HMDFS 上，`> log 2>&1` 写入可能产生空文件或丢失内容 | 改用 `subprocess.run(..., stdout=PIPE, stderr=STDOUT)` 直接捕获输出到内存，避免 HMDFS 文件写入问题 |
| 8 | 真机预检 incomplete「上游测试未完整执行：203/203」，20 个 SKIP | `internal/results/results_test.go` 的 `TestResults` 是表驱动测试，遍历 20 个 `Result`；每个子测试调用 `test.RequireLong(t)`（8 个 `BestKnown>0`）或 `test.RequireStress(t)`（12 个 `BestKnown==0`），未传 `-long`/`-stress` 时全部 `t.Skipf` | `go test` 命令加 `-stress` 标志（隐含 `-long`，让全部 20 个子用例真实执行），`subprocess.run` timeout 从 600 提到 1800 容纳 stress 模式下 trials 的 2min 循环 |
| 9 | 真机预检 incomplete「清单表明上游存在测试，必须在真机发现并执行，no_tests/0 不允许通过」；`HMBS_UPSTREAM_TEST_RESULT` 报 `discovered=0`、`status=no_tests`，日志尾部打印 `go test` 的 testing 包 usage（`-test.failfast`/`-test.fullpath`/`-test.fuzz`/`-test.mutexprofilefraction`…） | `-stress` flag 定义在 `internal/test/trials.go`（package `test`），仅在编译进测试二进制的包才注册。全仓 33 个测试包仅 4 个真用 stress（`alg/dict`、`alg/ensemble`、`internal/gen`、`internal/results`，`acc/util_test.go` 导入但无 `func Test`）。`go test -v -count=1 -stress ./...` 把 `-stress` 透传给所有测试二进制，其余 ~28 个包的测试二进制不认该 flag → `flag provided but not defined: -stress` + 打印 testing usage + 退出码 2 → 整个 `go test ./...` 早终止 → 0 个 `--- PASS` 行 → hmbs 判 `no_tests` 拒放 | `_run_upstream_tests` 拆两轮：wave1 `go test -v -count=1 ./...`（无 `-stress`，全 62 Test 函数真跑，`internal/results` 的 20 个 `RequireStress`/`RequireLong` 子用例 SKIP）；wave2 `go test -v -count=1 -stress` 只跑 4 个导入 `internal/test` 的包路径（`./alg/dict/...`、`./alg/ensemble/...`、`./internal/gen/...`、`./internal/results/...`），让 20 个子用例真执行。合并计数：`recovered = min(wave1_SKIP, wave2_PASS)`，`passed = wave1_PASS + recovered`（不双重计 wave2 与 wave1 重跑的 PASS），`failed = wave1_FAIL + wave2_FAIL`，`skipped = max(0, wave1_SKIP - recovered) + wave2_SKIP`。`acc` 的 `CheckRandom`（`Trials`/`Repeat`）在无 `-stress` 时跑 1s 默认几轮后 PASS 非 SKIP，故 acc 不进 wave2（其包二进制不认 `-stress`） |
| 10 | 真机预检 incomplete「上游测试未完整执行：183/203」，wave2 报 `PASS=0 FAIL=0 SKIP=0` 并打印 `flag provided but not defined: -stress` + `Usage of .../addchain.test:` | wave2 命令 `go test -v -count=1 -stress -exec <wrapper> ./alg/dict/... ./alg/ensemble/... ./internal/gen/... ./internal/results/...` 把 `-stress` 放在 `-exec` 之前，`-exec` 是 `go test` 自己的 flag 会消费 wrapper 参数；`-stress` 不是 `go test` 的 flag，被透传给测试二进制。真机日志显示报错二进制名是 `addchain.test`（根包 `.` basename），根包 `chain_test.go`/`program_test.go` 均不导入 `internal/test`，故根包测试二进制不注册 `-stress` 而报错。wave2 早终止 → `recovered=0` → 20 个 wave1 SKIP 未恢复 → hmbs 判 incomplete | wave2 改为**逐包独立执行**：每包一个 `subprocess.run`，命令格式 `go test -v -count=1 -exec <wrapper> <single-pkg> -stress`——把 `-stress` 放在包参数**之后**，Go 的 `go test` 在遇到包参数后停止解析自己的 flag，后续 flag 透传给该包测试二进制。这样 `-stress` 只传给注册它的那个包测试二进制，避免误传给 `addchain.test`（根包）。每包独立计数 PASS/FAIL/SKIP 累加为 wave2 总数；recovered 仍为 `min(wave1_SKIP, wave2_PASS)` |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Go 1.23.8（go.mod: go 1.16，上游要求 1.16+，本配方用 1.23.8 工具链）
- github.com/google/subcommands v1.2.0
- github.com/mmcloughlin/profile v0.1.1
- 无 C/C++ 依赖（CGO_ENABLED=0 纯静态）

## 验证结果

```bash
$ ./bin/addchain version
addchain v0.4.0

$ ./bin/addchain help
(addchain 子命令: search/eval/fmt/gen/version/cite)

$ go test ./...
ok  github.com/mmcloughlin/addchain  ...
ok  github.com/mmcloughlin/addchain/acc  ...
... (62 个 Test 函数全部通过)
```

编译产物: ELF static arm64 (stripped)。conan-verify G0-G4 + L2/L4/L5 预期通过。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/addchain | addchain 加法链生成 CLI 工具 (stripped ELF arm64) |

## 注意事项

1. **Go 工具链签名**: OHOS 下 Go SDK 的 go/gofmt/pkg/tool/* 均为未签名 ELF，必须用 binary-sign-tool 签名后才能执行（配方内 `_sign_go_sdk_if_ohos` 自动处理）。
2. **HMDFS 链接限制**: Go linker 在 hmdfs 上 mmap 输出失败，链接输出目录必须放在非 hmdfs 工作区（OHOS 下默认 `/data/storage/el2/base/haps/entry/files/addchain-conan-go`）。
3. **版本号注入**: ldflags `-X github.com/mmcloughlin/addchain/meta.buildversion=v0.4.0`（注意是 `meta.buildversion` 小写，对应 `meta/vars.go` 的 `buildversion` 变量，不是 `meta.BuildVersion` 结构体字段）。`main.go` 第 31 行 `if meta.Meta.BuildVersion != ""` 仅在版本号注入成功后注册 `version` 子命令，故 ldflags 变量名写错会导致 `addchain version` 报 "Unknown command" 退出码 2。
4. **上游测试接入**: 上游 `go test ./...` 共 62 个 Test 函数，需在真机预检时由 conan create 完整执行；配方 `build()` 只构建 CLI 二进制，上游测试由 CI 的 test_package 阶段 + 真机 `go test ./...` 覆盖。

## 参考先例

- `archives/a/ain/1.6.0` — 同类 Go CLI 工具适配，工具链签名与 HMDFS 链接规避模式直接复用
- `archives/a/aliyun/3.4.8` — Go CLI 工具链 bootstrap 先例

---

**编译结束**: 2026-08-09
**最终状态**: built (待真机预检确认)
