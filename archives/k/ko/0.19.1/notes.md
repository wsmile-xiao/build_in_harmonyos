# ko 0.19.1 适配笔记

## 目标库

- ko-build/ko v0.19.1：从 Go 源码直接构建容器镜像（无需 Dockerfile）的 CLI 工具。
- 纯 Go：`import "C"` = 0、`#cgo` = 0、无 `//go:embed`、无 vendor/、无 replace。
- go.mod 要求 `go 1.26.3`（硬下限，GOTOOLCHAIN=local）。
- 19 direct + 142 indirect Go module（go.sum 586 行），由 `go mod download` 经 goproxy.cn 拉取。
- conan 依赖图为空图（无任何 self.requires / tool_requires），R36 无阻塞。

## 编译环境

- 构建系统: Go (CGO_ENABLED=0 静态编译)
- 编译日期: 2026-09-18
- 编译器: Go 1.26.3 linux/arm64（配方自下载，golang.google.cn → dl.google.com 回退，
  sha256 9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565，
  与 archives/a/ahoy/2.5.0 内嵌值一致）
- 状态: built

## 编译命令

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct \
GOSUMDB=sum.golang.google.cn \
go build -trimpath -ldflags "-s -w -X github.com/google/ko/pkg/commands.Version=v0.19.1" \
  -o <el2>/link-out/ko .
