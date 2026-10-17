# kubeconform 0.7.0 适配笔记

## 基本信息

- **软件**: kubeconform — FAST Kubernetes manifests validator，支持 Custom Resources
- **版本**: 0.7.0（首次适配，无后缀）
- **上游**: https://github.com/yannh/kubeconform（tag v0.7.0，2025-05-12）
- **许可证**: Apache-2.0
- **构建系统**: Go custom（`go build ./cmd/kubeconform`）
- **Go 要求**: go.mod 声明 `go 1.24`，配方使用 Go 1.24.0 工具链
- **源码**: `https://github.com/yannh/kubeconform/archive/refs/tags/v0.7.0.tar.gz`
- **SHA256**: `9cb00e6385346c9de21e8fe318a4ec9854a8c7165d08b10b20ed32e28faef9a8`（已下载实测约 1MB 归档并验算）
- **申请人**: gcw_6a3w2yXz，队伍：来都来了

## 上游测试审计（2026-09-18，基于 v0.7.0 源码包实测解包统计）

`go test ./...` 覆盖 6 个包、12 个 `_test.go` 文件、20 个顶层 `Test` 函数：

| 包 | 文件数 | Test 函数 |
|----|--------|-----------|
| pkg/config | 1 | TestSkipKindMaps, TestFromFlags（2） |
| pkg/loader | 1 | TestHTTPURLLoader_Load, TestHTTPURLLoader_Load_Retries（2，httptest 本地 mock，无外部网络） |
| pkg/output | 5 | TestJSONWrite, TestJunitWrite, TestPrettyTextWrite, TestTapWrite, TestTextWrite（5） |
| pkg/registry | 1 | TestSchemaPath（1，纯模板拼接） |
| pkg/resource | 3 | TestIsYamlFile, TestIsJSONFile, TestFindResourcesInReader, TestSignatureFromBytes, TestSignatureFromMap, TestResources, TestFromStream（7） |
| pkg/validator | 1 | TestValidate, TestValidationErrors, TestValidateFile（3，内存 mock registry） |
| **合计** | **12** | **20** |

全部为离线用例（httptest 本地 server、内存 mock schema、无外部下载），可在真机完整执行。
`acceptance.bats` / `acceptance-nonetwork.bats` 需要 docker + bats + 在线 schema 下载，真机与 CI 均不具备条件，未运行（见 PR 补充说明）。

## 编译方案

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=vendor \
  go build -trimpath -mod=vendor \
  -ldflags "-s -w -X main.version=v0.7.0" \
  -o kubeconform ./cmd/kubeconform
```

- 版本注入路径为 `main.version`（与 `.goreleaser.yml` 的 `-X main.version={{.Tag}}` 一致，`kubeconform -v` 打印 `v0.7.0`）。
- 上游自带 `vendor/` 目录，`-mod=vendor` 离线构建，不跑 `go mod download`，不依赖 GOPROXY 网络。
- OHOS 上 GOOS 取 `linux`（与 dasel/buildifier 等 Go 配方一致），产物经 `binary-sign-tool` 自签名后方可 execve。
- Go 工作目录（GOCACHE/GOTMPDIR/链接输出）路由到 ext2 分区或 `OHOS_GO_WORKDIR`，规避 HMDFS mmap/签名问题（E166/E128 模式）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败：`invalid path 'archives/g/gama/...patch??'` | 上游某文件名尾带回车符，Windows 保护性拦截 | `git config core.protectNTFS false` 后完整检出；与本配方无关 |
| 2 | test_package 在线 schema 不可用风险 | kubeconform 默认从 github 下载 schema，真机/CI 网络受限 | test_package 自带本地 JSON schema（`schemas/testkind-v1.json`），`-schema-location` 指向本地模板，全离线验证 |

## 源码修改

无源码修改，无 patches，纯 Go 编译。

## 验证结果（待真机预检回填）

- `go test -mod=vendor -v ./...`：待真机回填（目标 20/20）。
- test_package（5 项：version/help/valid/invalid/stdin）：待真机回填（目标 5/5）。
- 证伪设计：invalid 用例断言输出含 `Invalid: 1` 且退出码非零；version 用例断言含 `v0.7.0`；非空文本 grep，非单纯退出码判断。

---

**编写日期**: 2026-09-18
**当前状态**: 未提交工作树，待 HMBS 真机预检
