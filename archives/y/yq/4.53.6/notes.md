# yq 4.53.6 适配笔记

## 基本信息
- **软件**: yq（mikefarah/yq — 轻量便携的命令行 YAML/JSON/XML/CSV/TOML/properties 处理器，jq 的 YAML 对应物）
- **版本**: 4.53.6（上游 tag `v4.53.6`）
- **许可**: MIT（`LICENSE` 为 "The MIT License (MIT) / Copyright (c) 2017 Mike Farah"）
- **上游源码**: https://github.com/mikefarah/yq/archive/refs/tags/v4.53.6.tar.gz
- **tarball 校验**: `sha256 = 132a28a669526f99dba52486ac80de3bdafdf9a1a52a0c6bd6045301aca0cd25`，
  `tar tzf | wc -l = 565`（顶层目录 `yq-4.53.6/`，375145 字节）
- **交付物**: `bin/yq`（aarch64 ELF，静态链接，`-trimpath -s -w`，带 `.codesign` 段）

## 上游构建方式
- main 包在**仓库根目录**（`yq.go`，`package main`），`cmd/` 是 cobra 命令实现。
- 上游 Makefile：`go build --ldflags "$(LDFLAGS)"`，`Makefile.variables` 里
  `LDFLAGS += -X main.GitCommit=... / -X main.GitDescribe=...`。
  ⚠ **这两个变量实际定义在 `package cmd`（`cmd/version.go`），`-X main.*` 指向不存在的
  符号、对版本显示毫无影响**；`yq --version` 的版本串始终来自源码常量
  `cmd/version.go: Version = "v4.53.6"`。
- 本配方等价命令（主包为根目录，故 `-o <out> .`）：
  ```
  go build -trimpath -ldflags "-s -w" -o <ext2>/out/yq .
  ```
  不需要任何 `-X`：交付版本正确性由消费者用例 C1 断言
  （stdout 恰为 `yq (https://github.com/mikefarah/yq/) version v4.53.6`）。

## OHOS 平台要点（沿用本仓 kubergrunt 0.19.0 / dbmate 2.33.0 / tlsx 1.2.2 / aliae 1.5.0 已验证做法）
| 编号 | 现象 | 本配方处置 |
|------|------|-----------|
| E166 | Go 链接器在 HMDFS 上 mmap 写输出失败 | `GOCACHE/GOMODCACHE/GOPATH/GOTMPDIR/TMPDIR` 与 `-o` 输出全部落到 ext2（`/data/storage/el2/base/cache`，回退 `/data/storage/el2/base/haps/entry/files`，做真实写探针） |
| E128 | 会被 execve 的 ELF 必须带 `.codesign` 段 | 自举的 Go 工具链（`bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*`）与交付二进制都用 `/data/service/hnp/bin/binary-sign-tool` 自签名（先 `llvm-objcopy --remove-section .codesign`） |
| E077 | HMDFS 的 chmod 语义（group 固定 6 / other 固定 0 / owner 保底 rw-） | 签名/解包后统一 `chmod 0o755` 恢复 owner 的 x 位 |
| E046 | HMDFS 不支持 getcwd，而 `go` 要从 cwd 向上找 `go.mod` | 源码整树先复制到 ext2（`<work>/src`）再 `go mod download` / `go build` / `go test` |

### yq 特有的一条：构建树必须可写
`pkg/yqlib` 的部分用例（`recipes_test.go` / `format_test.go` 等）会**回写源码树里的
`doc/*.md`**。OHOS 上把源码复制到 ext2 副本恰好同时满足两个需求：可写 + 可 getcwd
（也避免了污染 conan 的 source 缓存）。

### go test 的 E128 特殊处理
`go test` 内部生成的测试二进制（`$GOTMPDIR/go-build*/b001/*.test`）配方无法预先签名，
不签名则 execve 直接 `EACCES`（`fork/exec ...: permission denied`）。处置与本仓
kubergrunt / aliae 一致：`go test -exec=<wrapper>`，wrapper 在 exec 前就地签名。

