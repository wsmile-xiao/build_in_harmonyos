# ali 0.8.0 — 适配笔记

> 档案创建时间: 2026-09-04
> 最后更新: 2026-09-04
> 状态: built
> 适配路径: 路径 A（基础适配）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ali |
| 版本 | 0.8.0 |
| 上游仓库 | https://github.com/nakabonne/ali |
| 构建系统 | Go modules (custom) |
| 许可证 | MIT |
| 源码 | https://github.com/nakabonne/ali/archive/refs/tags/v0.8.0.tar.gz |
| SHA256 | faf94ef7e0daa6d51b7064dd9757d4216168b19ed03c145ebf30e18f99fc81ad |
| Go 版本 | 1.24.5 |

## 二、适配要点

### Go 工具链自举
- OHOS 真机未预装 Go（E250），配方在 build 前通过 `_ensure_go_toolchain()` 自动下载官方 Go 1.24.5 二进制包
- 支持 arm64 / amd64 双架构，优先使用 `golang.google.cn` 镜像，回退 `mirrors.aliyun.com` 与 `dl.google.com`
- 下载后对 `go`, `gofmt` 及 `pkg/tool/linux_*/*` 下全部 ELF 用 `binary-sign-tool` 签名（E128/E318）

### HMDFS 规避
- Go linker 的最终输出不能落在 HMDFS（E051），链接阶段输出到 `$OHOS_GO_WORKDIR/link-out`（`/data/storage/el2/...`）
- `TMPDIR` / `GOTMPDIR` / `GOCACHE` / `GOMODCACHE` 全部重定向到非 HMDFS 工作区

### 上游测试
- 上游测试命令：`go test -v -count=1 -race ./...`（Makefile `make test`）
- OHOS 上测试 ELF 需签名后才能执行，通过 `go test -exec ohos-test-exec.sh` wrapper 在执行前自动签名
- 测试统计：顶层 `Test*` 共 28 个，涵盖 main / attacker / export / gui，各包大量 table-driven subtests
- 详见 `test_package/MANIFEST.yml` 声明

### 版本注入
- goreleaser 的 ldflags 为 `-X main.version={{.Version}}`，配方对齐为 `-X main.version=v0.8.0`
- `ali --version` 输出 `version=v0.8.0`，与上游发布一致

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| (无) | Go 源码在 OHOS 上可直接编译，无需补丁 | - | 无补丁 |

## 四、编译命令
```bash
# 探索性编译（复现 conan 流程）
go mod download
go build -trimpath -ldflags "-s -w -X main.version=v0.8.0" -o bin/ali .
go test -v -count=1 ./...

# Conan 验证
conan create archives/a/ali/0.8.0 --user=gyccc --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 五、验证
- 本地需在 HarmonyOS aarch64 真机预检通过后合入
- `ali --version` / `ali --help` 均可执行

## 六、已知限制
- GUI 运行需要终端（termdash），headless 环境仅测试不启动 GUI
- `GOTOOLCHAIN=local` 强制使用自举 Go 1.24.5，避免自动下载更新版本

## 七、结束记录
- 最终状态: built
- 结束时间: 2026-09-04
