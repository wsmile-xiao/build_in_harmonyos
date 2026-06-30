# talhelper 1.17.1 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-06-01
- 编译器: Go 1.24.2 (GOROOT=/storage/Users/currentUser/usr/local/go)
- 状态: built

## 编译步骤

talhelper 是一个 Go 工具，用于辅助创建 Talos Linux 集群配置。采用 CGO_ENABLED=0 静态编译。

```bash
# 1. 创建缺失的本地模块 tsehelper (go.mod 中的 replace directive)
mkdir -p hack/tsehelper/pkg/versiontags
# 从 GitHub 源码仓库获取 versiontags/tags.go 内容并创建本地包

# 2. Go 静态编译
export GOROOT=/storage/Users/currentUser/usr/local/go
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64
go build -a -ldflags="-s -w" -o $DEFAULT_PREFIX/bin/talhelper .

# 3. ELF 签名（鸿蒙平台必须）
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/talhelper

# 4. DESTDIR staging 安装
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp $DEFAULT_PREFIX/bin/talhelper $TEST_PREFIX/$DEFAULT_PREFIX/bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tsehelper` 模块缺失: `hack/tsehelper does not exist` | go.mod 有 `replace tsehelper => ./hack/tsehelper` 但源码 zip 不含 hack/ 目录 | 从 GitHub API 获取 tsehelper/pkg/versiontags/tags.go 源码，手动创建 hack/tsehelper 目录 |
| 2 | Go 编译器版本不匹配: `version "go1.23.6" does not match go tool version "go1.24.2"` | 已安装的 go 编译器（pkg/tool/linux_arm64/compile）是 go1.23.6 版本，但 go 二进制是 go1.24.2 | 设置 GOROOT 指向完整 Go SDK (/storage/Users/currentUser/usr/local/go)，并签名所有 Go SDK 工具二进制 |
| 3 | Go SDK compile 工具无法执行: `permission denied` | Go SDK 中的工具二进制未经 ELF 签名 | 使用 ohc-run.py sign-elf 对 Go SDK pkg/tool/linux_arm64/ 下所有二进制签名 |

## 源码修改

- 新增 `hack/tsehelper/pkg/versiontags/tags.go`: 从 GitHub 原始仓库获取的 versiontags 包，提供 TalosVersionTags 类型
- 新增 `hack/tsehelper/go.mod`: tsehelper 本地模块定义，依赖 golang.org/x/mod v0.14.0

## 依赖版本

- Go 1.24.2 (Go SDK at /storage/Users/currentUser/usr/local/go)

## 验证结果

```bash
$ talhelper help
talhelper is a tool to help you create a Talos cluster.
# 二进制正常执行，输出帮助信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| talhelper-1.17.1-ohos-aarch64.tar.gz | ~24MB | 预编译包 |

## 注意事项

- Go 编译时必须使用 `-a` 标签强制重新编译所有包（避免版本不匹配问题）
- hack/tsehelper 目录在原始源码 zip 中不存在，需要手动创建
- Go 工具链的版本一致性很重要：go 二进制和 compile/link 等工具版本必须匹配
---

**编译结束**: 2026-06-01 20:11
**最终状态**: built
