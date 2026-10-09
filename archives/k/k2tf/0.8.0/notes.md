# k2tf 0.8.0 — 适配笔记

> 档案创建时间: 2026-09-29
> 最后更新: 2026-09-29
> 状态: built（待真机预检通过后 published）
> 适配路径: 路径 A（基础适配，Go CLI 工具）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | k2tf |
| 版本 | 0.8.0 |
| 上游仓库 | https://github.com/sl1pm4t/k2tf |
| 构建系统 | Go modules (custom) |
| 许可证 | MPL-2.0 |
| 源码 | https://github.com/sl1pm4t/k2tf/archive/refs/tags/v0.8.0.tar.gz |
| SHA256 | 9efdac448a99dbdda558eb93b63ed0b3ccabbac43c14df21ef3ba9bd402a4003 |
| Go 版本 | 1.24.5（k2tf go.mod 要求 >= 1.22） |

## 二、适配要点

### 工具性质
- k2tf 是将 Kubernetes YAML 对象转换为 Terraform HCL 配置的 CLI 工具（Go）
- 主包在模块根目录 `main.go`，构建产物为单个 `k2tf` 可执行文件
- 上游 `make test` = `go build -v && go test -v ./...`

### Go 工具链自举
- OHOS 真机未预装 Go（E250），配方在 build 前通过 `_ensure_go_toolchain()` 自动下载官方 Go 1.24.5 二进制包
- 支持 arm64 / amd64 双架构，优先使用 `golang.google.cn` 镜像，回退 `mirrors.aliyun.com` 与 `dl.google.com`（与 ali/0.8.0 已发布配方同一套 sha256，真机已验证）
- 下载后对 `go`, `gofmt` 及 `pkg/tool/linux_*/*` 下全部 ELF 用 `binary-sign-tool` 签名（E128/E318/E250）

### HMDFS 规避
- Go linker 的最终输出不能落在 HMDFS（E051），链接阶段输出到 `$OHOS_GO_WORKDIR/link-out`（`/data/storage/el2/...`）
- `TMPDIR` / `GOTMPDIR` / `GOCACHE` / `GOMODCACHE` 全部重定向到非 HMDFS 工作区

### 依赖拉取
- k2tf 无 `vendor/` 目录，依赖（k8s.io/api、terraform-plugin-sdk、hcl/v2 等）需经 GOPROXY 拉取
- 配方 `GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct`（ali/0.8.0 真机已验证可拉取）

### 上游测试
- 上游测试命令：`go test -v -count=1 ./...`（对应 Makefile `make test`）
- 测试文件 5 个、顶层 `func Test*` 10 个，含大量 table-driven subtest
- OHOS 上测试 ELF 需签名后才能执行，通过 `go test -exec ohos-test-exec.sh` wrapper 在执行前自动签名
- 统计口径：逐行统计 `go test -v` 输出的 `--- PASS: / --- FAIL: / --- SKIP:`（单一确定性数据源）
- 本地 Linux amd64 实测 `go test -v -count=1 ./...`：PASS=92 FAIL=0 SKIP=0（discovered=92）
- `build()` 运行真实 `go test -v -count=1 ./...` 后写 `HMBS_UPSTREAM_TEST_RESULT`，并把结果持久化到包内 `res/hmbs_upstream.json`；`test_package` 每次运行从包内读取同一份真实结果重放（cache-hit 时 build() 被跳过也能拿到），持久化结果缺失时如实标记 failed 并列出已搜路径，绝不伪造计数（HMBS「宁缺毋假」规则）

### 版本注入
- main.go 构建时变量 `version/commit/date`，`k2tf -v` 打印 `k2tf version: %s`
- 配方 ldflags `-X main.version=v0.8.0`，test.sh 冒烟校验输出含 `0.8.0`

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| (无) | Go 源码在 OHOS 上可直接编译，无需补丁 | - | 无补丁 |

## 四、编译命令
```bash
# 探索性编译（本机复现）
GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct go mod download
go build -trimpath -ldflags "-s -w -X main.version=v0.8.0" -o bin/k2tf .
go test -v -count=1 ./...

# Conan 验证（真机）
conan create archives/k/k2tf/0.8.0 --user=gyccc --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 五、验证
- 本机 Linux amd64 `go test -v -count=1 ./...` 全绿（92 用例），实际以 HarmonyOS aarch64 真机预检为准
- `k2tf -v` / `k2tf --help` 可执行

## 六、已知限制
- k2tf 为纯转换工具，不依赖网络/图形，测试在 OHOS 上可直接运行
- `GOTOOLCHAIN=local` 强制使用自举 Go 1.24.5，避免自动下载更新版本

## 七、结束记录
- 最终状态: built（待预检）
- 结束时间: 2026-09-29
