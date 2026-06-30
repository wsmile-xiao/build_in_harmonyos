# protoc-gen-go 1.36.11 适配笔记

## 编译环境
- 构建系统: Go (custom, go build)
- 编译日期: 2026-06-01
- 编译器: Go 1.24.2 (静态编译 CGO_ENABLED=0)
- 状态: published

## 编译步骤

protoc-gen-go 是 Go 语言的 protobuf 代码生成器插件，源码来自 protocolbuffers/protobuf-go 仓库。

1. 从 GitHub 下载 protobuf-go v1.36.11 源码（tar.gz）
2. 安装完整匹配的 Go 1.24.2 工具链（解决 GOROOT 版本不匹配问题）
3. 在源码 `cmd/protoc-gen-go` 目录下执行静态编译：
   ```bash
   cd $BUILD_SRC_DIR/cmd/protoc-gen-go
   TMPDIR=/data/storage/el2/base/cache \
   GOCACHE=/data/storage/el2/base/cache/go-build-clean \
   CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
   GOPROXY=https://goproxy.cn,direct \
   go build -ldflags="-s -w" -o protoc-gen-go .
   ```
4. ELF 签名后安装到 $DEFAULT_PREFIX/bin/protoc-gen-go

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 版本不匹配: compile 报 "go1.23.6 does not match go tool 1.24.2" | GOROOT 源码(1.23.6)与 go 二进制(1.24.2)版本不一致 | 从 golang.google.cn 下载完整 Go 1.24.2 安装包，设置 GOROOT 为新安装路径 |
| 2 | 新下载的 Go 二进制无法执行 | 未 ELF 签名（OpenHarmony 安全策略） | 使用 ohc-run.py sign-elf 签名所有 Go 工具二进制 |
| 3 | init-build SSL 证书验证失败下载源码 | OpenHarmony SSL 证书链不完整 | 手动 curl --insecure 下载 tarball，用 file:// URL 传入 init-build |
| 4 | Go linker mmap 在 HMDFS 上失败 | HMDFS 不支持 mmap 写操作 | 设置 TMPDIR=/data/storage/el2/base/cache，GOCACHE 同样指向此路径 |

## 源码修改

无补丁。protoc-gen-go 是纯 Go 项目，无需修改源码即可编译。

## 依赖版本

- Go 1.24.2 (编译工具链，从 golang.google.cn 下载)
- protobuf-go v1.36.11 源码 (go.mod 要求 go 1.23)

## 验证结果

```bash
$ protoc-gen-go --version
protoc-gen-go v1.36.11
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| protoc-gen-go | 5.8MB | ELF 静态可执行文件，已签名 |

## 注意事项

- Go 项目在 OpenHarmony 上必须使用 CGO_ENABLED=0 静态编译
- Go 安装包必须版本自洽（GOROOT 源码与 go 二进制版本一致），否则编译器报版本不匹配错误
- 所有 Go 工具二进制需 ELF 签名后才能在 OpenHarmony 上执行
- GOPROXY 使用 https://goproxy.cn,direct 加速模块下载
---

**编译结束**: 2026-06-01 19:08
**最终状态**: published
