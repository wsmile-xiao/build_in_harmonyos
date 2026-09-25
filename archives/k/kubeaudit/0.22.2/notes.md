# kubeaudit 0.22.2 适配笔记

## 基本信息

- **软件**: kubeaudit — Kubernetes 安全审计工具（Shopify），审计集群/清单是否符合安全最佳实践
- **版本**: 0.22.2（首次适配，无后缀）
- **上游**: https://github.com/Shopify/kubeaudit（tag v0.22.2，剥 tag 后 commit 92c3147139a73eab8f6c9cbf9a1ee4d9c4196bd8）
- **许可证**: MIT（LICENSE 为 9 行 MIT 文本，Copyright 2017 Shopify Inc）
- **构建系统**: Go custom（`go build ./cmd`）
- **Go 要求**: go.mod 声明 `go 1.22.1`，配方使用 Go 1.24.0 工具链（`GOTOOLCHAIN=local`）
- **源码**: `https://github.com/Shopify/kubeaudit/archive/refs/tags/v0.22.2.tar.gz`
- **SHA256**: `90752d42c4d502ab6776af3358ae87a02d2893fc2bb7a0364d6c1fdcd8ff0570`（136701 字节，实测下载验算）
- **申请人**: GoliWie，队伍：不知对不队

## 上游测试审计（2026-09-23，基于 v0.22.2 源码包实测解包统计）

`go test ./...` 覆盖 21 个包、37 个 `_test.go` 文件、64 个顶层 `Test` 函数：

| 包 | 文件数 | 说明 |
|----|--------|------|
| .（根包） | 6 | kubeaudit/options/util/fix/ 示例用例（MANIFEST_MODE） |
| auditors/all | 1 | 组合审计器（fixtures） |
| auditors/apparmor | 1 | AppArmor 注解 |
| auditors/asat | 2 | automountServiceAccountToken |
| auditors/capabilities | 2 | capabilities add/drop |
| auditors/deprecatedapis | 1 | 废弃 API 版本 |
| auditors/hostns | 2 | hostPID/hostNetwork/hostIPC |
| auditors/image | 1 | 镜像 tag/digest |
| auditors/limits | 1 | 资源 limits |
| auditors/mounts | 1 | 敏感 hostPath 挂载 |
| auditors/netpols | 2 | NetworkPolicy 覆盖 |
| auditors/nonroot | 2 | runAsNonRoot |
| auditors/privesc | 2 | allowPrivilegeEscalation |
| auditors/privileged | 2 | privileged 标志 |
| auditors/rootfs | 2 | readOnlyRootFilesystem |
| auditors/seccomp | 2 | seccomp profile |
| config | 1 | 配置文件解析 |
| internal/k8sinternal | 2 | k8s client 辅助 |
| internal/sarif | 2 | SARIF 报告生成 |
| internal/yaml | 1 | YAML 辅助 |
| pkg/fix | 1 | fixer 结果序列化 |

- `internal/test/test.go` 定义 MANIFEST_MODE（审计本地 YAML fixture，完全离线）与
  LOCAL_MODE（需 kubectl + kind 集群）。`AuditMultiple` 在 LOCAL_MODE 且
  `USE_KIND != "true"` 时直接返回 nil（静默跳过），因此离线环境 `go test ./...`
  全部可跑、LOCAL 用例自动跳过。上游 CI（.github/workflows/ci.yml + test.sh）使用
  `go test -race` + kind v1.20.15；`-race` 需要 cgo，与 CGO_ENABLED=0 冲突，本适配
  去掉 `-race`。
- 全部 21 个包在 build() 内按 E318/P017 范式执行：`go test -mod=mod -c` 编译到
  go-workspace/test-out、binary-sign-tool 自签名后回包源码目录 `-test.v
  -test.count=1` 运行（保留相对 fixture 路径）。

## 编译方案

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=mod \
GOPROXY=https://goproxy.cn,direct GOSUMDB=sum.golang.google.cn \
  go build -trimpath -mod=mod \
  -ldflags "-s -w -X github.com/Shopify/kubeaudit/cmd.Version=v0.22.2 -X github.com/Shopify/kubeaudit/cmd.Commit=92c3147 -X github.com/Shopify/kubeaudit/cmd.BuildDate=2026-09-23T00:00:00Z" \
  -o kubeaudit ./cmd
