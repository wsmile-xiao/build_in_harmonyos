# cloudfoundry-cli 8.18.3 适配笔记

## 编译环境
- 构建系统: Go (go.mod)
- 编译日期: 2026-08-06
- 编译器: Go 1.25.0 (linux/arm64)
- 状态: built

## 编译步骤

### 1. 环境准备
- 安装 Go 1.25.0 (linux-arm64) 从 go.dev
- strip 并 ELF 签名所有 Go SDK 二进制（go, gofmt, 及 7 个工具链工具）
- 配置 conan remote ohpcd 和 ohos-aarch64 profile

### 2. 源码获取
- GitHub 在鸿蒙设备上不可达，使用 gh-proxy.com 镜像下载源码 tarball
- SHA256: b1d752410595f21838eafe56887e57d31e1dd212db2d77137d606d5a85039bf0

### 3. 补丁应用
- 0001-go.mod.patch: 将 go.mod 中的 `go 1.26.2` 降至 `go 1.25.0`
- 原因: Go 1.26.x 在鸿蒙上不可用（ELF 签名问题），Go 1.25.0 可用

### 4. 编译
```bash
export GOROOT=~/usr/local/go
export PATH=$GOROOT/bin:$PATH
export GOPROXY=https://goproxy.cn,direct
export GOTOOLCHAIN=local
export CGO_ENABLED=0
export TMPDIR=/data/storage/el2/base/cache
export GOCACHE=/data/storage/el2/base/cache/go-cache
go build -trimpath -ldflags "-s -w -X code.cloudfoundry.org/cli/v8/version.binaryVersion=8.18.3" -o cf .
```

### 5. 签名
```bash
strip cf
binary-sign-tool sign -selfSign 1 -inFile cf -outFile cf.signed -signAlg SHA256withECDSA
mv cf.signed cf
chmod 755 cf
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 不可达 | 鸿蒙设备网络限制 | 使用 gh-proxy.com 镜像下载 |
| 2 | Go 二进制 Permission denied | ELF 未签名 | strip + binary-sign-tool 签名 |
| 3 | Go linker mapping output file failed | HMDFS 不支持 mmap 写入 | 输出到 /data/storage/el2/base/cache |
| 4 | go.mod 要求 Go 1.26.2 | 上游使用最新 Go 版本 | 补丁降至 1.25.0 |
| 5 | Go 工具链自动下载 1.26.5 失败 | GOTOOLCHAIN=auto | 设置 GOTOOLCHAIN=local |

## 源码修改

- patches/0001-go.mod.patch: go.mod 版本指令 1.26.2 → 1.25.0

## 依赖版本

- Go 1.25.0 (编译器，非 Conan 依赖)

## 验证结果

```bash
$ cf --version
cf version 8.18.3
$ cf help
[显示帮助信息]
```

## 注意事项

- Go 编译的二进制必须先 strip 再 ELF 签名
- Go linker 在 HMDFS 上无法直接输出二进制，需要输出到 ext4 可写路径
- 版本号通过 ldflags -X 注入: code.cloudfoundry.org/cli/v8/version.binaryVersion
---

**编译结束**: 2026-08-06 04:18
**最终状态**: built
