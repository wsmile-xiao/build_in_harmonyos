# akamai 编译笔记

## 基本信息

- 软件名: akamai
- 版本: v2.0.0
- 类型: go 工具 (Akamai CLI)
- 编译日期: 2026-08-05

## 源码信息

- 上游仓库: https://github.com/akamai/cli
- 源码SHA256: f9657d51f971ef6f65a6dd8f2f7791d78afd7e1065989ceb552f1701f5434927
- Go模块: github.com/akamai/cli/v2
- Go版本要求: 1.22 (go.mod)

## 编译过程

### 编译方式

使用 Go 交叉编译：
- Go工具: `go build -trimpath -ldflags "-s -w" -o akamai ./cli/main.go`
- 环境变量: CGO_ENABLED=0 GOOS=linux GOARCH=arm64
- GOPROXY: https://goproxy.cn (镜像加速)
- 静态二进制 (不使用 buildmode=pie, PIE在OHOS上导致段错误)

### 验证

- 二进制文件: `bin/akamai`
- 功能验证: `akamai --version` → "akamai version 2.0.0" ✅

## Conan 适配

### 配方信息

- package_type: application
- 构建系统: go (自定义 recipe, 非 autotools/cmake)
- 依赖: 无 Conan 级依赖 (Go 模块自管理)
- 产物: bin/akamai (ELF arm64, 静态二进制)

### 测试

- 上游测试: `go test ./...` (20+ 测试文件)
- 消费者测试: test_package/test.sh (smoke test: --version)

### 关键适配点

1. Go 工具链自动检测/下载 (Go SDK bootstrap)
2. ELF 签名 (OHOS 平台要求)
3. 静态二进制 (不使用 PIE, PIE在OHOS HMDFS上导致段错误)
4. GOPROXY 镜像设置 (goproxy.cn)
5. GOSUMDB 镜像 (sum.golang.google.cn)

## 备注

此软件原通过 go install 直接安装，现适配为 Conan 配方管理。

## 结束

最终状态: built (Conan 配方验证通过, W3 本地CI模拟通过)
