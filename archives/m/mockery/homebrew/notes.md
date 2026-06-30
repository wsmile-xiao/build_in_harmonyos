# mockery homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-02
- 编译器: Go 1.26.3 (~/usr/local/go1263/bin/go)
- 目标平台: linux/arm64 (OpenHarmony)
- 状态: published

## 编译步骤

1. **init-build**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build mockery homebrew --url=https://github.com/vektra/mockery/archive/refs/tags/v2.52.1.tar.gz`
2. **修正manifest**: system=custom, build_system=go
3. **依赖升级**: `go get golang.org/x/tools@latest` (升级 v0.17.0 → v0.45.0) 以解决 Go 1.26.3 与 x/tools v0.17.0 的兼容性问题（tokeninternal 包的 invalid array length 错误）
4. **go mod tidy**: 清理依赖并更新 go.sum
5. **移除 go.work/go.work.sum**: go.work 文件导致依赖版本冲突，移除后使用 go.mod 直接构建
6. **Go编译**: `TMPDIR=/data/storage/el2/base/cache CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct ~/usr/local/go1263/bin/go build -ldflags="-s -w -X github.com/vektra/mockery/v2/pkg/logging.SemVer=v2.52.1" -o mockery .`
7. **DESTDIR安装**: 手动 cp mockery 到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/mockery`
8. **ELF签名**: `python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf` 对 staging 和本地二进制签名
9. **本地安装**: cp 到 `$DEFAULT_PREFIX/bin/mockery`
10. **验证**: `~/usr/local/bin/mockery --version` → v2.52.1

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | x/tools v0.17.0 编译报 `invalid array length -delta * delta` | Go 1.26.3 语言规范变更，不再允许负数作为数组长度；x/tools v0.17.0 的 tokeninternal 包使用了此模式 | `go get golang.org/x/tools@latest` 升级到 v0.45.0 |
| 2 | go.work 导致依赖版本冲突 | go.work 文件强制拉取 v0.24.0，也有同样的兼容问题 | 移除 go.work 和 go.work.sum 文件 |
| 3 | `--version` 显示 v0.0.0-dev | 从 tarball 构建无 git 版本信息，SemVer 默认为空，debug.ReadBuildInfo 返回 "(devel)" | ldflags `-X` 注入 SemVer=v2.52.1 |
| 4 | cp 覆盖已安装二进制报 Operation not permitted | HMDFS 不支持覆盖写入（R5 铁律） | `rm -f` 先删除再复制 |

## 源码修改

- 移除 go.work 和 go.work.sum（构建冲突）
- go.mod 升级: golang.org/x/tools v0.17.0 → v0.45.0, golang.org/x/mod v0.14.0 → v0.36.0, golang.org/x/sys v0.12.0 → v0.44.0, go 1.23 → 1.25.0

## 依赖版本

- Go 1.26.3 (~/usr/local/go1263/bin/go)
- golang.org/x/tools v0.45.0
- golang.org/x/mod v0.36.0
- golang.org/x/sys v0.44.0
- github.com/spf13/cobra v1.8.1
- github.com/rs/zerolog v1.33.0

## 验证结果

```bash
$ ~/usr/local/bin/mockery --version
02 Jun 26 03:57 UTC INF couldn't read any config file version=v2.52.1
02 Jun 26 03:57 UTC INF Starting mockery dry-run=false version=v2.52.1
02 Jun 26 03:57 UTC INF Using config:  dry-run=false version=v2.52.1
v2.52.1

$ file ~/usr/local/bin/mockery
ELF executable, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ~/usr/local/bin/mockery | ~11MB | mockery v2.52.1 ELF arm64 二进制（已签名、已strip） |
| $TEST_PREFIX/$DEFAULT_PREFIX/bin/mockery | ~11MB | DESTDIR staging 安装副本 |

## 注意事项

- Go 1.26.3 与 x/tools ≤ v0.24.0 不兼容，必须升级到 v0.45.0+
- mockery 的版本信息通过 ldflags `-X github.com/vektra/mockery/v2/pkg/logging.SemVer` 注入，否则显示 v0.0.0-dev
- HMDFS 文件系统不支持覆盖写入，必须先 rm -f 再 cp（R5 铁律）
- go.work 文件在发布构建中应移除，避免版本冲突
---

**编译结束**: 2026-06-02 12:10
**最终状态**: built
