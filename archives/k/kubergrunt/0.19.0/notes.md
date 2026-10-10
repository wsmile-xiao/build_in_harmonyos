# kubergrunt 0.19.0 适配笔记

## 基本信息
- **软件**: kubergrunt（Gruntwork 的 EKS/Kubernetes 集群管理辅助 CLI）
- **版本**: 0.19.0（上游 tag `v0.19.0`，2026-01-14 发布）
- **许可**: Apache-2.0
- **上游源码**: https://github.com/gruntwork-io/kubergrunt/archive/refs/tags/v0.19.0.tar.gz
- **tarball 校验**: `sha256 = 0bc4d67db238b974bb2a80b4786beb8ff3c38b748b3e10448c5f0174c7ead488`，
  `tar tzf | wc -l = 130`（顶层目录 `kubergrunt-0.19.0/`）
- **交付物**: `bin/kubergrunt`（aarch64 ELF，静态链接，带 `.codesign` 段）

## 上游构建方式（.circleci/config.yml）
```
build-go-binaries --app-name kubergrunt --src-path ./cmd --dest-path ./bin \
    --ld-flags "-X main.VERSION=$CIRCLE_TAG -extldflags '-static'"
```
本配方等价命令（`_MAIN_PACKAGE = "./cmd"`）：
```
go build -trimpath -ldflags "-s -w -X main.VERSION=0.19.0" -o <ext2>/out/kubergrunt ./cmd
```
`main.VERSION` 是上游源码里的空变量（`cmd/main.go`），由 `-X` 在链接期注入，
最终由 `gruntwork-io/go-commons/entrypoint` 渲染为 `kubergrunt version 0.19.0`。

## OHOS 平台要点（沿用本仓 dbmate 2.33.0 / tlsx 1.2.2 / aliae 1.5.0 已验证做法）
| 编号 | 现象 | 本配方处置 |
|------|------|-----------|
| E166 | Go 链接器在 HMDFS 上 mmap 写输出失败 | `GOCACHE/GOMODCACHE/GOPATH/GOTMPDIR/TMPDIR` 与 `-o` 输出全部落到 ext2（`/data/storage/el2/base/cache`，回退 `/data/storage/el2/base/haps/entry/files`） |
| E128 | 会被 execve 的 ELF 必须带 `.codesign` 段 | 自举的 Go 工具链（`bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*`）与交付二进制都用 `/data/service/hnp/bin/binary-sign-tool` 自签名（先 `llvm-objcopy --remove-section .codesign`，sign-tool 拒绝覆盖已存在的段） |
| E077 | HMDFS 的 chmod 语义（group 固定 6 / other 固定 0 / owner 保底 rw-） | 签名后统一 `chmod 0o755` 恢复 owner 的 x 位 |
| E046 | HMDFS 不支持 getcwd，而 `go` 要从 cwd 向上找 `go.mod` | 源码整树先复制到 ext2（`<work>/src`），再在该目录里 `go mod download` / `go build` / `go test` |

### go test 的 E128 特殊处理（关键）
`go test` 内部产出的测试二进制（`$GOTMPDIR/go-build*/b001/*.test`）是 go 运行时
临时生成的，配方无法预先签名；不签名则 execve 直接 `EACCES`
（现象：`fork/exec .../<pkg>.test: permission denied`）。处置与本仓 aliae 1.5.0 一致：
`go test -exec=<wrapper> ./...`，wrapper 在 exec 前对测试二进制就地签名。

## 上游测试（`go test`）统计与口径
- 命令：`go test -count=1 -json -timeout 300s ./...`（OHOS 上追加 `-exec=<sign wrapper>`）。
- 口径：**顶层 Test 函数**计数（子测试单列，不计入主线数字）。
- 上游 130 个文件中共 24 个 `_test.go`，分布在 5 个包（`cmd`、`eks`、`eksawshelper`、
  `kubectl`、`tls`），共 **89 个顶层 Test 函数**、55 个子测试；没有测试文件的包
  （`commonerrors`、`jsonpatch`、`logging`、`cmd/eks`）不计入用例数。

### Linux/x86_64 预检实测（go1.26.3 linux-amd64，本机 glibc）
| 包 | pass | fail |
|----|------|------|
| cmd | 2 | 0 |
| eksawshelper | 4 | 1（`TestTagExistsInRepo` 需 AWS ECR 凭据） |
| kubectl | 13 | 18（需真实 Kubernetes 集群 + `kubectl`） |
| tls | 23 | 10（需 Kubernetes 集群，部分经 `openssl` 校验） |
| eks | 8 | 10（需 AWS 凭据 + terraform） |
| **合计** | **50** | **39** |

- 39 个失败**全部**是外部资源依赖（AWS 凭据 / Kubernetes 集群 / terraform），
  在无凭据的 CI 环境同样不可能通过；配方**如实统计并逐条打印**，不静默跳过、不改上游断言。
- 配方把 29 个不依赖外部资源的“离线确定性用例”（`_OFFLINE_TESTS`）作为**硬门禁**：
  它们必须 100% 通过，否则 `conan create` 直接失败。本地预检 29/29 通过。
