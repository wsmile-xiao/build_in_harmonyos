# duf 0.9.1 适配笔记

## 编译环境
- 构建系统: custom (Go build)
- 编译日期: 2026-06-01
- 编译器: Go 1.24.2 (linux/arm64)
- 状态: built

## 编译步骤

duf 是纯 Go 工具（Disk Usage/Free utility，类似 df 但更美观），不需要 configure/make 流程，直接使用 `go build` 编译：

```bash
source .build-context-duf-0.9.1
cd $BUILD_SRC_DIR

# 关键：GOROOT 必须设置为 ~/usr/local/go，否则会因 pkg 版本不匹配报错
# GOROOT 默认指向 ~/usr/local（DEFAULT_PREFIX），其 pkg/tool 目录来自 go1.23.6
# Go 1.24.2 安装在 ~/usr/local/go/ 下，需要明确指定

# 关键：TMPDIR 必须设置为 /data/storage/el2/base/cache，否则 Go linker 
# 会报 "mapping output file failed: permission denied"
# 这是因为鸿蒙平台 /tmp 是只读的，而 Go linker 使用 mmap 写入输出文件

# Go 工具链的 link/compile/asm 需要先 ELF 签名才能正常执行

# DESTDIR 模式：先安装到 staging，再安装到 DEFAULT_PREFIX
GOROOT=/storage/Users/currentUser/usr/local/go \
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
GOPROXY=https://goproxy.cn,direct \
TMPDIR=/data/storage/el2/base/cache \
go build -ldflags="-s -w" -o $TEST_PREFIX/$DEFAULT_PREFIX/bin/duf .

# 签名 staging 产物
ohc-run.py sign-elf $TEST_PREFIX/$DEFAULT_PREFIX/bin/duf

# 安装到 DEFAULT_PREFIX（模拟用户部署）
cp $TEST_PREFIX/$DEFAULT_PREFIX/bin/duf $DEFAULT_PREFIX/bin/duf

# 签名本地安装产物
ohc-run.py sign-elf $DEFAULT_PREFIX/bin/duf
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go build 报 `version "go1.23.6" does not match go tool version "go1.24.2"` | GOROOT 默认为 ~/usr/local（DEFAULT_PREFIX），其 pkg/tool 目录来自 go1.23.6；Go 1.24.2 安装在 ~/usr/local/go/ 下 | 设置 `GOROOT=/storage/Users/currentUser/usr/local/go` |
| 2 | Go linker 报 `mapping output file failed: permission denied` | 鸿蒙平台 /tmp 只读，Go linker 使用 mmap 写入中间输出文件需要可写目录 | 设置 `TMPDIR=/data/storage/el2/base/cache` |
| 3 | Go 工具链 (link/compile/asm) 执行报 permission denied | 鸿蒙 ELF 签名要求，未签名的二进制无法执行 | 使用 `ohc-run.py sign-elf` 签名 Go 工具链二进制 |
| 4 | GitHub 源码下载超时/SSL证书失败 | 网络限制导致无法直接下载 GitHub tarball | 使用 Go module cache 获取源码：`go mod download` 通过 goproxy.cn 成功获取 |
| 5 | go test 无法运行（fork/exec permission denied） | 鸿蒙平台 ELF 签名要求，Go 测试二进制生成在 build cache 中无法预签名 | 跳过 go test，记录为平台限制 |

## 源码修改

无补丁，无源码修改。Go 工具在本平台（linux/arm64）直接编译通过。

## 依赖版本

- Go 1.24.2 (linux/arm64)
- github.com/IGLOU-EU/go-wildcard v1.0.3 (Go module dependency)
- github.com/jedib0t/go-pretty/v6 v6.6.8 (Go module dependency)
- github.com/mattn/go-runewidth v0.0.16 (Go module dependency)
- github.com/muesli/mango v0.2.0 (Go module dependency)
- github.com/muesli/roff v0.1.0 (Go module dependency)
- github.com/muesli/termenv v0.16.0 (Go module dependency)
- golang.org/x/sys v0.35.0 (Go module dependency)
- golang.org/x/term v0.34.0 (Go module dependency)

## 验证结果

```bash
$ duf --version
duf (built from source)

$ duf
╭──────────────────────────────────────────────────────────────────────────────╮
│ 92 local devices                                                             │
├────────────────┬────────┬─────────┬────────┬────────┬────────┬───────────────┤
│ MOUNTED ON     │   SIZE │    USED │  AVAIL │  USE%  │ TYPE   │ FILESYSTEM    │
...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| duf (ELF binary) | ~3.0MB | 签名后的 aarch64 静态链接二进制 |

## 注意事项

- duf 不支持 --version flag 显示版本号，仅输出 "duf (built from source)"
- 源码获取通过 Go module cache 而非直接下载 tarball（网络限制）
- Go linker 在鸿蒙上需要特殊 TMPDIR 设置
---

**编译结束**: 2026-08-06 08:11
**最终状态**: built
