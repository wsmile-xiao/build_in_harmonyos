
# lego 4.29.0 适配笔记
## 编译环境
- 构建系统: **Go** (custom) — 使用 go build 编译，CGO_ENABLED=0 静态编译
- 编译日期: 2026-06-17
- 编译器: Go 1.26.4 (clang/clang++ 未使用)

- 状态: built

## 编译步骤
1. 使用 Go module proxy (goproxy.cn) 下载源码和依赖
2. `go build -trimpath -ldflags '-X "main.version=v4.29.0"' -o dist/lego ./cmd/lego/`
3. 手动安装到 DESTDIR 和 DEFAULT_PREFIX

## 遇到的问题与解决方案
| 问题 | 根因 | 解决方案 |
|------|------|----------|
| GitHub 下载超时 | SSL证书/网络限制 | 使用 Go module proxy (goproxy.cn) |
| 自动检测为 autotools | 有 Makefile 存在 | 手动构建 (Go project) |

## 依赖版本
- Go 1.26.4

## 验证结果
- `$DEFAULT_PREFIX/bin/lego --version` → lego version v4.29.0 linux/arm64

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| lego | 85MB | statically linked Go binary (aarch64) |
---

**编译结束**: 2026-06-17 23:02
**最终状态**: built
