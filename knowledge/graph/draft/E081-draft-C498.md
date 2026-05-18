# E081: Go 编译器无法在鸿蒙执行

## 错误现象

```bash
$ ~/tmp/go/bin/go version
zsh: permission denied: /storage/Users/currentUser/tmp/go/bin/go

$ /data/service/hnp/bin/binary-sign-tool sign -inFile ~/tmp/go/bin/go -outFile ~/tmp/go/bin/go.signed -selfSign 1
[Error] [sign_elf.cpp] [WriteCodeSignBlock] Failed to save 4K data to .codesign section
sign failed
```

## 根因分析

1. **鸿蒙 ELF 签名机制**: 所有 ELF 可执行文件必须经过签名才能执行
2. **Go 编译器限制**: Go 编译器二进制（约 11MB）无法被 binary-sign-tool 正确签名
3. **签名失败原因**: 可能是因为 Go 二进制文件过大或有特殊的段结构

## 影响范围

- 所有 Go 语言项目无法在鸿蒙上直接编译
- 包括但不限于：ngrok、frp、hugo、syncthing 等
- Go 项目的 bootstrap 编译也需要现有的 Go 编译器

## 解决方案

### 方案 A: 预编译 Go 编译器（推荐）

需要 cmd-pkgs 提供已签名的 Go 编译器预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- go 1.21.0
```

### 方案 B: 交叉编译

在其他平台（如 Linux x86_64）使用交叉编译为鸿蒙 arm64 编译 Go 项目：

1. 设置 GOOS=linux GOARCH=arm64
2. 编译生成静态二进制
3. 签名后传输到鸿蒙

### 方案 C: Go 源码 bootstrap（耗时）

1. 从 Go 源码编译需要 C 编译器支持的部分
2. 逐步构建完整的 Go 工具链
3. 这个过程非常复杂且耗时

## 验证方法

```bash
# 验证 Go 编译器可用
go version

# 验证签名成功
/data/service/hnp/bin/llvm-readelf -S ~/usr/local/bin/go | grep .codesign
```

## 关键发现

在编译 ngrok 1.7.1 时发现：
- ngrok 1.x 是纯 Go 项目（客户端和服务端都是 Go）
- Go 编译器下载成功但无法执行
- 签名工具签名 Go 失败

## 建议

1. 向 cmd-pkgs 添加预编译的 Go 编译器（已签名）
2. 优先使用交叉编译或预编译版本
3. 对于简单的 Go 项目，可以直接下载官方预编译版本（如果支持 arm64）

## 相关错误

- E051: syscall 未实现（Go 可能使用一些特殊的 syscall）
- E002: /tmp 只读（Go 默认使用 /tmp）