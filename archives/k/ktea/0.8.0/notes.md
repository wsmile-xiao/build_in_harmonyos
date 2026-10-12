# ktea 0.8.0 适配笔记

## 基本信息

- **软件**: ktea — Kafka TUI（终端用户界面）客户端，基于 charmbracelet/bubbletea
- **版本**: 0.8.0（首次适配，无后缀）
- **上游**: https://github.com/jonas-grgt/ktea（tag v0.8.0）
- **许可证**: Apache-2.0（LICENSE 为 Apache License 2.0 全文）
- **构建系统**: Go custom（`go build ./cmd/ktea`）
- **Go 要求**: go.mod 声明 `go 1.25.4`，配方自举 Go 1.26.5（`GOTOOLCHAIN=local`）
- **源码**: `https://github.com/jonas-grgt/ktea/archive/refs/tags/v0.8.0.tar.gz`
- **SHA256**: `3bf694bd583e0e655a3540c4d812e64726db632f4e7080d4cf9fbef4b1a3d363`
- **模块**: module ktea；无 vendor/；无 CGO；入口 ./cmd/ktea（package main，`var version string`）
- **编译日期**: 2026-10-08

## 上游测试审计（R51，基于 v0.8.0 源码包实测统计）

`go test ./...` 覆盖 **29 个包、46 个 `_test.go` 文件、72 个顶层 `func Test`**（含
kadmin/sradmin 的 TestMain，TestMain 也以 `func Test` 前缀计入）。tests/ 目录无 `_test.go`，
不计入。

| 包 | 顶层 Test | 运行策略 |
|----|-----------|----------|
| cmd/ktea | 1 | ✅ 运行 |
| config | 1 | ✅ 运行 |
| kcadmin | 1 | ✅ 运行 |
| serdes | 1 | ✅ 运行 |
| ui/components/border | 1 | ✅ 运行 |
| ui/components/chips | 1 | ✅ 运行 |
| ui/components/cmdbar | 4 | ✅ 运行 |
| ui/components/notifier | 1 | ✅ 运行 |
| ui/components/statusbar | 1 | ✅ 运行 |
| ui/components/tab | 1 | ✅ 运行 |
| ui/pages/cgroups_page | 1 | ✅ 运行 |
| ui/pages/cgroups_topics_page | 1 | ✅ 运行 |
| ui/pages/configs_page | 4 | ✅ 运行 |
| ui/pages/consume_form_page | 1 | ✅ 运行 |
| ui/pages/consume_page | 1 | ✅ 运行 |
| ui/pages/create_cluster_page | 8 | ✅ 运行 |
| ui/pages/create_schema_page | 1 | ✅ 运行 |
| ui/pages/create_topic_page | 2 | ✅ 运行 |
| ui/pages/kcon_clusters_page | 1 | ✅ 运行 |
| ui/pages/kcon_page | 7 | ✅ 运行 |
| ui/pages/publish_page | 2 | ✅ 运行 |
| ui/pages/record_details_page | 2 | ✅ 运行 |
| ui/pages/schema_details_page | 1 | ✅ 运行 |
| ui/pages/subjects_page | 1 | ✅ 运行 |
| ui/pages/topics_page | 1 | ✅ 运行 |
| ui/tabs/cgroups_tab | 1 | ✅ 运行 |
| ui/tabs/clusters_tab | 1 | ✅ 运行 |
| **27 个可运行包小计** | **49** | ✅ 全过 |
| kadmin | 17 + TestMain | ⛔ 仅 go test -c 编译证明可编译 |
| sradmin | 4 + TestMain | ⛔ 仅 go test -c 编译证明可编译 |
| **29 包合计** | **72**（含 2 个 TestMain） | 27 包实跑 + 2 包编译证明 |

### 23 个阻塞用例原因（kadmin 18 + sradmin 5，全部同根因）

`kadmin/kadmin_test.go:32` 与 `sradmin/sradmin_test.go:18` 的 `TestMain(m *testing.M)`
调用 testcontainers-go 在 `TestMain` 内启动 Docker 容器；OHOS（HarmonyOS PC）无 Docker
守护进程，硬跑必然在启动容器时失败：

| 包 | 文件 | 阻塞原因 |
|----|------|----------|
| kadmin | kadmin_test.go | TestMain 经 testcontainers-go/modules/kafka 启动 Docker Kafka 容器 |
| kadmin | mtls_test.go | TestMain 复用 kadmin 包级 TestMain（Docker），mtls 用例依赖 Redpanda 容器镜像 docker.redpanda.com/...:v23.3.10 |
| kadmin | sarama_kadmin_scram_test.go | TestMain 复用包级 TestMain（Docker），SCRAM 用例依赖 Redpanda 容器 |
| kadmin | cgroup_*_test.go（5） | 复用包级 TestMain（Docker Kafka），无容器则无法提供真实 broker |
| kadmin | cluster_config_test.go | 复用包级 TestMain（Docker Kafka） |
| kadmin | config_lister_test.go | 复用包级 TestMain（Docker Kafka） |
| kadmin | config_updater_test.go | 复用包级 TestMain（Docker Kafka） |
| kadmin | offset_lister_test.go | 复用包级 TestMain（Docker Kafka） |
| kadmin | record_reader_test.go | 复用包级 TestMain（Docker Kafka） |
| kadmin | topic_creator/deleter/lister/publisher_test.go（4） | 复用包级 TestMain（Docker Kafka） |
| sradmin | sradmin_test.go | TestMain 经 testcontainers-go/modules/compose 读取 docker-compose.yml 起 Schema-Registry compose |
| sradmin | srclient_sradmin_test.go | 复用包级 TestMain（compose Schema-Registry） |
| sradmin | subject_deleter_test.go | 复用包级 TestMain（compose Schema-Registry） |
| sradmin | subject_lister_test.go | 复用包级 TestMain（compose Schema-Registry） |

