# yj 5.1.0 适配笔记

## 编译环境
- 构建系统: custom (Go 语言项目)
- 编译日期: 2026-06-15
- 编译器: clang/clang++ (Go 1.26.0 for compilation)
- 状态: built

## 编译步骤

yj 是 Go 语言项目，使用 `go build` 编译。因 Go 1.24.x linker 在 HMDFS 上 mmap 失败，需使用 Go 1.26.0。

```bash
# 设置 Go 1.26.0 环境
export GOROOT=/storage/Users/currentUser/usr/local/go1.26/go
export PATH="$GOROOT/bin:$PATH"
export GOPATH="$HOME/go"
export GOCACHE="$HOME/tmp/go-cache26"
export TMPDIR="$HOME/tmp"

# 编译 yj
CGO_ENABLED=0 go build -ldflags "-X main.Version=5.1.0" -o yj .

# 安装到 staging (DESTDIR)
STAGING_PREFIX="$TEST_PREFIX/$DEFAULT_PREFIX"
mkdir -p "$STAGING_PREFIX/bin"
cp yj "$STAGING_PREFIX/bin/yj"
chmod 755 "$STAGING_PREFIX/bin/yj"

# 运行测试 (需要先 ELF 签名)
go test -c -o yj.test .
# 签名后执行
./yj.test -test.v

# 安装到本地 (模拟用户部署)
cp yj "$DEFAULT_PREFIX/bin/yj"
chmod 755 "$DEFAULT_PREFIX/bin/yj"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 1.24.x linker "mapping output file permission denied" | HMDFS 不支持 Go linker 的 mmap 写入方式 | 使用 Go 1.26.0 (其 linker 使用不同的写入策略 "Copied OK") |
| 2 | Go toolchain binaries 无法 fork/exec (permission denied) | HMDFS 上未签名的 ELF 二进制无法执行 | 使用 binary-sign-tool 签名所有 Go toolchain 二进制 |
| 3 | go test 生成的测试二进制无法执行 | HMDFS ELF 签名要求 | 使用 go test -c 编译测试二进制，手动签名后再执行 |
| 4 | 无 configure/make 步骤 | Go 语言项目使用 go build | 自定义编译流程 (go build → cp → go test) |

## 源码修改

无源码修改。yj 在 OpenHarmony 上可以零修改编译。

## 依赖版本

- Go 1.26.0 (编译器)
- clang 15.0.4 (系统编译器)
- 无外部库依赖 (Go 项目自带所有依赖)

## 验证结果

```bash
$ yj -v
v5.1.0

$ echo '{"key": "value"}' | yj -r
key: value

$ echo 'key: value' | yj -yj
{"key":"value"}

# Tests: 27 PASS (6 functions + 21 subtests)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| yj | 4.6MB | 主二进制文件 (ELF static, aarch64) |

## 注意事项

- 必须使用 Go 1.26.0 编译，Go 1.24.x/1.25.x 的 linker 在 HMDFS 上 mmap 失败
- Go toolchain 二进制需要 ELF 签名才能在 HMDFS 上执行
- 测试二进制也需要 ELF 签名
---

**编译结束**: 2026-06-15 22:16
**最终状态**: built
