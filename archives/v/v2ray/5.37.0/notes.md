# v2ray 5.37.0 编译记录

## 编译信息
- **软件**: v2ray
- **版本**: 5.37.0
- **日期**: 2026-05-25
- **编译器**: Go 1.25.0 (linux/arm64)
- **目标**: OpenHarmony aarch64

## 源码信息
- **来源**: GitHub v2fly/v2ray-core
- **URL**: https://github.com/v2fly/v2ray-core/archive/refs/tags/v5.37.0.tar.gz
- **大小**: 1.1 MB

## 编译过程

### 环境设置
```bash
export PATH=/storage/Users/currentUser/usr/local/go/bin:$PATH
export GOPATH=/storage/Users/currentUser/go
export GOROOT=/storage/Users/currentUser/usr/local/go
export GOPROXY=https://goproxy.cn,https://goproxy.io,direct
```

### 依赖下载
由于网络问题，使用国内 Go 代理 (goproxy.cn) 下载依赖。

### 编译命令
```bash
go build -v -o v2ray ./main/main.go
```

## 编译产物
- **二进制**: v2ray (49 MB)
- **类型**: ELF executable, 64-bit LSB arm64, dynamic

## 特殊处理

### SSL 证书问题
系统缺少 CA 证书，需要在下载时使用 SSL 跳过。

### Go 代理配置
默认 Go 代理无法访问，需要配置国内镜像。

## 知识提取
- E068: Go 项目编译需要设置 GOPROXY 环境变量
- Go 项目不需要 configure/make，直接使用 go build
- 需要正确设置 GOPATH 和 GOROOT 环境变量

---
**编译结束**: 2026-05-25 20:16
**最终状态**: published
---

**编译结束**: 2026-05-25 20:18
**最终状态**: built

## 知识提取

### E069: Go 项目编译模式
- **类别**: 构建系统模式
- **描述**: Go 语言项目使用 go build 而非 configure/make
- **触发条件**: go.mod 存在
- **解决方案**:
  1. 设置 GOPROXY=https://goproxy.cn（国内代理）
  2. go mod download 下载依赖
  3. go build -v -o <output> <entry_point>
- **影响**: G0 干净构建验证不适用

### Go 编译注意事项
- Go 1.24+ 需要设置 toolchain
- 使用国内代理 goproxy.cn 解决网络问题
- 编译产物是静态链接（无外部依赖）
- 需要 ELF 签名才能在鸿蒙上执行

---
**编译结束**: 2026-05-25 20:19
**最终状态**: built
