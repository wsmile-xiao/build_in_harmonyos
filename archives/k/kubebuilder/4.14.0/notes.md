# kubebuilder 4.14.0 适配笔记

## 编译环境
- 构建系统: custom (Go project)
- 编译日期: 2026-06-04
- 编译器: go 1.25.11 (downloaded from Chinese mirror, ELF signed)
- 状态: published

## 编译步骤

1. 下载源码: `curl -fsSL https://github.com/kubernetes-sigs/kubebuilder/archive/refs/tags/v4.14.0.tar.gz`
2. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build kubebuilder 4.14.0`
3. 安装 Go 1.25.11 (从中国镜像 golang.google.cn 下载，ELF签名所有二进制)
4. 设置 GOPROXY=https://goproxy.cn,direct (解决 Go module 下载超时问题)
5. 设置 GOTOOLCHAIN=auto (自动下载所需 Go 版本)
6. 执行编译: `go build -v -o kubebuilder .` (在源码目录)
7. Staging 安装: DESTDIR 模式，安装到 $TEST_PREFIX/$DEFAULT_PREFIX/bin/kubebuilder
8. 本地安装: cp kubebuilder ~/usr/local/bin/kubebuilder

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py init-build SSL 下载失败 | Python SSL 证书验证失败 | 先用 curl 手动下载源码包，再 init-build --no-download |
| 2 | go.mod 要求 Go 1.25.7，本地只有 Go 1.24.2 | kubebuilder v4.14.0 依赖新版 Go | 从 golang.google.cn 下载 Go 1.25.11，签名后使用 |
| 3 | Go module 下载超时 (proxy.golang.org) | 网络限制无法访问 proxy.golang.org | 设置 GOPROXY=https://goproxy.cn,direct |
| 4 | Go 工具链 ELF 未签名 | 下载的 Go 工具无法在 OpenHarmony 上执行 | 使用 ohc-run.py sign-elf 签名所有 Go 工具链 ELF 文件 |
| 5 | GOTOOLCHAIN=auto 下载的 Go 无执行权限 | 新下载的 Go 版本未签名 | 手动下载 Go 1.25.11 到指定路径并签名 |

## 源码修改

修改 go.mod 中的 Go 版本要求：
- 原始: `go 1.25.7` → 已恢复为 `go 1.25.7`（Go 1.25.11 兼容）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| go | 1.25.11 | golang.google.cn 镜像下载 + ELF 签名 |

## 验证结果

```bash
$ ~/usr/local/bin/kubebuilder version
KubeBuilder:          (devel)
Kubernetes:           1.35.0
Git Commit:           unknown
Build Date:           unknown
Go OS/Arch:           linux/arm64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kubebuilder | 23MB | Go 编译的 aarch64 ELF 二进制 |

## 注意事项

- kubebuilder 是 Go 项目，不支持传统的 configure/make 编译方式
- 需要使用 Go 1.25.x 系列版本才能编译 v4.14.0
- Go 工具链的所有 ELF 二进制都需要签名才能在 OpenHarmony 上执行
- 使用中国 Go 模块代理 (goproxy.cn) 解决模块下载超时问题
---

**编译结束**: 2026-06-08 17:31
**最终状态**: published
