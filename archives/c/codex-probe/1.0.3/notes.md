# codex-probe 1.0.3 — 编译适配笔记

## 软件简介

codex-probe 是一个**单文件 Go CLI**，面向 Codex 凭证与诊断工作流：

- `--login`：OAuth PKCE 登录（本地 `:1455` 回调），写出凭证 JSON
- `--renew [-f]`：单文件或目录内凭证原地续期
- `--status`：读取剩余配额（5 小时窗口 + 每周窗口）
- `--apitest`：对每个模型端点发轻量请求验证可用性
- `--sync`：本地凭证 AES-256-GCM 加密后同步到 Supabase
- `--output <x.csv>`：把 `--status` / `--apitest` 结果导出 CSV
- `--proxy`：固定代理 / 系统代理自动探测 / `--proxy ""` 强制直连

源码：https://github.com/JamesChan21/codex-probe

## 上游真实技术事实

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/JamesChan21/codex-probe |
| 上游 tag | v1.0.3（最新 release，另外有 v1.0.0~v1.0.2） |
| 源码 URL | https://github.com/JamesChan21/codex-probe/archive/refs/tags/v1.0.3.tar.gz |
| 源码 SHA256 | `48868bd2aab102fdf32c5419a812d1792cf46e23beb2c1320a9c7c82e20051f5` |
| 上游语言 | Go（纯 Go，无 `import "C"`，无 cgo 指令） |
| 构建系统 | Go modules（`go.mod` / `go.sum`） |
| go.mod | `module github.com/QuantumNous/new-api/tools/codex-probe`，`go 1.22` |
| 命令入口 | `./cmd/codex-probe`（**不是**仓库根包；根目录无 main.go） |
| 直接依赖 | `golang.org/x/net v0.26.0`、`golang.org/x/sys v0.21.0` |
| `*_test.go` 数量 | **0** |
| `TestXxx` / `BenchmarkXxx` / `ExampleXxx` 数量 | **0** |
| CI workflow | `.github/workflows/release.yml`（GoReleaser 构建/发布，配 `.github/cliff.toml` 生成 changelog）——**无任何测试 step** |
| `go test -v -count=1 ./...` 实测 | 每包 `[no test files]`，退出码 0，真实测试数 = **0** |
| **上游真实测试统计** | **0（no_tests）** |
| license | MIT（README 声明；仓库内**无 LICENSE 文件**，GitHub API license 字段为 null） |

> ⚠️ `cmd/codex-probe/test.go` 名字像测试，但实现的是 `--apitest` **生产功能**
> （对 Codex 模型端点发轻量请求），被链接进可执行文件，不是测试夹具。

## 编译环境

- **平台**：HarmonyOS (OHOS) linux/arm64
- **Go 版本**：go1.26.5（`GOTOOLCHAIN=local`；本地不存在时由配方自举下载并签名）
- **CGO_ENABLED=0**：纯 Go 静态链接，产物无动态依赖（`llvm-readelf -d` 为空）
- **Go SDK SHA256**：`fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49`（linux-arm64）
- **工作区**：`/data/storage/el2/base/haps/entry/files/codex-probe-1.0.3-go`
- **编译命令**：
  ```
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
  GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct \
  GOSUMDB=sum.golang.google.cn \
  go build -trimpath -ldflags "-s -w" -o codex-probe ./cmd/codex-probe
  ```
- **产物**：`codex-probe`，静态 aarch64 ELF，stripped，约 6.1 MB，含 `.codesign` section

## 关键问题与解决方案

### P1: GitHub 直连下载失败
- **问题**：本机直接请求 `https://github.com/.../v1.0.3.tar.gz` 报
  `Remote end closed connection without response`。
- **解决**：`conandata.yml` 只写官方 URL（R39），CI 的 `get_mirrors`
  （`ci/conan/build_and_test.sh`）会自动改写为
  `[gh-proxy.com/<url>, <url>]` 镜像回退列表；本地分析时用
  `gh-proxy.com` 与 `codeload.github.com` 双通道下载，产物**逐字节一致**、
  sha256 交叉验证相同。

### P2: Go linker mmap 在 HMDFS 上失败（E051/E166）
- **问题**：Go linker 以 mmap 写输出文件，在 HMDFS 上报
  `mapping output file failed: permission denied`。
- **解决**：整个 Go 工作区（`GOCACHE` / `GOTMPDIR` / `GOMODCACHE` / `TMPDIR`
  与链接输出目录 `link-out`）都放到 ext2 类可写分区
  `/data/storage/el2/base/haps/entry/files`（带写探测回退到
  `/data/storage/el2/base/cache`），与 argo / spicedb / aiac 经验一致。

### P3: OHOS execve 需要代码签名（E128/E077）—— 本次最大陷阱
- **问题**：Go SDK 解压后**未签名**的 ELF 一律被拒绝执行：
  `go/bin/go: Permission denied`（rc 126）。
- **实测对照**（同机同路径，仅签名状态不同）：

  | 状态 | `go version` 结果 |
  |---|---|
  | 未签名 | Permission denied（rc 126） |
  | `binary-sign-tool sign -selfSign 1` | `go version go1.26.5 linux/arm64`（rc 0） |
  | `llvm-strip --strip-all` + 签名 | 同样可执行（rc 0） |

- **解决**：Go SDK 的 `bin/{go,gofmt}` 与 `pkg/tool/linux_arm64/*`
  全部签名（本次 10 个 ELF），产物 `codex-probe` 同样签名后再打包。
