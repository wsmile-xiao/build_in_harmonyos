# brev-cli 编译笔记

## 编译信息
- 版本：v0.6.326
- 构建系统：Go + Makefile
- Go 版本：1.26.1
- 编译日期：2026-06-08

## 编译过程
1. 下载源码（使用 GitHub 加速器 ghfast.top）
2. Go build 编译（纯 Go，CGO_ENABLED=0）

## 特殊处理

### NVML 依赖问题
brev-cli 使用 NVIDIA NVML 库（go-nvml），该库依赖 CGO：
- 问题1：系统无 GCC，只有 clang
- 问题2：clang 编译失败（RTLD_DEEPBIND 问题）
- 问题3：CGO_ENABLED=0 不工作（NVML 类型未定义）

解决方案：
- 修改 gpu_nvml.go 构建标签：`//go:build (linux || windows) && nvml`
- 创建 gpu_stub.go stub 文件：`//go:build (linux || windows) && !nvml`
- 使用纯 Go 编译，禁用 NVML 功能

### Go 环境设置
- Go SDK 位于 ~/usr/local/go-1.26.1
- GOPROXY=https://goproxy.cn,direct
- GOSUMDB=sum.golang.google.cn

### 权限问题
编译成功后，二进制无法执行（permission denied）：
- 鸿蒙系统安全限制
- 需要 ELF 签名才能执行
- binary-sign-tool 签名失败（"not trust command"）
- 建议：发布预编译包时使用签名流程

## 编译命令
```bash
export PATH=~/usr/local/go-1.26.1/bin:$PATH
export GOROOT=~/usr/local/go-1.26.1
export GOPROXY=https://goproxy.cn,direct
export GOSUMDB=sum.golang.google.cn
export CGO_ENABLED=0
go build -o bin/brev ./main.go
```

## 文件修改
- pkg/cmd/register/gpu_nvml.go: 构建标签修改
- pkg/cmd/register/gpu_stub.go: 新增 stub 文件
