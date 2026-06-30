# kdoctor v0.2.2 适配笔记

## 编译环境
- 构建系统: go (go1.26.4 linux/arm64)
- 编译日期: 2026-06-21
- 编译器: clang/clang++ (for CGO if needed, CGO_ENABLED=0)
- 状态: published

## 编译步骤

```bash
source .build-context-kdoctor-v0.2.2
cd $BUILD_SRC_DIR
export GOPROXY=https://goproxy.cn
export CGO_ENABLED=0
go build -mod=vendor -o kdoctor ./cmd/agent/
mkdir -p $TEST_PREFIX/bin
cp kdoctor $TEST_PREFIX/bin/
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
cp kdoctor $TEST_PREFIX$DEFAULT_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `undefined: runtime_cyclesPerSecond` 和 `runtime_expandFinalInlineFrame` | vendored godeltaprof 包的 stub.go 有 `!go1.21` 构建标签，Go 1.21+ 不编译导致符号未定义 | 新建 `stub_go121.go`（`//go:build go1.21`），提供相同的 `//go:linkname` 声明 |

## 源码修改

- 新增文件: `vendor/github.com/pyroscope-io/godeltaprof/internal/pprof/stub_go121.go`
  - 为 Go 1.21+ 提供缺失的 `runtime_expandFinalInlineFrame` 和 `runtime_cyclesPerSecond` linkname 声明
  - 补丁: `0001-vendor-github.com-pyroscope-io-godeltaprof-internal-pprof-stub_go121.go.patch`

## 依赖版本
- Go: go1.26.4 linux/arm64
- 无外部 C 依赖（CGO_ENABLED=0，纯 Go 静态二进制）

## 验证结果

```bash
$ file kdoctor
kdoctor: ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked

$ kdoctor --help
# 输出 kdoctor 帮助信息和配置项，正常运行
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kdoctor-v0.2.2-ohos-aarch64.tar.gz | 46MB | 预编译包（strip 后） |
| kdoctor-v0.2.2-ohos-aarch64-debug.tar.gz | 18MB | 调试符号包 |

## 注意事项

- kdoctor 是 Kubernetes 网络诊断工具，需要 K8s 集群环境才能完整运行
- `--version` 命令不返回标准版本号（该工具使用 `--help` 展示信息）
- G0 干净构建验证因 Go 项目无 configure 步骤而跳过（预期行为）
- G2 功能验证中 `--version` 返回非零退出码（kdoctor 不支持该参数），但 `--help` 正常工作