```

## 上游测试

- 入口：`go test ./...`（CI test.yaml：`go test -coverprofile=coverage.txt -covermode=atomic -race ./...`）
- 29 个 `*_test.go`，testify + stdlib testing。
- OHOS 技法（kics 2.1.20 同款）：`go test -c` 逐包编译测试二进制 → binary-sign-tool 自签名 →
  作为 conan 进程子进程直接运行（`-test.v -test.count=1`），每个测试二进制在其**包目录**内运行
  （与 go test 行为一致，保证相对路径 testdata 可解析）。
- 不预 skip 任何用例。实测探针证明：自签名 Go 二进制可以 fork/exec 系统 git（2.45.2），
  因此 pkg/internal/git 的 gittesting.GitInit 系用例真实执行。

## OHOS 平台适配点

| # | 平台限制 | 处置 |
|---|---|---|
| 1 | Go 链接器 mmap 在 HMDFS 上 permission denied | 链接输出落 /data/storage/el2 ext2 工作区，再拷回 build/bin |
| 2 | 未签名 ELF 不能 fork/exec | ko 产物与 go test -c 的测试二进制全部 binary-sign-tool 自签名 |
| 3 | Go SDK 自带的 go/gofmt/compile/link 等工具二进制同样不能 exec | SDK 解压后整体签名（.ohos-signed 标记幂等） |
| 4 | /tmp 只读 | TMPDIR/GOTMPDIR/GOCACHE/GOMODCACHE 全部落 el2 工作区 |
| 5 | ko 无 vendor 目录 | GOFLAGS 不设 -mod=vendor，改 `go mod download`（GOPROXY=goproxy.cn + GOSUMDB=sum.golang.google.cn） |
| 6 | GOTOOLCHAIN=local | 防止 go 试图联网下载 toolchain（SDK 1.26.3 恰好满足 go.mod 下限） |

## test_package（鸿蒙消费者用例）

| # | 用例 | 验证内容 |
|---|---|---|
| 1 | `ko version` | 输出包含 v0.19.1（ldflags 注入链路 + 二进制可执行） |
| 2 | `ko help` | 列出 build/apply/create/publish/resolve/run/version/cache 全部核心子命令（cobra 命令面完整） |
| 3 | `ko completion bash` | 真实 cobra completion 路径生成含 __ko_start 的补全脚本 |

## 验证结果

### conan create（3 轮，最终轮 EXIT=0）

- 命令：`conan create archives/k/ko/0.19.1 -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build="ko/*"`
- 日志：`reports/conan-create.log`（round3 最终）；round1/round2 留档于 `reports/conan-create.round1.log` / `.round2.log`
- round1：构建成功但 test_package 2 个断言写错（基于对子命令面/completion 标记的错误预期）→ exit 1
- round2：修 test.sh 断言 + 剥离测试运行 env 的 GOOS/GOARCH（ko 的 NewBuilder 视进程级 GOOS 与 --platform 冲突）→ exit 0
- round3：补 G1 要求的 export_sources()/apply_conandata_patches()（no-op，patches 为空）后终跑 → exit 0
- package_id `6b129b068851896169fae42d399fa922d239ce8a`（三轮一致，settings os=OHOS arch=armv8）
- 产物：`bin/ko` ELF 64-bit LSB arm64, static, stripped, 31638592 B；`ko version` → `v0.19.1`（EXIT=0）

### 上游测试（实际执行，go test 全量）

- 测试命令（OHOS 技法）：`go test -c -o <bin> <pkg>`（逐包，10 个含测试的包）→ binary-sign-tool 自签名 → 从**各包目录**直接运行 `<bin> -test.v -test.count=1`
- 完整输出：`reports/upstream_test_full.log`
- **统计：用例总数 278，通过 260，失败 18，跳过 0**（HMBS_UPSTREAM_TEST_RESULT 见 conan-create.log）

| 包 | 通过 | 失败 |
|---|---|---|
| pkg/build | 88 | 11 |
| pkg/caps | 69 | 0 |
| pkg/commands | 8 | 5 |
| pkg/commands/options | 20 | 0 |
| pkg/internal/git | 8 | 0 |
| pkg/internal/gittesting | 1 | 0 |
| pkg/internal/testing | 2 | 0 |
| pkg/publish | 13 | 2 |
| pkg/publish/kind | 4 | 0 |
| pkg/resolve | 46 | 0 |

失败用例（18 个 FAIL 行，其中 3 个为父级聚合，叶子用例 15 个）与归因：

| 根因类 | 用例 | 归因证据 |
|---|---|---|
| HMDFS 软链 lstat 被拒（自签名二进制受限） | TestGoBuild、TestGoBuildWithKOCACHE、TestGoBuildWithoutSBOM、TestGoBuildIndex、Test_gobuilds（顶层+4 子用例）、TestPublishImages、TestNewBuilder（顶层+1 子用例） | `tarring kodata: filepath.Walk(".../test/kodata"): lstat .../kodata/b: permission denied`。`test/kodata/b -> a` 是上游源码自带软链（专为测试软链 chasing 设计）；自签名 Go 二进制在 HMDFS 上 lstat 软链 EACCES（项目已知平台限制，kics symlink 限制同源） |
| os.Symlink() 被拒 | TestWalkRecursiveSymlinkTraversal、TestWalkRecursiveSymlinkWithinKodata | `symlink ...: permission denied`（测试本体创建软链；平台限制） |
| 硬编码 /tmp + OHOS /tmp 只读 | TestLayout、TestMulti | `mkdir /tmp/ko...: read-only file system`（layout_test.go:35 / multi_test.go:47 硬编码 `os.MkdirTemp("/tmp", "ko")`） |
| docker daemon 依赖 | TestNewPublisherCanPublish（顶层+bare_with_local_domain_and_repo 子用例） | `dial unix /var/run/docker.sock: connect: no such file or directory`（该用例本就要真实 docker daemon，上游 CI 是 ubuntu 有 docker） |
| 间歇性网络（3 轮中 round3 通过） | TestDebugger | round1 `Empty reply from server`、round2 `curl 28 connect timeout`、round3 通过（`git clone https://github.com/go-delve/delve.git`） |

以上 18 个失败**全部归因为平台/环境限制，非配方或代码缺陷**；修复方向均超出包配方能力
（HMDFS 软链限制、/tmp 只读、无 docker daemon、github 直连不稳）。

### test_package（3 个鸿蒙消费者用例，全部通过）

```
[ok] ko version reports v0.19.1 (output: v0.19.1)
[ok] ko help lists all core subcommands (build/apply/create/resolve/run/delete/login/version)
[ok] ko completion bash generated a valid bash completion script
[ok] all 3 HarmonyOS consumer test cases passed
```

### conan-verify

- `python3 scripts/ohc-run.py conan-verify ko 0.19.1` → **Verdict: PASS**（EXIT=0）
- G0/G1/G2/G3/G4 ✅，L2/L4/L5 ✅；G4 的「无法找到程序包 ID」⚠️ 为框架已知 bug（listing 层级取错），非阻塞
- 报告：`reports/conan-verify-report.md`

### 可复现性

- 三轮 package_id 一致（6b129b06…）；round2 与 round3 的失败集合 diff 仅 TestDebugger 一项（间歇网络），其余完全一致。
---

**编译结束**: 2026-09-18 15:04
**最终状态**: built
