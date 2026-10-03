# parlay v0.11.0 — 编译适配笔记

## 软件简介

parlay（Enrich SBOMs with data from third party services）—— Snyk 开源的纯 Go 命令行工具，
输入 CycloneDX/SPDX SBOM，从 ecosyste.ms、Snyk、OpenSSF Scorecard 等外部服务补全包元数据后输出更丰富的 SBOM。
源码: https://github.com/snyk/parlay

## 上游真实技术事实

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/snyk/parlay |
| 上游 tag | v0.11.0（commit 116cb0e2126c3603ab2da7ae8e1421687e211c17） |
| 源码 URL | https://github.com/snyk/parlay/archive/refs/tags/v0.11.0.tar.gz |
| 源码 SHA256 | `c1f9eaa073b6c958a0722b145fcea9fa3579c9b5552f3359d86f91917441253b`（与 Homebrew Formula/p/parlay.rb v0.11.0 一致，本地下载实测一致） |
| 上游语言 | Go（纯 Go，无 `import "C"`，CGO_ENABLED=0） |
| 构建系统 | Go modules（`go.mod`/`go.sum`），`module github.com/snyk/parlay`，`go 1.23` |
| 命令入口 | 根包（main.go 在仓库根，`go build .`，非 ./cmd 子目录） |
| 版本注入 | goreleaser ldflags 三处：`internal/commands.version`、`lib/ecosystems.Version`、`lib/snyk.Version` |
| `*_test.go` 数量 | **13** |
| `TestXxx` 函数数量 | **72**（`grep -rhoE '^func (Test[A-Za-z0-9_]+)' --include='*_test.go' . \| wc -l`，tag 根实测） |
| 上游测试入口 | `Makefile: test: lint` + `go test -cover -v ./...`；`acceptance: build` + `bats -r .`（6 个 bats 用例，需 live 网络 + bats，不属于 `go test` 口径） |
| CGO 依赖 | 无 |
| license | Apache-2.0 |

### 上游测试文件清单（13 文件 / 72 函数）

| 文件 | Test 函数数 |
|---|---|
| internal/utils/cdx_test.go | 1 |
| internal/utils/input_test.go | 4 |
| internal/utils/spdx_test.go | 6 |
| lib/ecosystems/cache_test.go | 10 |
| lib/ecosystems/enrich_cyclonedx_test.go | 16 |
| lib/ecosystems/enrich_spdx_test.go | 3 |
| lib/ecosystems/package_test.go | 5 |
| lib/ecosystems/repo_test.go | 2 |
| lib/sbom/decode_test.go | 5 |
| lib/scorecard/enrich_test.go | 5 |
| lib/snyk/enrich_test.go | 9 |
| lib/snyk/package_test.go | 3 |
| lib/snyk/self_test.go | 3 |
| **合计** | **72** |

> 说明：enrich_cyclonedx_test.go 含若干子测试（t.Run），上游口径按顶层 `func TestXxx` 计数 72；
> `go test -v` 仅列首（column-0，无缩进）的 `--- PASS:` 行与该口径一一对应（子测试行为缩进 `    --- PASS: Parent/child`，不计数），conanfile 按此解析，不做减法推导。
> acceptance.bats 6 用例（5 个需访问 ecosyste.ms live API + 1 个负例）需 bats 运行器与外网，
> 不计入 `go test` 总数，在 MANIFEST 审计中如实声明。

## 直接依赖（go.mod）

核心依赖：CycloneDX/cyclonedx-go、spdx/tools-golang、spf13/cobra+viper、packageurl-go、
hashicorp/go-retryablehttp、rs/zerolog、stretchr/testify 等（详见 go.mod）。
全部为 Go 模块依赖，由 `go mod download` 经 GOPROXY（goproxy.cn 优先）获取，无系统库依赖。

## 编译环境

- **平台**: HarmonyOS (OHOS) linux/arm64
- **Go 版本**: go1.24.0（SDK 自动下载 bootstrap，`GOTOOLCHAIN=local`，满足 go.mod `go 1.23`）
- **CGO_ENABLED=0**：纯静态编译
- **GOPROXY**: `https://goproxy.cn,https://proxy.golang.org,direct`
- **编译命令**:
  ```
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  GOPROXY=https://goproxy.cn,direct GOTOOLCHAIN=local \
  go build -trimpath \
    -ldflags "-s -w -X github.com/snyk/parlay/internal/commands.version=0.11.0 -X github.com/snyk/parlay/lib/ecosystems.Version=0.11.0 -X github.com/snyk/parlay/lib/snyk.Version=0.11.0" \
    -o parlay .
  ```
