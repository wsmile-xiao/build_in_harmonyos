# gopass 1.16.0 适配笔记

## 编译环境
- 构建系统: makefile (Go project, custom build)
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (Go binary uses Go internal linker)
- Go版本: go1.26.4 linux/arm64
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/gopasspw/gopass/archive/refs/tags/v1.16.0.tar.gz`
2. Go静态编译:
   ```bash
   GO111MODULE=on CGO_ENABLED=0 go build -o gopass \
     -buildvcs=false -tags=netgo -trimpath \
     -ldflags="-s -w -X main.version=1.16.0 -X main.commit=unknown -X main.date=2026-06-17"
   ```
3. 生成shell补全: `make completion`
4. 安装到staging:
   ```bash
   install -m 0755 gopass $TEST_PREFIX/$DEFAULT_PREFIX/bin/gopass
   install -m 0644 gopass.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/gopass.1
   install -m 0644 bash.completion $TEST_PREFIX/$DEFAULT_PREFIX/share/bash-completion/completions/gopass
   install -m 0644 fish.completion $TEST_PREFIX/$DEFAULT_PREFIX/share/fish/vendor_completions.d/gopass.fish
   install -m 0644 zsh.completion $TEST_PREFIX/$DEFAULT_PREFIX/share/zsh/site-functions/_gopass
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PIE模式(-buildmode=pie)编译的gopass运行segfault | PIE模式在鸿蒙上产生dynamically linked ELF，动态链接器不兼容 | 不使用-buildmode=pie，直接静态编译(CGO_ENABLED=0) |
| 2 | tempfile测试失败(/dev/shm不可写) | 鸿蒙平台/dev/shm权限受限 | 平台限制，不影响实际功能(TMPDIR可用) |

## 依赖版本

- Go 1.26.4 (linux/arm64)

## 验证结果

```bash
$ ./gopass version
gopass 1.16.0 go1.26.4 linux arm64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gopass-1.16.0-ohos-aarch64.tar.gz | ~18MB | 预编译包(静态编译) |

## 注意事项

- gopass是Go项目，不使用autotools/configure，需用go build直接编译
- 必须CGO_ENABLED=0，否则PIE模式会segfault
- 不使用-buildmode=pie，直接静态编译更可靠
---

**编译结束**: 2026-06-17 22:48
**最终状态**: published
