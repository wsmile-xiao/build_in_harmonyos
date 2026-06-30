# opa 0.70.0 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-06-01
- 编译器: Go 1.26.3 (~/sdk/go1.26.3/bin/go)
- 状态: published

## 编译步骤

opa 是 Go 项目（Open Policy Agent），不需要 configure/make 流程。

1. 源码解压后，删除空的 vendor 目录（只含 modules.txt，无实际包）
2. 使用 Go 1.26.3 进行静态编译（本地 Go 1.24.2 的 compile 工具实际为 1.23.6 版本，存在版本不匹配问题）
3. 编译命令:
```bash
TMPDIR=/data/storage/el2/base/cache \
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
GOPROXY=https://goproxy.cn,direct \
GOROOT=~/sdk/go1.26.3 \
PATH=~/sdk/go1.26.3/bin:$PATH \
go build -ldflags="-s -w" -o /data/storage/el2/base/cache/opa .
```
4. ELF 签名后安装到 $DEFAULT_PREFIX/bin/opa

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go build 版本不匹配: "compile version go1.23.6 does not match go tool version go1.24.2" | 本地 Go 安装的 go 命令是 1.24.2 但 pkg/tool/ 下的 compile/link 等工具是 1.23.6 版本，安装不一致 | 使用 ~/sdk/go1.26.3/bin/go 编译，其 compile 工具版本正确为 go1.26.3 |
| 2 | vendor 目录为空（只有 modules.txt）导致 -mod=vendor 模式找不到依赖包 | 源码包的 vendor 目录不完整 | 删除 vendor 目录，使用 GOPROXY 下载依赖 |
| 3 | Go linker mmap 在 HMDFS 上失败 | HMDFS 文件系统不支持 mmap 操作 | 输出到 /data/storage/el2/base/cache/ 避免问题 |
| 4 | 未签名 ELF 二进制无法执行（permission denied） | OpenHarmony 安全策略要求 ELF 签名 | 使用 ohc-run.py sign-elf 签名 |

## 源码修改

无补丁，无源码修改。

## 依赖版本

- Go 1.26.3 (编译器)
- opa go.mod 要求 Go 1.21+（兼容）

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/opa version
Version: 0.70.0
Build Commit: 
Build Timestamp: 
Build Hostname: 
Go Version: go1.26.3
Platform: linux/arm64
WebAssembly: unavailable
```

WebAssembly: unavailable 是因为 CGO_ENABLED=0 静态编译禁用了 WASM 支持，这是预期行为。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| opa-0.70.0-ohos-aarch64.tar.gz | ~30MB | 预编译包（含 ELF 签名的 opa 二进制） |

## 注意事项

- 必须使用 ELF 签名后才能在 OpenHarmony 上执行
- CGO_ENABLED=0 是 Go 项目在 OpenHarmony 上的标准编译方式
- WebAssembly 功能不可用（静态编译模式下被禁用）
- 本地 Go 1.24.2 安装的 compile 工具版本不匹配（1.23.6），必须使用 Go 1.26.3 编译
---

**编译结束**: 2026-06-01 19:57
**最终状态**: published