- **上游测试命令**（conanfile build() 内真实执行）:
  ```
  go test -v -count=1 ./...
  ```
  计数：逐行解析 `--- PASS:`/`--- FAIL:`/`--- SKIP:`，discovered=72。

## 关键问题与解决方案

### P1: 源码归档下载
- **问题**: GitHub 直接下载可能不稳定
- **解决**: conandata.yml 写官方 URL 在后、gh-proxy 镜像在前作为有序回退；
  sha256 保持官方值不变（c1f9eaa0…），镜像仅做传输加速。

### P2: Go linker mmap 在 HMDFS 上失败
- **问题**: Go linker 用 mmap 写输出文件，在 HMDFS 上 `mapping output file failed: permission denied`
- **解决**: OHOS 下链接输出先写到 `/data/storage/el2/base/haps/entry/files`（探测回退到 cache），
  再拷贝回 build/bin，与 aiac/adbtuifm 经验一致。

### P3: OHOS ELF 自签名
- **问题**: OHOS 上每个被 fork/exec 的 ELF 必须携带 `.codesign` section
- **解决**: 用 `binary-sign-tool sign -selfSign 1 ... -signAlg SHA256withECDSA` 对 parlay 二进制
  及 Go SDK 工具链全部签名；找不到签名工具时仅警告（由真机门禁判定）。

### P4: 上游测试必须完整接入
- **问题**: 上游有 72 个 Go 单测，不可用 no_tests 替代
- **解决**: build() 内真实运行 `go test -v -count=1 ./...`，逐行解析三类标记行，
  输出 `HMBS_UPSTREAM_TEST_RESULT`（discovered=72）；失败则抛异常中断构建。
  lint（golangci-lint）与 bats acceptance（需外网 + bats）不在 conan 内运行，如实声明。

## 测试验证（待真机 evidence 轮填写实测数字）

- **parlay --version**: 应输出 `0.11.0`（ldflags 注入）
- **parlay --help**: 应列出 ecosystems/snyk/scorecard/deps 子命令
- **parlay ecosystems enrich not-here**: 非零退出（负例闭合）
- **上游 go test ./...**: 72/72 为目标值，以真机 `HMBS_UPSTREAM_TEST_RESULT` 为准

## 编译产物

- parlay（静态 ARM64 ELF，stripped，约数 MB）
- 本地未执行 conan（按任务守则，仅真机执行）

**编译日期**: 2026-10-02
**最终状态**: 待真机验证（built）

## 2026-10-02 fixing_verification轮修复
- 现象: 真机 go test returncode=1, 解析 PASS/FAIL为0, 旧逻辑把未观测72个算成skipped=72.
- 根因判断: 主二进制已签名但go test临时.test二进制未签名, OHOS内核拒绝fork/exec, 导致零执行; 同时旧逻辑用算术补齐skipped掩盖了零执行, 且无output tail可诊断.
- 修改: conanfile新增go-test-exec.sh wrapper(OHOS下go test -exec自签名.test二进制), 保留原始PASS/FAIL/SKIP计数不再补齐, 输出80行tail到日志, reason携带20行摘录, 缺口经gaps如实上报(ohos_feature/test_failure).

## 2026-10-02 fixing_verification轮修复（计数口径）
- 现象: 真机 `go test -v` 解析 executed=83/passed=83，discovered=72，rule4 判 inconsistent（executed+skipped>discovered）。
- 根因判断: 旧解析用 `strip()` 后判 `--- PASS:`，把缩进的子测试（t.Run，如 enrich_cyclonedx）也计入，比顶层 `grep ^func Test` 的 72 多出约 11 个。
- 修改: conanfile 改为仅计 column-0 的 `--- PASS:/FAIL:/SKIP:`（`line.startswith`，不 strip），与 72 口径对齐；test.sh 负例输出改写到 `${TMPDIR}/parlay-neg-$$.out`（原写死 `/tmp` 在真机上 cat 报 No such file）。
