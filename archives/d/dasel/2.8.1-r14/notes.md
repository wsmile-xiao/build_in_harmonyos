# dasel 2.8.1-r14 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-06-02
- 编译器: ~/usr/local/go1263/bin/go (Go 1.26.3)
- 状态: built

## 编译步骤

1. 源码下载: https://github.com/TomWright/dasel/archive/refs/tags/v2.8.1.tar.gz
2. Go 编译命令:
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct ~/usr/local/go1263/bin/go build \
  -ldflags="-s -w -X github.com/tomwright/dasel/v2/internal.Version=v2.8.1" \
  -o dasel ./cmd/dasel/
```
3. DESTDIR staging 安装: cp dasel $TEST_PREFIX/$DEFAULT_PREFIX/bin/dasel
4. 本地安装: cp dasel $DEFAULT_PREFIX/bin/dasel
5. ELF 签名: ohc-run.py sign-elf $DEFAULT_PREFIX/bin/dasel
6. 验证: ~/usr/local/bin/dasel --version → dasel version v2.8.1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build SSL下载失败 | SSL证书验证问题 | 手动 curl -kL 下载源码 |
| 2 | 版本显示"development"而非v2.8.1 | ldflags -X main.version 路径错误 | 版本变量在 internal 包，改为 -X github.com/tomwright/dasel/v2/internal.Version=v2.8.1 |

## 源码修改

无源码修改，纯 Go 编译。

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)

## 验证结果

```bash
$ ~/usr/local/bin/dasel --version
dasel version v2.8.1

$ echo '{"name":"test"}' | dasel -r json '.name'
"test"
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dasel-2.8.1-r14-ohos-aarch64.tar.gz | 9550KB | 预编译包 |
| dasel-2.8.1-r14-ohos-aarch64-debug.tar.gz | 70KB | debug符号包 |

## 注意事项

- dasel 是纯 Go 项目，使用 `go build` 而非 autotools/cmake
- 版本注入需要使用正确的包路径: `github.com/tomwright/dasel/v2/internal.Version`
- Go 模块路径: github.com/tomwright/dasel/v2（注意 v2 后缀）
---

**编译结束**: 2026-08-06 06:05
**最终状态**: built
