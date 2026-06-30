# nuclei 3.8.0 适配笔记

## 编译环境
- 构建系统: custom (Go项目)
- 编译日期: 2026-06-01
- 编译器: Go 1.26.3 (~/sdk/go1.26.3/bin/go)
- 状态: published

## 编译步骤

nuclei 是 ProjectDiscovery 的漏洞扫描器，为纯 Go 项目，无 configure/make 流程。

```bash
# 环境变量
export GOROOT=/storage/Users/currentUser/sdk/go1.26.3
export PATH=$GOROOT/bin:$PATH
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64
export TMPDIR=/data/storage/el2/base/cache

# 进入源码目录
cd ~/tmp/builds/nuclei-3.8.0.work

# 编译（入口点在 cmd/nuclei，而非根目录）
go build -ldflags="-s -w" -o $TMPDIR/nuclei ./cmd/nuclei

# 安装（使用install代替cp，HMDFS限制）
install -m 755 $TMPDIR/nuclei $DEFAULT_PREFIX/bin/nuclei

# DESTDIR模式staging
install -m 755 $TMPDIR/nuclei $TEST_PREFIX/$DEFAULT_PREFIX/bin/nuclei
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go.mod要求go 1.25.7+，系统Go仅1.24.2 | 版本差距大 | 使用~/sdk/go1.26.3/bin/go |
| 2 | `go build .`失败：no Go files in root | nuclei主入口不在根目录 | 改为`go build ./cmd/nuclei` |
| 3 | Go linker mmap在HMDFS失败 | 链接器内部mmap不支持HMDFS | 输出到/data/storage/el2/base/cache/ |
| 4 | 未签名二进制permission denied | 需ELF签名才能在鸿蒙执行 | ohc-run.py sign-elf签名 |
| 5 | init-build自动下载SSL失败 | GitHub SSL证书问题 | 手动curl下载后--no-download |

## 依赖版本

- Go 1.26.3 (~/sdk/go1.26.3)
- 无其他编译依赖（纯Go项目，CGO_ENABLED=0）

## 验证结果

```bash
$ nuclei --version
[INF] Nuclei Engine Version: v3.8.0
[INF] Nuclei Config Directory: /data/storage/el2/base/haps/entry/files/nuclei

$ file nuclei
ELF executable, 64-bit LSB arm64, static, stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nuclei | 110MB | 静态编译，ELF签名，stripped |

## 注意事项

- nuclei 是 CGO_ENABLED=0 纯静态编译，无动态链接依赖
- 必须使用 Go 1.26.3（1.26.0有corrupted runtime，低于1.25.7不满足go.mod要求）
- 输出路径必须避开HMDFS（Go linker mmap问题）
---

**编译结束**: 2026-06-01 23:26
**最终状态**: published