```

- 与 kubeconform 0.7.0 模板的最大 delta：上游**无 vendor/**，构建期先
  `go mod download`（GOPROXY=goproxy.cn）拉取模块闭包（k8s.io/api、apimachinery、
  client-go、apiextensions-apiserver、cert-manager、go-sarif/v2、logrus、cobra、
  testify、yaml.v3 及间接闭包，go.sum 1043 行），GOFLAGS 用 `-mod=mod` 而非
  `-mod=vendor`。
- 版本注入：上游 Makefile 经 build/ldflags.sh 注入 `-X cmd.Version/Commit/
  BuildDate`（ldflags.sh 依赖 `git describe`/`git rev-parse`，Makefile 对 go <
  1.22.1 $(error)——均绕开）。实际 `kubeaudit version` 输出来自
  `go:embed cmd/commands/VERSION`（内容 `0.22.2`）；ldflags 按固定值注入仅为
  Makefile 对齐（未知 -X 目标被链接器忽略，无副作用）。
- OHOS 上 GOOS 取 `linux`，产物经 `binary-sign-tool` 自签名后方可 execve；单遍
  `go build -o` 一次成型输出到 go-workspace/link-out（HMDFS mmap 链接限制，
  E124/E134/E166 模式），签名后拷入包 bin/。
- Go 工作目录（GOCACHE/GOMODCACHE/GOTMPDIR/链接输出/测试 ELF）路由到
  `/data/storage/el2/base/haps/entry/files/kubeaudit-conan-go/0.22.2`（可经
  `OHOS_GO_WORKDIR` 覆盖），规避 HMDFS 限制。

## test_package（OHOS 特有用例，非上游复用）

1. `version` 输出 `0.22.2`（验证 go:embed 在 OHOS 工具链下生效）
2. `--help` 退出码 0（cobra 在 OHOS 下正常）
3. `privileged -f bad.yml` 检出 `PrivilegedTrue` 且退出码 2（manifest 模式全链路
   + 上游默认 --exitcode 语义在 OHOS 上生效）
4. `privileged -f good.yml` 干净清单退出码 0
5. `autofix -f bad.yml -o` 将 `privileged: true` 重写为 `privileged: false`
6. （OHOS-only）产物 ELF 含 binary-sign-tool 写入的 `.codesign`/`.note.ohos` 签名节
   （未签名 ELF 会被 HarmonyOS execve 拒绝）
7. （OHOS-only）CGO_ENABLED=0 产物静态链接：无 PT_INTERP、无 DT_NEEDED（无
   glibc/musl 动态耦合）

## 源码修改

无源码修改，无 patches，纯 Go 编译。

## 运行时说明

- manifest 模式（`-f`）完全离线可用；cluster/local 模式需要 kubeconfig 与
  K8s API 网络可达，属运行环境条件，不影响构建与离线审计。
- CGO_ENABLED=0 使用纯 Go DNS 解析器（读 /etc/resolv.conf），符合 OHOS 环境。

## 验证结果（2026-09-23 真机回填）

- `go test -mod=mod`（21 包离线口径，`go test -c` 编译 → binary-sign-tool 签名 →
  回源码目录 `-test.v -test.count=1` 运行）：discovered=executed=passed=**379**，
  failed=0，skipped=0（64 个顶层 Test 展开含子测试共 379 例；LOCAL_MODE 用例在无
  kind 集群时按上游语义静默跳过，本轮 SKIP=0）。
- 逐包通过数（HMBS_GO_TEST_PKG）：`.` 10 / auditors/all 32 / apparmor 17 / asat 20 /
  capabilities 22 / deprecatedapis 10 / hostns 20 / image 11 / limits 10 / mounts 6 /
  netpols 19 / nonroot 75 / privesc 14 / privileged 14 / rootfs 14 / seccomp 16 /
  config 1 / internal/k8sinternal 15 / internal/sarif 7 / internal/yaml 42 / pkg/fix 4
  （全部 0 fail）。
- 证据：CI 日志中 `HMBS_UPSTREAM_TEST_RESULT` / `HMBS_GO_TEST_PKG` 标记与
  `upstream-go-test.log`（379 条 `--- PASS:`、0 条 `--- FAIL:`）。
- test_package 7/7 通过（--ohos 口径：version 嵌入 / help / PrivilegedTrue 检出+退出码
  2 / 干净清单退出码 0 / autofix 重写 / OHOS 签名节 / 静态链接无 INTERP 无 NEEDED），
  `HMBS_TEST_PACKAGE_RESULT` passed。
- 权威 CI：`zsh ci/conan/build_and_test.sh`，`CI_PACKAGES=archives/k/kubeaudit/0.22.2`、
  `CI_BRANCH=feat/kubeaudit-0.22.2`：L0/L1/L2/L4/L5 全 pass，Success 1/1（100%）。
  CI 对 conandata.yml 的 gh-proxy 镜像改写（E415 类原地改写）已还原，未带入候选。