## 上游测试（`go test`）统计与口径
- 命令：`go test -count=1 -json -timeout 300s ./...`（OHOS 上追加 `-exec=<sign wrapper>`）。
- **口径（三层，从宽到窄都写明，避免少报）**：
  1. 源码里 `^func Test*` 共 **363 处** = 361 个真实 Test 函数 + 2 个 `TestMain`（测试钩子，非用例）；
  2. 默认 `go test ./...` **实际调度 361 个顶层用例**（360 pass / 1 fail）+ **135 个子测试**
     = **496 个用例事件**；
  3. 硬门禁 = 上游 3 个正式测试包（根包 8 + `cmd` 58 + `pkg/yqlib` 294 = **360 个顶层用例**）。
- **不计入门禁的两处（日志里如实打印）**：
  | 项 | 原因 |
  |----|------|
  | `test/TestFormatStringFromFilename` | **上游自带失效用例**：断言未知扩展名 → `"unknown"`，而实现 `pkg/yqlib/format.go:125` 明确回退 `"yaml"`（代码注释 "extension ... not a recognised format, defaulting to yaml"）。上游自己的 `scripts/test.sh` 就是 `go list ./... \| grep -v -E 'examples' \| grep -v -E 'test'`，**把整个 test 包排除在测试集之外** |
  | 根包 `TestGoInstallCompatibility` | `//go:build goinstall` 标记，需要 `go install` + 网络，默认 `./...` 不调度；上游也是单独 `go test -tags goinstall -run TestGoInstallCompatibility .` |
- **离线确定性**：yq 的上游用例**全部**不依赖外部资源——纯内存数据结构、字符串处理与表驱动黄金
  YAML/JSON（`formatting_expressions_test.go`、`operators_test.go`、`yaml_test.go`、`json_test.go`、
  `xml_test.go`、`csv_test.go`、`toml_test.go`、`ini_test.go`、`hcl_test.go`、`lua_test.go`、
  `base64_test.go`、`recipes_test.go` 等），无网络请求、无凭据、无外部进程
  （已核对：`*_test.go` 中无 `net/http`、无 `exec.Command`；`decoder_uri_test.go` 只是
  percent-decoding，不是网络解码器）。因此门禁口径可以按"包"设闸而不是挑子集：
  **这些包内不得有任何失败，通过数合计不得低于 350**（容忍上游平台条件性 `t.Skip`，例如
  `operator_system_test.go` 在找不到外部命令时 skip、`utils_test.go` 在文件描述符不可观测时 skip；
  全过时为 360）。

### Linux/x86_64 预检实测（go1.26.3 linux-amd64）
| 包 | pass | fail | skip | 子测试 |
|----|------|------|------|--------|
| `(root)`（main 包） | 8 | 0 | 0 | 0 |
| `cmd` | 58 | 0 | 0 | 80 |
| `pkg/yqlib` | 294 | 0 | 0 | 55 |
| `test` | 0 | 1 | 0 | 0 |
| **合计** | **360** | **1** | **0** | **135** |

- 用例事件总计 **496**，通过 **495**（99.8%）；唯一失败为上述上游失效用例。
- 门禁三包 **360/360 = 100%**、0 失败 → `offline deterministic gating set: 3 packages,
  360 upstream cases expected, passed=360 skipped=0 failed=0 missing_pkgs=0 (floor=350)`。
- ⚠ 上述数字来自 Linux/x86_64 预检（本机无 OHOS SDK/工具链）；OHOS 侧真实数字以 CI 日志中
  `===== upstream \`go test ./...\` summary =====` 段为准。

