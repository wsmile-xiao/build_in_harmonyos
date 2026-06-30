# cue 0.11.2 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-06-08
- 编译器: Go 1.26.4 (gc, CGO_ENABLED=0)
- 状态: published

## 编译步骤

cue 是 Go 语言编写的配置语言，直接使用 Go 编译，无需 configure/make：

```bash
export PATH=~/.harmonybrew/bin:$PATH
export TMPDIR=/data/storage/el2/base/cache
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
cd /data/storage/el2/base/cache/builds/cue-0.11.2.work
go build -ldflags="-s -w" -o /data/storage/el2/base/cache/cue-bin ./cmd/cue/
```

安装：
```bash
# Staging (DESTDIR mode)
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp cue-bin $TEST_PREFIX/$DEFAULT_PREFIX/bin/cue

# 本地安装
mkdir -p $DEFAULT_PREFIX/bin
cp cue-bin $DEFAULT_PREFIX/bin/cue
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 编译错误: `invalid array length -delta * delta` | cue v0.11.2 vendored 的 golang.org/x/tools 内部代码 `tokeninternal.go` 使用了 compile-time size check (`var _ [-delta * delta]int`)，Go 1.26 的 `token.FileSet` 结构体大小发生变化导致 delta != 0，数组长度变负 | 将 compile-time array length check 替换为 runtime check (`if delta != 0 { panic(...) }`) |

## 源码修改

- `internal/golangorgx/tools/tokeninternal/tokeninternal.go` 第 77-78 行:
  - 原代码: `var _ [-delta * delta]int` (compile-time assertion)
  - 新代码: `if delta != 0 { panic(fmt.Sprintf("token.FileSet size mismatch: ...")) }` (runtime check)

## 依赖版本

- Go 1.26.4 (harmonybrew)

## 验证结果

```bash
$ cue version
cue version (devel)

go version go1.26.4
      -buildmode exe
       -compiler gc
        -ldflags -s -w
     CGO_ENABLED 0
          GOARCH arm64
            GOOS linux
         GOARM64 v8.0
cue.lang.version v0.11.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cue-0.11.2-ohos-aarch64.tar.gz | ~21MB | 预编译包 (ELF arm64, static, stripped) |

## 注意事项

- cue 使用 Go 编译，CGO_ENABLED=0 生成纯静态二进制，无外部依赖
- Go 1.26 与 cue v0.11.2 的 vendored golang.org/x/tools 存在兼容性问题，需要补丁
- 下载 URL 使用 gh.idayer.com GitHub 代理加速（原 URL 有 SSL 证书问题）
---

**编译结束**: 2026-06-08 22:08
**最终状态**: published
