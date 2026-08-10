# git-town 16.4.1 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-08-06
- 编译器: Go 1.26.5 (Harmonybrew)
- 状态: built

## 编译步骤

1. Install Go toolchain via Harmonybrew: `brew install go`
2. Set GOPROXY to Chinese mirror: `go env -w GOPROXY=https://goproxy.cn,direct`
3. Build: `GOWORK=off CGO_ENABLED=0 go build -ldflags="-s -w" -o git-town .`
4. Binary output: static ELF arm64, 17MB

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go not installed | HarmonyOS has no Go toolchain | Install via Harmonybrew: `brew install go` |
| 2 | Module download timeout | proxy.golang.org blocked in HarmonyOS | Set GOPROXY=https://goproxy.cn,direct |
| 3 | `-mod=readonly` error | go.work file creates workspace mode conflict | Set GOWORK=off and GOFLAGS=-mod=mod |
| 4 | no cc/c++ in PATH | init-build checks for cc/c++ which are absent | Non-blocking warning, Go uses its own compiler |

## 源码修改

无补丁，源码未做任何修改。git-town 纯 Go 实现，CGO_ENABLED=0 编译为静态二进制。

## 依赖版本

- Go: 1.26.5 (via Harmonybrew)
- Go modules: managed by go.mod/go.sum (downloaded via GOPROXY)

## 验证结果

```bash
$ git-town --version
Git Town 16.4.1

$ git-town --help
Branching and workflow support for Git.
...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/git-town | 17MB | Static ELF arm64 binary |

## 注意事项

- GOWORK=off is required because the source includes a go.work file that conflicts with conan's source extraction
- GOPROXY mirror (goproxy.cn) must be configured for HarmonyOS builds
- ELF signing required on OHOS (handled in conanfile.py via binary-sign-tool)
---

**编译结束**: 2026-08-06 13:35
**最终状态**: built
