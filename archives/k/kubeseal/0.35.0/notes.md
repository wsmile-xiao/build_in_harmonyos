# kubeseal 0.35.0 适配笔记

## 基本信息
- **软件**: kubeseal / sealed-secrets controller（bitnami-labs/sealed-secrets — 用非对称密钥把 K8s Secret 加密成可安全入库的 SealedSecret）
- **版本**: 0.35.0（上游 tag `v0.35.0`）
- **许可**: Apache-2.0
- **上游源码**: https://github.com/bitnami-labs/sealed-secrets/archive/refs/tags/v0.35.0.tar.gz
- **tarball 校验**: `sha256 = 2ded0a68ee2a39f32214c6c11c4f6ba5597bc383cf1359594e95b9eede349fc1`，
  `tar tzf | wc -l = 426`（顶层目录 `sealed-secrets-0.35.0/`，1329290 字节）
- **交付物**: `bin/kubeseal`（客户端，aarch64 ELF 静态、`-trimpath -s -w`、带 `.codesign`）与
  `bin/controller`（`sealed-secrets` 控制器本体，同一套构建参数）

## 上游构建方式
- 单模块双命令（module `github.com/bitnami-labs/sealed-secrets`，go.mod 要求 **go 1.25.7**）：
  `cmd/kubeseal` 与 `cmd/controller`。
- 上游 Makefile：`GO_LD_FLAGS = -X main.VERSION=$(VERSION)`，其中 `VERSION` 取
  `git describe --exact-match --abbrev=0 --tags` 的 tag（无 tag 时退化为 commit hash）。
  ⚠ **tarball 里没有 `.git`**，所以必须显式注入版本，否则两个二进制都打印源码默认值
  `UNKNOWN`（`pkg/buildinfo.DefaultVersion`）——本配方与 release 构建一致地注入 `v0.35.0`。
- 本配方等价命令（两个 main 包各一条）：
  ```
  go build -trimpath -ldflags "-s -w -X main.VERSION=v0.35.0" -o <ext2>/out/kubeseal   ./cmd/kubeseal
  go build -trimpath -ldflags "-s -w -X main.VERSION=v0.35.0" -o <ext2>/out/controller ./cmd/controller
  ```
- 交付集合与软件级 `archives/k/kubeseal/commands.json` 的
  `versions."0.35.0".commands = ["kubeseal", "controller"]` 严格一致（M8 自检会比对）。

## OHOS 平台要点（沿用本仓 kubergrunt 0.19.0 / yq 4.53.6 / dbmate 2.33.0 / tlsx 1.2.2 / aliae 1.5.0 已验证做法）
| 编号 | 现象 | 本配方处置 |
|------|------|-----------|
| E166 | Go 链接器在 HMDFS 上 mmap 写输出失败 | `GOCACHE/GOMODCACHE/GOPATH/GOTMPDIR/TMPDIR` 与两个 `-o` 输出全部落到 ext2（`/data/storage/el2/base/cache`，回退 `/data/storage/el2/base/haps/entry/files`，做真实写探针） |
| E128 | 会被 execve 的 ELF 必须带 `.codesign` 段 | 自举的 Go 工具链（`bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*`）与两个交付二进制都用 `/data/service/hnp/bin/binary-sign-tool` 自签名（先 `llvm-objcopy --remove-section .codesign`） |
| E077 | HMDFS 的 chmod 语义（group 固定 6 / other 固定 0 / owner 保底 rw-） | 签名/解包后统一 `chmod 0o755` 恢复 owner 的 x 位 |
| E046 | HMDFS 不支持 getcwd，而 `go` 要从 cwd 向上找 `go.mod` | 源码整树先复制到 ext2（`<work>/src`）再 `go mod download` / `go build` / `go test` |

### go test 的 E128 特殊处理
`go test` 内部生成的测试二进制（`$GOTMPDIR/go-build*/b001/*.test`）配方无法预先签名，
不签名则 execve 直接 `EACCES`（`fork/exec ...: permission denied`）。处置与 kubergrunt /
yq / aliae 一致：`go test -exec=<wrapper>`，wrapper 在 exec 之前就地签名再 `exec`。

## 上游测试（`go test`）统计与口径
- 命令：`go test -count=1 -json -timeout 300s ./...`（OHOS 上追加 `-exec=<sign wrapper>`）。
- **口径（都写明，避免少报）**：
  1. 源码 `^func Test` 共 **70 处**（`integration/integration_suite_test.go` 那条在
     `//go:build integration` 标记下，默认不调度）；
  2. 默认 `go test ./...` **实际调度 69 个顶层用例**（68 pass / 1 fail）+ **43 个子测试**
     = **112 个用例事件**；
  3. 硬门禁 = 9 个上游测试包的 **68 条离线确定性用例**（69 条调度用例减去 1 条环境依赖）。