- **⚠️ 隐藏坑（本次踩到并修正）**：判定「是否已签名」**不能**用
  `.codesign` 的裸字节/字符串搜索。Go 二进制内嵌 macOS 工具链用的
  `codesign` 字样，`b".codesign" in data` 会**假阳性**判定「已签名」而跳过
  签名步骤，最终表现为 rc 126 —— 但报错信息完全指向不了真正原因
  （文件看起来有 `.codesign` 字样、`ls -l` 也有 x 位）。
  正确做法：用 `llvm-readelf -S <file>` 判定**真实的 `.codesign` section 头**。
  本配方已按此实现（`_has_codesign_section`）。

### P4: 上游无测试 → 补增消费者测试（R51 / rule8）
- **问题**：上游 1.0.3 无任何 `*_test.go`，CI 只有 GoReleaser 发布流，无测试入口。
- **解决**：`go test -v -count=1 ./...` 作为源码树审计留痕（每包
  `[no test files]`，不计为通过），HMBS 标记
  `HMBS_UPSTREAM_TEST_RESULT status=no_tests` 由 `test_package/conanfile.py`
  用裸 `print()` 输出（`MANIFEST.yml: upstream_test_in_build: false`，
  与已合入的 aiac/5.3.0 一致）。
  另在 `test_package/test.sh` 提供 **6 用例 / 13 断言**的消费者冒烟测试。

### P5: 上游地域探针会干扰测试设计
- **问题**：上游对**任何真实命令**都会先跑 `checkNotChina()`
  （依次请求 `ipinfo.io/country`、`api.country.is`、`ip-api.com`），
  全部失败则告警继续，判定为 `CN` 则打印警示框并 `exit 1`。
  若冒烟测试跑到这一步，结果会随 CI 出口地域/网络而变。
- **解决**：6 个用例全部使用**在该探针之前就失败闭合**的路径
  （参数互斥校验、配置加载失败、`--login` 缺 `-o`、`--output` 非 `.csv`），
  以及 `--help` / 空参数（直接打印 Usage 退出）。全离线，不触达网络。

### P6: `grep` 断言踩坑（测试自身缺陷，已在提交前修正）
- **问题**：`grep -Fq "--login" file` 中 needle 以 `--` 开头，被 grep 当作
  **选项**解析：`grep: unrecognized option '--login'`，断言假失败。
- **解决**：断言统一改为 `grep -Fq -e "$needle" "$file"`。
  首次实测 9/13 通过，修正后 13/13 通过。

## 源码修改

**无。** 未对上游源码做任何修改，`patches: {}`。

## 依赖版本

| 依赖 | 版本 | 获取方式 |
|---|---|---|
| Go SDK | 1.26.5 (linux-arm64) | 配方自举下载（3 个镜像顺序回退）+ sha256 校验 |
| golang.org/x/net | v0.26.0 | Go module（GOPROXY） |
| golang.org/x/sys | v0.21.0 | Go module（GOPROXY） |

无系统 C/C++ 库依赖（产物完全静态）。

## 验证结果

```bash
# 工具链
$GOROOT/bin/go version
# go version go1.26.5 linux/arm64          -> rc 0

# 产物
file codex-probe
# ELF executable, 64-bit LSB arm64, static, ..., stripped
llvm-readelf -S codex-probe | grep codesign
#   [16] .codesign   PROGBITS   ...          -> 存在

# 消费者冒烟测试（test_package/test.sh）
sh test.sh <package>/bin/codex-probe
# [case 1] --help                          rc=0  Usage / --login 命中
# [case 2] 空参数                           rc=0  Usage 命中
# [case 3] --sync --status                 rc=1  "--sync cannot be combined"
# [case 4] --config <不存在> --login        rc=1  "failed to load config"
# [case 5] --config <存在> --login          rc=1  "--login requires -o"
# [case 6] --status --output report.txt    rc=1  "--output path must end with .csv"
# [ok] all 13 assertions passed across 6 cases   -> rc 0, 13/13
```

- **上游测试用例通过率**：0/0（上游无测试，不适用；清点证据见
  `test_package/MANIFEST.yml` 的 `upstream_test_audit`）
- **新增测试用例通过率**：13/13 断言（6/6 用例）100%

## 注意事项

1. **上游无 LICENSE 文件**：README 声明 MIT，但 tag v1.0.3 仓库内不含 LICENSE，
   故包内未附 license 文件，manifest 记为 MIT 并注明来源。
2. **地域限制属上游设计**：codex-probe 在任何真实命令前做地域探测，检测到
   `CN` 会主动 `exit 1`（提示配置代理）。这是上游行为，非适配缺陷；在鸿蒙 PC
   上使用时需按上游说明配置代理或 `--proxy`。
3. **凭证与密钥**：`--sync` 使用 `sync_aes_gcm_key`（AES-256-GCM）加密本地
   凭证，密钥来自用户本地配置，本适配不涉及任何密钥注入。
4. **签名是硬前提**：任何在 OHOS 上要 `execve` 的 Go ELF（含 Go SDK 自身）
   都必须携带有效 `.codesign` section；判定请用 `llvm-readelf -S`，
   不要用字符串搜索。

**编译开始**：2026-09-18
**最终状态**：built
---

**编译结束**: 2026-09-18 22:01
**最终状态**: built
