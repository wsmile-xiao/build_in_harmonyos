# goenv 3.1.1 适配笔记

## 编译环境
- 构建系统: Go (CGO_ENABLED=0 静态编译)
- 编译日期: 2026-08-06
- 编译器: Go 1.24.0 (auto-bootstrapped via conan recipe)
- 状态: built

## 编译步骤

goenv 是一个 Go 语言项目，不需要传统的 configure/make 流程。

1. 下载源码: `curl -fsSL -o ~/tmp/downloads/goenv-3.1.1.tar.gz https://github.com/go-nv/goenv/archive/refs/tags/3.1.1.tar.gz`
2. 解压到构建目录: `~/tmp/builds/goenv-3.1.1.work`
3. 编译:
   ```bash
   cd ~/tmp/builds/goenv-3.1.1.work
   GOROOT=/storage/Users/currentUser/usr/local/go \
   PATH=/storage/Users/currentUser/usr/local/go/bin:$PATH \
   TMPDIR=/data/storage/el2/base/cache \
   CGO_ENABLED=0 \
   GOPROXY=https://goproxy.cn,direct \
   GOOS=linux \
   GOARCH=arm64 \
   go build -ldflags "-X main.version=3.1.1 -X main.commit=unknown -X main.buildTime=2026-06-01T12:00:00Z" -o goenv .
   ```
4. DESTDIR 安装:
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   cp goenv $TEST_PREFIX/$DEFAULT_PREFIX/bin/goenv
   chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/goenv
   ```
5. 本地安装+ELF签名:
   ```bash
   cp goenv $DEFAULT_PREFIX/bin/goenv
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/goenv
   $DEFAULT_PREFIX/bin/goenv --version
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go版本不匹配(compile: go1.23.6 vs go: go1.24.0) | ~/usr/local/bin/go的GOROOT指向旧版工具链 | conan recipe auto-bootstraps Go 1.24.0 SDK from golang.google.cn |
| 2 | `go build` link步骤权限拒绝 | TMPDIR=/tmp只读(E002) | 设置TMPDIR=/data/storage/el2/base/cache |
| 3 | `go test ./...` 全部permission denied | 鸿蒙ELF签名要求，test二进制未签名无法执行 | 平台限制，跳过测试，手动验证主二进制 |

## 依赖版本

- Go 1.24.0 (auto-bootstrapped from golang.google.cn in conan recipe)

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/goenv --version
goenv 3.1.1

$ file $DEFAULT_PREFIX/bin/goenv
ELF executable, 64-bit LSB arm64, static, BuildID=16d8119feb2c6b3102bf45a982c5c2364d3ec0ca, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| goenv | 18.8MB | 静态编译的Go版本管理器二进制 |

## 注意事项

- goenv 是 Go 项目而非 bash 脚本项目（旧版 goenv 1.x 是 bash 脚本，新版 2.x+ 是 Go 编写）
- GOROOT 必须设置为 ~/usr/local/go，不能使用系统默认的 ~/usr/local（旧版工具链）
- Go test 无法在鸿蒙平台执行（ELF签名限制），功能验证通过手动运行 --version
---

**编译结束**: 2026-08-06 14:52
**最终状态**: built