- **唯一失败项 `pkg/controller/TestHttpCert` 属环境依赖（固定端口）**：该用例用
  `httpserver(...)` 绑定 `listenAddr`（默认 `:8080`）再对 `http://localhost:8080/v1/cert.pem`
  发真实请求；当 runner 上 8080 被占用时必然失败
  （本机复现：`ERROR HTTP server exiting error="listen tcp :8080: bind: address already in use"`）。
  它既不是配方的缺陷、也不是本平台的缺陷，且**无法在配方侧消灭**（用例里的默认端口由上游
  包级变量决定，改它就得改上游代码）⇒ 如实单列、不计入门禁。
- 其余用例全部离线确定性：`pkg/kubeseal`（加解密核心）、`pkg/crypto`、`pkg/apis/.../v1alpha1`
  （20 条转换语义）、`cmd/kubeseal`/`cmd/controller` 的 CLI 用例、`pkg/flagenv`/`pkg/pflagenv`/
  `pkg/multidocyaml` 工具用例。上游测试里**没有** `t.Skip`，因此门禁要求严格 `pass`。

### Linux/x86_64 预检实测（go1.26.3 linux-amd64）
| 包 | pass | fail | skip | 子测试 |
|----|------|------|------|--------|
| `cmd/controller` | 1 | 0 | 0 | 0 |
| `cmd/kubeseal` | 6 | 0 | 0 | 3 |
| `pkg/apis/sealedsecrets/v1alpha1` | 20 | 0 | 0 | 4 |
| `pkg/controller` | 26 | **1**（TestHttpCert，固定 :8080） | 0 | 0 |
| `pkg/crypto` | 1 | 0 | 0 | 0 |
| `pkg/flagenv` | 1 | 0 | 0 | 0 |
| `pkg/kubeseal` | 11 | 0 | 0 | 36 |
| `pkg/multidocyaml` | 1 | 0 | 0 | 0 |
| `pkg/pflagenv` | 1 | 0 | 0 | 0 |
| **合计（调度）** | **68** | **1** | **0** | **43** |

- 用例事件总计 **112**（另有 12 个无 `_test.go` 的包被 `./...` 触及但不计用例）。
- 门禁：`offline deterministic gating set: 9 packages, 69 upstream cases scheduled,
  68 gated (after excluding 1 environment-dependent case(s)), passed=68 failed=0
  missing_pkgs=0`。
- ⚠ 上述数字来自 Linux/x86_64 预检（本机无 OHOS SDK/工具链）；OHOS 侧真实数字以 CI 日志中
  `===== upstream \`go test ./...\` summary =====` 段为准。

## 消费者用例（test_package/consumer_check.py，11 个用例 / 48 项断言）
真跑交付出来的 `bin/kubeseal` 与 `bin/controller`，期望值是外部可核对真值：
| 用例 | 命令 | 断言 |
|------|------|------|
| C1 | `kubeseal --version` | exit 0，stdout 恰为 `kubeseal version: v0.35.0\n`（验证 `-X main.VERSION` 注入） |
| C2 | `kubeseal --help` | exit 0，stdout 含 `--cert`/`--recovery-unseal`/`--recovery-private-key`/`--fetch-cert`/`--scope`/`--format` |
| C3 | `kubeseal --cert <cert> --format json < Secret` | exit 0；`kind: SealedSecret`、`apiVersion: bitnami.com/v1alpha1`、name/namespace 保持、`spec.encryptedData` 恰为 `foo`/`hello` 且每个值都是 >64 字符的密文 |
| C4 | `kubeseal --recovery-unseal --recovery-private-key <key> -o json < SealedSecret` | exit 0；`kind: Secret`、name/namespace 一致、`data.foo == "YmFy"`、`data.hello == "d29ybGQ="`，base64 解码后 == `b"bar"`（**逐字段往返比对**） |
| C5 | 同上但 `--format yaml` | exit 0；YAML 里 `kind: SealedSecret`、`apiVersion`、name/namespace、`encryptedData` 的 foo/hello 齐全 |
| C6 | 用 C5 的 YAML 走 `--recovery-unseal -o yaml` | exit 0；`kind: Secret` 且 `foo: YmFy`、`hello: d29ybGQ=` 与原 Secret 逐字节一致 |
| C7 | 用**另一对钥匙的私钥**解封同一份 SealedSecret | **exit 1**、stdout 为空、stderr 含 `no key could decrypt secret`（证明密文确实绑定在封印证书的公钥上，不是原样搬抄） |
| C8 | `kubeseal --cert <不存在的文件>` | exit 1、stderr 含 `no such file or directory` |
| C9 | `kubeseal --cert <有效证书>` + 非 Secret 输入 | exit 1、stderr 含 `no secrets found` |
| C10 | `controller --version` | exit 0，stdout 恰为 `controller version: v0.35.0\n` |
| C11 | `controller --help` | exit 0，合并 stdout+stderr 后含 `--key-prefix`/`--key-renew-period`/`--key-size`（控制器用 k8s flag 包，`--help` 走 stderr） |

