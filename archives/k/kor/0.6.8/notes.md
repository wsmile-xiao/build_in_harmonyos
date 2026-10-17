# kor 0.6.8 适配笔记

## 软件信息

- **软件名**: kor
- **版本**: 0.6.8
- **上游仓库**: https://github.com/yonahd/kor
- **标签**: v0.6.8
- **描述**: Kubernetes Orphaned Resources Finder — 发现 Kubernetes 集群中未使用的资源（ConfigMap、Secret、Service、Deployment 等 20+ 类）
- **许可证**: MIT
- **构建系统**: Go modules (go 1.25.0)
- **产物**: `kor` 静态可执行文件 (CGO disabled, stripped)

## 源码信息

- **源码包**: `https://github.com/yonahd/kor/archive/refs/tags/v0.6.8.tar.gz`
- **sha256**: `e651f3178e8c9cc1cd522661ac129b2518ed3fc981b0a9eebdf531e9c0b17b17`
- **压缩格式**: tar.gz

## 依赖判断

- kor 为**纯 Go** 项目：`go.mod` 要求 go 1.25.0，依赖（cobra/viper/client-go/prometheus 等）全部为 Go module，无 cgo、无 C/C++ 三方库依赖。
- cnb 制品仓无 `go/*` 配方 —— 无需提依赖任务；Go 工具链按知识图谱 E128/draft 指引在 build() 内自举下载并签名（见下）。

## 编译调试过程（本机真机实跑）

1. **Go 工具链自举（E128）**：本机无预装 Go，从 `golang.google.cn`（国内镜像）下载
   `go1.25.7.linux-arm64.tar.gz`，SHA-256 与官方值一致（`ba611a53...`）。
2. **工具链签名（E077 四步）**：对 `bin/` + `pkg/tool/linux_arm64/` 下 9 个 ELF 逐个
   `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1`
   → `chmod 0o755`。签名后 `go version` 实测输出 `go version go1.25.7 linux/arm64`。
3. **模块拉取**：`GOPROXY=https://goproxy.cn,direct` + `go mod download` 成功。
4. **编译**：`CGO_ENABLED=0 go build -trimpath -ldflags=-s -ldflags=-w -o kor main.go`
   成功，产物为 31MB 静态 arm64 ELF（`kor` 入口为仓库根 `main.go`，与上游 Makefile 一致）。
   GOCACHE/GOTMPDIR/链接器输出路由到 ext2（E166）。
5. **产物签名（E128）**：对 kor 二进制签名后，`kor version` 实测输出 `kor version: vdev`，
   `kor --help` 列出全部子命令（all/configmap/deployment/...）。
6. **上游测试验证**：`go test -c` 编译测试二进制 → 签名 → 直跑 `.test`（E128 绕法），
   `pkg/kor` 110 个用例全 PASS。

## 补丁说明

- **无补丁**：kor 纯 Go 且编译零报错，orig/work 无源码差异（仅 `.edit-tracker.json`），
  `conandata.yml` 的 `patches: []`。

## 交付物清单

- `conanfile.py`（主配方）：自举签名 Go → 编译 → 签名产物 → package bin/kor
- `test_package/conanfile.py`：冒烟测试（kor version）+ 上游 go test 套件（HMBS marker）
- `test_package/test.sh`、`test_package/MANIFEST.yml`
- `commands.json`、`manifest.yaml`、`conandata.yml`
- `reports/test-report.md`、`packaging/*.tar.gz`

## 结束标记

最终状态: published

## 补充说明

- kor 上游测试 120 个用例（pkg/kor 110 + pkg/filters 3 + pkg/utils 7）全部 hermetic：
  pkg/kor 用 k8s fake clientset，pkg/utils/slack_test.go 用 httpmock（注册 mock responder，
  不真发网络请求），无真实集群连接、无外部网络依赖，全部可离线运行。
- 与 tlsx 先例差异：kor 需要 go ≥ 1.25.0（tlsx 用 1.24.0），入口为根目录 `main.go`
  （tlsx 为 `./cmd/tlsx`），测试包无上游固有 `t.Skip`，无需排除任何包。
