# ytt 0.55.1 — 适配笔记

> 档案创建时间: 2026-09-18
> 最后更新: 2026-09-18
> 状态: built
> 适配路径: 路径 A（基础适配）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ytt |
| 版本 | 0.55.1 |
| 上游仓库 | https://github.com/carvel-dev/ytt |
| 构建系统 | Go modules (custom) |
| 许可证 | Apache-2.0 |
| 源码 | https://github.com/carvel-dev/ytt/archive/refs/tags/v0.55.1.tar.gz |
| SHA256 | 4591a3b659dba43a6e8b3d5dd2ef9cb03011868bacab66684c0cfb6b7a698eb1 |
| Go 版本 | 1.26.3 |

## 二、上游源码审计
- 入口包：`./cmd/ytt`（`cmd/ytt/ytt.go` 调用 `pkg/cmd` 命令树），构建产物为单体 `ytt` 可执行文件。
- 上游构建脚本 `hack/build.sh`：`CGO_ENABLED=0`，`LDFLAGS="-X carvel.dev/ytt/pkg/version.Version=$VERSION"`，`go build -trimpath -o ytt ./cmd/ytt/...`。配方对齐为 `-s -w -X carvel.dev/ytt/pkg/version.Version=0.55.1`。
- 上游测试入口 `hack/test-all.sh`：`go test ./...` 外加 `examples/integrating-with-ytt/internal-templating` 的 `go test ./...` 契约测试。
- 测试规模（源码审计，解包 v0.55.1 归档实数）：33 个 `_test.go` 文件，共 158 个 `Test*`/`Example*` 顶层函数；`pkg/yamltemplate/filetests` 与 `pkg/validations/filetests` 下共 220 个 `.tpltest` 数据驱动 fixture（由 `template_test.go` 等通过 filetests 运行器执行）；`test/e2e` 含 12 个测试函数，通过 `exec "../../ytt"` 调用源码根已构建二进制。
- `pkg/version/version.go` 默认 `Version = "develop"`，靠 ldflags 注入版本号；`ytt version` 用于 test_package 冒烟验证。

## 三、适配要点

### Go 工具链自举
- OHOS 真机未预装 Go，配方在 build 前通过 `_ensure_go_toolchain()` 自动下载官方 Go 1.26.3 二进制包（与 `go.mod` 的 `go 1.26.3` 对齐）。
- 支持 arm64 / amd64 双架构，优先使用 `golang.google.cn` 镜像，回退 `dl.google.com`。
- 下载后对 `go`、`gofmt` 及 `pkg/tool/linux_*/*` 下全部 ELF 用 `binary-sign-tool` 签名。
- `GOTOOLCHAIN=local` 强制使用自举 Go，避免自动下载更新版本；`GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct`。

### HMDFS 规避
- Go linker 的最终输出不能落在 HMDFS，链接阶段输出到 `$OHOS_GO_WORKDIR/link-out` 后签名再拷贝到 `bin/`。
- `TMPDIR` / `GOTMPDIR` / `GOCACHE` / `GOMODCACHE` 全部重定向到非 HMDFS 工作区。

### 上游测试
- 上游测试命令：`go test -v -count=1 ./...`（`hack/test-all.sh`）。
- OHOS 上测试 ELF 需签名后才能执行，通过 `go test -exec ohos-test-exec.sh` wrapper 在执行前自动签名。
- e2e 依赖源码根 `ytt` 二进制：`build()` 在编译后把已签名二进制拷贝到 `source_folder/ytt` 再跑测试。
- `build()` 解析 `--- PASS/FAIL/SKIP` 行输出 `HMBS_UPSTREAM_TEST_RESULT`，并持久化到 `res/hmbs_upstream.json` 供 test_package 在缓存命中时重发。
- 详见 `test_package/MANIFEST.yml` 声明。

### 版本注入
- 上游 ldflags 为 `-X carvel.dev/ytt/pkg/version.Version=$VERSION`，配方对齐为 `-X carvel.dev/ytt/pkg/version.Version=0.55.1`。
- `ytt version` 输出对应版本，与上游发布一致。

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| test/e2e/assets/test_pipe_stdin.sh | 外层 `diff <(...)` 进程替换在 OHOS 只读 /tmp 下建临时文件失败（`can't create temporary file /tmp/sh*.tmp`），致 TestPipes 2 子用例+父用例共 3 个 FAIL；仅把外层比较改经 `$TMPDIR` 临时文件，管道 stdin 意图与断言不变 | patches/0001-e2e-pipe-tests-tmpdir.patch | portability |
| test/e2e/assets/test_pipe_redirect.sh | 同上；保留内层 `<(...)`（被测特性：ytt 读取 /dev/fd 管道），仅外层 diff 改经 `$TMPDIR` 临时文件；shebang 改为 `env bash` 以适配真机 bash 路径 | patches/0001-e2e-pipe-tests-tmpdir.patch | portability |

## 五、编译命令
```bash
# 探索性编译（复现 conan 流程）
go mod download
go build -trimpath -ldflags "-s -w -X carvel.dev/ytt/pkg/version.Version=0.55.1" -o bin/ytt ./cmd/ytt
go test -v -count=1 ./...

# Conan 验证
conan create archives/y/ytt/0.55.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 六、验证
- 本地需在 HarmonyOS aarch64 真机预检通过后合入。
- `ytt version` / `ytt --help` 均可执行；test_package 另覆盖基础模板渲染与 `--data-value` 覆写。

## 七、已知限制
- `examples/integrating-with-ytt/internal-templating` 契约测试需联网整理 go.mod，`go test ./...` 主套件已覆盖核心能力，契约测试不单独跑。
- e2e 用例通过已签名 staged 二进制执行，与上游 `hack/build.sh` 先构建再测试的顺序一致。

## 八、结束记录
- 最终状态: built
- 结束时间: 2026-09-18