**处置**：不虚报通过率。kadmin/sradmin 在 build() 内以 `go test -mod=mod -c` 编译测试
二进制证明可编译（产物落 go-workspace/test-out，自签名），但不执行；其 23 个 Test 函数
以 `blocked` 计入 HMBS_UPSTREAM_TEST_RESULT。剩余 27 个包真实运行且全过。

### 27 包实跑结果（OHOS aarch64，2026-10-08 真机回填）

全部 27 包按 E318/P017 范式执行：`go test -mod=mod -c` 编译到 go-workspace/test-out →
binary-sign-tool 自签名 → 回包源码目录 `-test.v -test.count=1` 运行（保留相对 fixture
路径）。

**discovered=executed=passed=418，failed=0，skipped=0**（49 个顶层 Test 展开含子测试共
418 例；全部离线，无 TTY 依赖，UI 测试均为内存 mock 的 model/Update/View 断言）。

逐包通过数（HMBS_GO_TEST_PKG，recipe-parser 口径含子测试）：cmd_ktea 5 / config 19 /
kcadmin 2 / serdes 5 / border 10 / chips 7 / cmdbar 23 / notifier 5 / statusbar 5 / tab 14 /
cgroups_page 11 / cgroups_topics_page 8 / configs_page 15 / consume_form_page 28 /
consume_page 20 / create_cluster_page 52 / create_schema_page 8 / create_topic_page 24 /
kcon_clusters_page 3 / kcon_page 18 / publish_page 18 / record_details_page 22 /
schema_details_page 21 / subjects_page 35 / topics_page 14 / cgroups_tab 3 / clusters_tab 23
（全部 0 fail）。

- 证据：`upstream-go-test.log` + `test-out/*.log`（418 条 `--- PASS:`、0 条 `--- FAIL:`、
  0 条 `--- SKIP:`），标记 `HMBS_UPSTREAM_TEST_RESULT` / `HMBS_GO_TEST_PKG`。

## 编译方案

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=mod \
GOPROXY=https://goproxy.cn,direct GOSUMDB=sum.golang.google.cn \
  go mod download
  go build -trimpath -mod=mod \
  -ldflags "-s -w -X main.version=v0.8.0" \
  -o <workspace>/link-out/ktea ./cmd/ktea
```

- 上游**无 vendor/**，构建期先 `go mod download`（GOPROXY=goproxy.cn）拉取模块闭包
  （IBM/sarama、bubbletea/bubbles/huh/lipgloss、kafka-go、testcontainers、
  docker/containerd/k8s.io 等，go.sum 大，含 Docker 侧间接依赖约 638MB 模块缓存）。
- go.mod 含两个 `replace`（huh/srclient → jonas-grgt fork），GOPROXY 以伪版本正常提供。
- 版本注入：cmd/ktea 声明 `var version string`（package main），上游 goreleaser 用
  `-X main.version` 注入；本配方 `-ldflags "-s -w -X main.version=v0.8.0"` 对齐。
  二进制**无 --version flag**（仅 -debug/-plain-fonts），Go flag 对 -help 打印 usage 且
  exit 0（smoke 用 --help）。
- OHOS 上 GOOS 取 `linux`，产物经 `binary-sign-tool` 自签名后方可 execve；单遍
  `go build -o` 一次成型输出到 go-workspace/link-out（HMDFS mmap 链接限制，
  E124/E134/E166 模式），签名后拷入包 bin/。
- Go 工作目录（GOCACHE/GOMODCACHE/GOTMPDIR/链接输出/测试 ELF）路由到
  `/data/storage/el2/base/haps/entry/files/ktea-conan-go/0.8.0`（可经
  `OHOS_GO_WORKDIR` 覆盖），规避 HMDFS 限制。
- Go 1.26.5 SDK 自举：arm64 tarball sha256
  `fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49`；
  SDK 全部工具 ELF（bin/go、bin/gofmt、pkg/tool/linux_arm64/*）签名后可用
  （`link` 等未签名 exec 报 permission denied）。

## test_package（OHOS 特有用例，非上游复用）

1. 二进制存在且可执行
2. ELF magic（\x7fELF）
3. `ktea --help` 执行且输出含 plain-fonts/debug（Go flag usage，exit 0）
4. （OHOS-only）产物 ELF 含 binary-sign-tool 写入的 `.codesign`/`.note.ohos` 签名节
   （未签名 ELF 会被 HarmonyOS execve 拒绝）
5. （OHOS-only）CGO_ENABLED=0 产物静态链接：无 PT_INTERP、无 DT_NEEDED（无 glibc/musl
   动态耦合）

## 源码修改

无源码修改，无 patches，纯 Go 编译。

## 运行时说明

- ktea 是交互式 TUI：`--help` 可在无 TTY 环境正常输出并 exit 0；实际连接 Kafka 需要
  broker 网络可达，属运行环境条件，不影响构建与离线测试。
- CGO_ENABLED=0 使用纯 Go DNS 解析器（读 /etc/resolv.conf），符合 OHOS 环境。

## 验证结果（2026-10-08 真机回填）

- conan-verify G0-G4 + L2/L4/L5 全过，`conan create` 通过，status published。
- 上游测试：27 包实跑 418/418 通过（0 fail 0 skip）；kadmin+sradmin 23 个 Test 阻塞
  （TestMain 需 Docker），仅编译证明，详见上文。
- test_package 5/5 通过（--ohos 口径），`HMBS_TEST_PACKAGE_RESULT` passed。
---

**编译结束**: 2026-10-08 22:28
**最终状态**: published