证书/私钥来源做了双路径（断言完全相同）：
1. 环境里有 `openssl` ⇒ 现场生成 RSA-2048 自签证书（本机预检走这条）；
2. 没有 `openssl` ⇒ 退回脚本内嵌的离线测试夹具（**公开测试数据、非真实凭据**，
   `CN=sealed-secrets-test-1/2`）。
脚本会打印实际使用的路径；两条路径本地都跑通（48 passed / 0 failed）。

## 交付形态自检（M1–M14，纯 Python 读字节判定，不依赖目标机的 readelf/nm/file）
M1 两个声明的二进制都在 / M2 体积在 5MiB–300MiB / M3 owner 有可执行位 / M4 ELF 魔数 /
M5 ELF64 + 小端 + `e_machine=0xB7`(AArch64) / M6 程序头**无 `PT_INTERP`**（CGO_ENABLED=0 静态）/
M7 含 `.codesign` 段（OHOS）/ M8 **`bin/` 集合恰等于 commands.json 声明的 `commands` 集合** /
M9 `licenses/LICENSE` 是 Apache-2.0 正文 / M10 包内无 `*.go`/`go.mod`/`go.sum`/`*.test` /
M11 无隐藏文件、无 `__pycache__`/`go-build` 缓存目录（JC5）/ M12 无 `*.o`/`*.a`/`*.c`/`*.s`/`*.h` /
M13 二进制内不含构建工作目录名（`conan-go-build`/`.go-work`）⇒ `-trimpath` 生效 /
M14 两个二进制 `--version` 都嵌入了钉住的版本串。

## 本地验证记录（2026-10-01，Linux/x86_64）
1. tarball 双校验：`sha256sum` 与 `tar tzf | wc -l`（426）均与 conandata.yml 一致。
2. Go 工具链镜像校验：`go1.26.3.linux-arm64.tar.gz` = `9d89a3ea…36565`（63741242 字节、16688 条目）、
   `go1.26.3.linux-amd64.tar.gz` = `2b2cfc71…eb556`，与 conandata.yml 逐位一致。
3. 用本机 go1.26.3 复现上游构建命令（两个 main 包）与全量 `go test ./...`（结果见上表，全量约 66 秒）。
4. `consumer_check.py` 用同一份源码产出的二进制（`--expect-machine x86_64`）预跑：
   **48 passed / 0 failed / 1 skipped**（11 个消费者用例 + 14 条 M 自检；M7 在 x86_64 上按参数跳过），
   并单独验证了"无 openssl"的夹具 fallback 路径同样 48/0。
5. **端到端 `conan create`（`-s os=Linux -s arch=x86_64`）退出码 0**，全流程真实执行：
   下载并解压 go1.26.3（sha256 校验）→ `go mod download` → 两次 `go build -trimpath` →
   全量 `go test -count=1 -json -timeout 300s ./...` → `package()` → `conan test` 消费者用例。
   日志关键行：
   - `packages touched: 21 ; top-level Test funcs scheduled: 69 (pass=68 fail=1 skip=0) ; subtests recorded: 43 ; total cases: 112`
   - `offline deterministic gating set: 9 packages, 69 upstream cases scheduled, 68 gated (after excluding 1 environment-dependent case(s)), passed=68 failed=0 missing_pkgs=0`
   - `[summary] consumer checks: 48 passed, 0 failed, 1 skipped`
   - recipe revision `b795550ff2c9323c8bc7483e8771cd6c`（与提交内容一致）
6. 未验证项：OHOS 侧的 ext2 路径可用性、`binary-sign-tool` 签名三条链路（工具链 ELF、两个交付
   二进制、`go test -exec` 的测试二进制）、aarch64 的 `e_machine=0xB7` 与 `.codesign` 段、
   以及 worker 上 `openssl` 是否可用（不可用则自动走内嵌夹具，两条路径都已本地验证）——
   只能在 CI 真机上验证（与已合入的 kubergrunt 0.19.0 / yq 4.53.6 同一套路线）。