## 消费者用例（test_package/consumer_check.py，9 个用例 / 35 项检查）
真跑交付出来的 `bin/yq`（不是 echo 型假测试），期望值全部是外部可核对真值：
| 用例 | 命令 | 断言 |
|------|------|------|
| C1 | `yq --version` | exit 0，stdout 恰为 `yq (https://github.com/mikefarah/yq/) version v4.53.6\n`（验证 tarball 版本 = 交付版本） |
| C2 | `yq --help` | exit 0，stdout 含 `yq is a portable command-line data file processor`、`Usage:`、`eval` |
| C3 | `yq -n '1+1'` | exit 0，stdout 恰为 `2\n` |
| C4 | `yq -n '[1,2,3] \| map(. * 2)'` | exit 0，stdout 恰为 `- 2\n- 4\n- 6\n` |
| C5 | stdin YAML → `yq -o=json -I=0` | exit 0，stdout 恰为 `{"a":1,"b":["x","y"]}\n` |
| C6 | stdin JSON → `yq -p=json` | exit 0，stdout 恰为 `a: 1\nb:\n  c: true\n` |
| C7 | `yq -n '"hello" \| upcase'` | exit 0，stdout 恰为 `HELLO\n` |
| C8 | `yq -n 'invalid syntax ('` | exit 1，stdout 为空，stderr 含 `Error: 1:1: lexer: invalid input text` |
| C9 | `yq '.a' <不存在的文件>` | exit 1，stdout 为空，stderr 同时含文件名与 `no such file or directory` |

## 交付形态自检（M1–M13，纯 Python 读字节判定，不依赖目标机的 readelf/nm/file）
M1 `bin/yq` 是常规文件 / M2 体积在 5MiB–300MiB / M3 owner 有可执行位 / M4 ELF 魔数 /
M5 ELF64 + 小端 + `e_machine=0xB7`(AArch64) / M6 程序头**无 `PT_INTERP`**（静态链接）/
M7 含 `.codesign` 段（OHOS）/ M8 `bin/` 目录恰为 `['yq']` / M9 `licenses/LICENSE` 是上游
MIT 正文（含 "The MIT License" 与 "Mike Farah"）/ M10 包内无 `*.go`/`go.mod`/`go.sum`/`*.test` /
M11 无隐藏文件、无 `__pycache__`/`go-build` 缓存目录（JC5）/ M12 无 `*.o`/`*.a`/`*.c`/`*.s`/`*.h` /
M13 二进制内不含构建工作目录名（`conan-go-build`/`.go-work`）⇒ 证明 `-trimpath` 生效。

## 本地验证记录（2026-10-01，Linux/x86_64）
1. tarball 双校验：`sha256sum` 与 `tar tzf | wc -l`（565）均与 conandata.yml 一致。
2. Go 工具链镜像校验：`go1.26.3.linux-arm64.tar.gz` = `9d89a3ea…36565`（63741242 字节、16688 条目）、
   `go1.26.3.linux-amd64.tar.gz` = `2b2cfc71…eb556`，与 conandata.yml 逐位一致。
3. 用本机 go1.26.3 复现上游构建命令与全量 `go test ./...`（结果见上表）；模块缓存 113 MB、
   GOCACHE 357 MB、全量测试 **25 秒**跑完（比 kubergrunt 轻得多）。
4. `consumer_check.py` 用同一份源码产出的二进制（`--expect-machine x86_64`）预跑：
   **34 passed / 0 failed / 1 skipped**（C1–C9 全过、M1–M13 全过，M7 在 x86_64 上按参数跳过）。
5. **端到端 `conan create`（`-s os=Linux -s arch=x86_64`）退出码 0**，全流程真实执行：
   下载并解压 go1.26.3（sha256 校验）→ `go mod download` → `go build -trimpath` →
   全量 `go test -count=1 -json -timeout 300s ./...` → `package()` → `conan test` 消费者用例。
   日志关键行：
   - `packages touched: 4 ; top-level Test funcs scheduled: 361 (pass=360 fail=1 skip=0) ; subtests recorded: 135 ; total cases: 496`
   - `offline deterministic gating set: 3 packages, 360 upstream cases expected, passed=360 skipped=0 failed=0 missing_pkgs=0 (floor=350)`
   - `[summary] consumer checks: 34 passed, 0 failed, 1 skipped`
6. 未验证项：OHOS 侧的 ext2 路径可用性、`binary-sign-tool` 签名三条链路（工具链 ELF、交付
   二进制、`go test -exec` 的测试二进制）、aarch64 的 `e_machine=0xB7` 与 `.codesign` 段——
   本机没有 OHOS SDK/工具链，只能在 CI 真机上验证（同 kubergrunt 0.19.0 已验证通过的路线）。
