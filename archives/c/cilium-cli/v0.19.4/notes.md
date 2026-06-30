# cilium-cli v0.19.4 适配笔记

## 编译环境
- 构建系统: go (CGO_ENABLED=0 static build)
- 编译日期: 2026-06-01
- 编译器: Go 1.26.3 (手动下载安装，本地 Go 1.24.2 不满足 go.mod 的 go 1.26.0 要求)
- 状态: built

## 编译步骤

1. 恢复已初始化骨架（archives/c/cilium-cli/v0.19.4/）
2. 下载 Go 1.26.3 (从 https://go.dev/dl/go1.26.3.linux-arm64.tar.gz)
3. 解压 Go 到 ~/tmp/go1.26.3/，对所有 ELF 二进制签名 (`ohc-run.py sign-elf`)
4. 设置环境变量：
   ```bash
   export PATH=~/tmp/go1.26.3/go/bin:$PATH
   export GOROOT=~/tmp/go1.26.3/go
   export GOPATH=/storage/Users/currentUser/go
   export GOTOOLCHAIN=local
   export CGO_ENABLED=0
   export GOOS=linux
   export GOARCH=arm64
   export GOPROXY=https://goproxy.cn,direct
   ```
5. 编译：
   ```bash
   go build -ldflags="-s -w -X 'github.com/cilium/cilium/cilium-cli/defaults.CLIVersion=v0.19.4'" -o cilium ./cmd/cilium
   ```
6. 安装到 staging: `cp cilium $TEST_PREFIX/$DEFAULT_PREFIX/bin/cilium`
7. 签名: `ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/cilium`
8. 安装到本地: `cp cilium $DEFAULT_PREFIX/bin/cilium` + sign-elf

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 1.24.2 不满足 go.mod 的 go 1.26.0 要求 | cilium-cli v0.19.4 使用了 Go 1.26 新增的 std 包 (crypto/pbkdf2, crypto/hkdf, crypto/sha3, weak) | 下载安装 Go 1.26.3，对所有 ELF 签名后使用 |
| 2 | Go 工具链二进制执行 permission denied | 下载的 Go 二进制未签名（鸿蒙 ELF 签名要求） | `ohc-run.py sign-elf` 签名所有 Go 工具链 ELF |
| 3 | 修改 vendor/modules.txt 版本约束后编译报 invalid -lang | sed 替换导致 vendor/modules.txt 中版本号格式错误（如 go 1.26.0.0） | 恢复原始 vendor/modules.txt，直接用 Go 1.26.3 编译 |

## 依赖版本

- Go 1.26.3 (需单独下载，本地 Go 1.24.2 不兼容)
- vendor 目录已包含所有依赖（使用 -mod=vendor 模式）

## 验证结果

```bash
$ cilium version
cilium-cli: v0.19.4 compiled with go1.26.3 on linux/arm64
cilium image (default): v1.19.3
cilium image (stable): v1.19.4
cilium image (running): unknown. Unable to obtain cilium version. Reason: kubernetes cluster unreachable
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cilium | ~143MB | 静态链接 ELF 二进制 (CGO_ENABLED=0) |

## 注意事项

- cilium-cli 依赖 Go >= 1.26.0，项目使用了 Go 1.26 新增的 std 包
- 二进制名称为 `cilium`（不是 `cilium-cli`），Makefile TARGET=cilium
- 编译产出为纯静态二进制，无外部依赖
- kubernetes cluster 不可达属于正常现象（测试环境无 k8s 集群）
---

**编译结束**: 2026-06-01 20:09
**最终状态**: built
