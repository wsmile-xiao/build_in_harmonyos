# k3d 5.9.0 适配笔记

## 轮次 1（2026-09-29）：初始工作树搭建（创建 PR 前）

### 定位
k3d 5.9.0 是纯 Go CLI（`github.com/k3d-io/k3d/v5`，MIT），一个在 Docker 里
跑 k3s 的轻量 Kubernetes 开发集群工具。go.mod 与 go.work 均要求
`go 1.26.3`。v5.9.0 源码自带 `vendor/`（上游 Makefile `GOFLAGS=-mod=vendor`），
构建与测试完全离线。

### 本轮背景
hmbs 真机预检在 evidence 阶段报「无法读取当前 archive 代码树，不能启动真机
预检」——`archives/k/k3d/5.9.0/` 工作树不存在。本轮产出完整 k3d archive
（保持未提交，等待 hmbs 同步并复跑 preflight）。

### 本轮产出（全部保持未提交）
- `conanfile.py`：Conan 2.x 配方（`package_type=application`，Go 构建）：
  - 探测设备 go 工具链（which → HNP_GO/HNP_GOROOT → find 扫描），打印
    `[go-toolchain-probe]` 机器证据表；
  - Go >= 1.26 时直接用；缺失/过旧时从 aliyun镜像 bootstrap go1.26.3
    （sha256 核对官方 go.dev 哈希，`go/bin` 与 `go/pkg/tool` 全部 ELF 用
    binary-sign-tool 签名，vibecheck/1.7.7 先例）；
  - workspace 模式（不设 GOWORK=off）+ `-mod=vendor`：`go build
    -mod=vendor -trimpath -ldflags "-X .../version.Version=v5.9.0" -o k3d .`
    （链接输出放非 hmdfs work root 的 link-out/ 规避 OHOS linker mmap 失败）；
  - build() 内先跑上游 `go test -v -mod=vendor ./...`（-p 1，OHOS 下 -exec
    包装器先签名测试二进制再执行），从 stdout 解析 `--- (PASS|FAIL|SKIP):`
    顶层行，输出 HMBS_UPSTREAM_TEST_RESULT（discovered=23）。
- `conandata.yml`：官方 GitHub tarball v5.9.0 + sha256 969cce82...（本机实测），
  gh-proxy 镜像置前、官方置后；`go_toolchain` go1.26.3（amd64/arm64，aliyun）。
- `test_package/`：`test.sh` 冒烟（k3d version 断言 v5.9.0 + `--help`），
  conanfile.py 输出 HMBS_TEST_PACKAGE_RESULT（discovered=2）；MANIFEST.yml
  声明 upstream_test_total=23、go_test_functions 口径、完整上游测试审计。
- `manifest.yaml` / `notes.md`：版本级元数据 + 上游测试审计。
- 软件级：`manifest.yaml`、`README.md`、`commands.json`。

### 上游测试（23 个 Test*，统计口径 = go test 函数计数）
源码审计确认 `go test -v ./...`（根模块 workspace 模式）共 23 个顶层 Test*
函数，分布 13 个 *_test.go / 7 个包。逐一核点：
- cmd/util/ports_test.go(1)、pkg/client/tools_test.go(2)、
  pkg/client/registry_test.go(1)、pkg/config/*(14)、
  pkg/runtimes/docker/translate_test.go(1)、pkg/util/yaml_test.go(2)、
  version/version_test.go(2)。

**唯一外网依赖用例**：`TestGetK3sVersion`（version/version_test.go）以非空
channel 调 `GetK3sVersion("v1.20")`，实时访问 update.k3s.io 拉取最新 k3s
版本并与 `v1.20.*` 正则比对。若真机沙箱无法出网到 update.k3s.io，它会如实
FAIL（t.Fatal）。**不**打桩不删断言：由 HMBS 标记的 failed/gaps 如实承载，
status=incomplete 或 failed，绝不伪装 100%。

其余 22 个均为自包含纯逻辑单元测试（config/yaml/translate/registry/ports/
tools；Test_findImages 仅需可写 TMPDIR，translate/registry 的 Docker 常量
不建立真实 docker 连接）。

### 关键决策
- **依赖承载**：k3d 依赖极其庞大（k8s client-go / docker SDK / gRPC /
  OpenTelemetry），但全部经仓库 vendor/ 离线承载，`-mod=vendor` 使构建与测试
  均不依赖 GOPROXY 拉取（无 test-only 依赖缺口问题）。
- **workspace 模式**：vendor/modules.txt 含 tools/docgen 子模块依赖，必须在
  go.work workspace 模式下编译；若设 GOWORK=off 报 "inconsistent vendoring"
  （本机实测复现），故配方不覆写 GOWORK。

### 下一步
工作树保持未提交，等待 hmbs 同步到真机复跑 preflight：
1. `conan create` 跑通工具链 bootstrap + `go build`；
2. `go test -v ./...` 真机真实执行 23 个上游用例 → HMBS_UPSTREAM_TEST_RESULT；
3. test_package 冒烟 2 条 → HMBS_TEST_PACKAGE_RESULT；
4. 真机全部门禁通过后由 HMBS 统一提交推送并生成 PR 正文。


### 轮次 1 收尾：同步 + 验证 + PR 正文草稿（2026-09-29）
- 同步上游 main 至 60ed50249（feat/k3d-5.9.0 分支已 reset 到最新 upstream/main，工作树未提交保留）。
- 本机实测校验：官方源码 tarball sha256 = 969cce82...（与 conandata.yml 一致）；go.mod/go.work 均 go 1.26.3；根模块 + ./docgen + ./tools 三模块 workspace（docgen/tools 无 _test.go，`go test ./...` 仅执行根模块 23 个测试）；审计确认 23 个 `func Test`（13 个 *_test.go），逐个函数名与 test_package/MANIFEST.yml 完全一致。
- 唯一外网用例 TestGetK3sVersion（version/version_test.go）以非空 channel 调 GetK3sVersion("v1.20")，实时访问 update.k3s.io；TestFetchLatestK3sVersion 用 httptest 本地 mock。已核点。
- 已写完整 PR 正文草稿至 .hmbs/pr-body.md（积分赛事模板全章节，填尽所有非测试事实；适配路径=路径 A 基础适配；测试用例数均标注「待真机 evidence 轮实测填写」，不含 {{...}}/请填写占位）。