- ⚠ 上述数字来自 Linux/x86_64 预检（本机无 OHOS SDK/工具链，编译类问题无法本地复现）；
  OHOS 侧的真实数字以 CI 日志中 `===== upstream \`go test ./...\` summary =====` 段为准。

## 消费者用例（test_package/consumer_check.py）
真跑交付出来的 `bin/kubergrunt`（不是 echo 型假测试），期望值取自上游行为：
| 用例 | 命令 | 断言 |
|------|------|------|
| C1 | `kubergrunt --version` | exit 0，stdout 恰为 `kubergrunt version 0.19.0\n`（验证 `-X main.VERSION` 注入生效） |
| C2 | `kubergrunt --help` | exit 0，stdout 含上游描述 `A CLI tool to help setup and manage a Kubernetes cluster.` 与 `eks`/`k8s`/`tls` 三个子命令 |
| C3 | `kubergrunt eks --help` | exit 0，含 `deploy`/`drain`/`sync-core-components`/`cleanup-security-group`/`verify`/`configure` |
| C4 | `kubergrunt k8s --help` | exit 0，含 `wait-for-ingress`/`kubectl` |
| C5 | `kubergrunt tls gen --help` | exit 0，含必填项 `--namespace value`、`--secret-name value` |
| C6 | `kubergrunt eks oidc-thumbprint`（缺必填 flag） | exit 1，stdout 为空，stderr 含 `--issuer-url is required` |
| C7 | `kubergrunt bogus`（未知子命令） | exit 1，stderr 含 `No help topic for 'bogus'` |
| C8 | `kubergrunt --loglevel bogus` | exit 1，stderr 含 `not a valid logrus Level: "bogus"` |

## 交付形态自检（M1–M13）
M1 二进制存在 / M2 常规文件且体积在 5MB–300MB / M3 owner 可执行位 /
M4 ELF 魔数 / M5 ELF64 + 小端 + `e_machine=0xB7`(AArch64) /
M6 无 `PT_INTERP`（静态链接，CGO_ENABLED=0）/ M7 含 `.codesign` 段（OHOS）/
M8 `bin/` 下只有 `kubergrunt` 一个文件 / M9 `licenses/LICENSE` 为 Apache-2.0 全文 /
M10 交付物无 Go 源码与模块文件（`*.go`/`go.mod`/`go.sum`/`*.test`）/
M11 无隐藏文件、无 `__pycache__`/`go-build` 缓存目录 / M12 无 `*.o`/`*.a`/`*.c` 中间产物 /
M13 二进制内不含构建工作目录名（证明 `-trimpath` 生效）。

## 本地验证记录（2026-10-01，Linux/x86_64）
1. tarball 双校验：`sha256sum` 与 `tar tzf | wc -l`（130）均与 conandata.yml 一致。
2. Go 工具链镜像校验：`go1.26.3.linux-arm64.tar.gz` = `9d89a3ea…36565`（63,741,242 B，
   16,688 条目）、`go1.26.3.linux-amd64.tar.gz` = `2b2cfc71…b556`（均与 conandata.yml 一致）。
3. 用本机 go1.26.3 复现上游构建命令与全量 `go test ./...`（结果见上表）。
4. `consumer_check.py` 用同一份源码产出的二进制（`--expect-machine x86_64`）预跑：
   C1–C8 全部通过、M1–M13 全部通过（M5/M7 在 x86_64 上按参数放宽）。
5. **端到端 `conan create` 本地跑通**（Linux/x86_64，`-s os=Linux -s arch=x86_64`，
   即非 OHOS 分支）：`conan create .` 退出码 0，全流程真实执行——下载并解压
   go1.26.3（sha256 校验）、`go mod download`（1.1 GB 模块）、`go build -trimpath`、
   全量 `go test -count=1 -json -timeout 300s ./...`、test_package 消费者用例。
   日志关键行：
   - `offline deterministic gating set: 29 tests, 29 passed, 0 missing, 0 failed`
   - `packages with test binaries: 9 ; top-level Test funcs: 89 (pass=50 fail=39 skip=0) ; subtests recorded: 55`
   - `[summary] consumer checks: 32 passed, 0 failed, 1 skipped`
   （M7 在 x86_64 上按参数跳过签名校验，OHOS 侧会执行）
6. 本地修掉的一个真实缺陷（已复现证据）：`build()` 最初把源码整树 `copytree` 到
   `<build_folder>/.go-work/src`，而本地 `conan create` 的 `source_folder` **就是
   build_folder 的父目录**，导致自我复制无限递归（`shutil.Error: [Errno 36]
   File name too long`，39 GB 中间目录）。现在 OHOS 分支复制到 ext2（不在 source
   树内）并加了"禁止复制到自身内部"的硬检查；非 OHOS 分支直接用 source_folder。
   OHOS 侧源码复制到 `/data/storage/el2/base/cache/...`，不受此影响。
7. 未验证项：OHOS 侧的 ext2 路径可用性、`binary-sign-tool` 签名与 `go test -exec`
   签名链路、aarch64 ELF 的 `e_machine=0xB7` 与 `.codesign` 段——本机没有 OHOS
   SDK/工具链，只能在 CI 真机上验证。
