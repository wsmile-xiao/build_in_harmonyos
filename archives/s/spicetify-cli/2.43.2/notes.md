# spicetify-cli 2.43.2 适配笔记

## 编译环境
- 构建系统: custom（Go项目，纯静态编译）
- 编译日期: 2026-06-01
- 编译器: go1.26.3（GOROOT=/storage/Users/currentUser/usr/local/go1263）
- 状态: built

## 编译步骤

spicetify-cli 是纯 Go 项目，无 configure/make 步骤，直接使用 `go build` 编译：

```bash
# 设置 Go 环境（必须使用 go1.26.3，因为系统默认 go 的 pkg/tool 版本不匹配）
export GOROOT=/storage/Users/currentUser/usr/local/go1263
export PATH=$GOROOT/bin:$PATH
export TMPDIR=/data/storage/el2/base/cache

# 静态编译
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct \
  go build -ldflags="-s -w -X main.version=2.43.2" -o spicetify .

# 安装到 staging（DESTDIR 模式）
install -m 755 spicetify $TEST_PREFIX/$DEFAULT_PREFIX/bin/spicetify

# 安装到本地（模拟用户部署）
install -m 755 spicetify $DEFAULT_PREFIX/bin/spicetify
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `compile: version "go1.23.6" does not match go tool version "go1.24.2"` | 系统默认 Go 的 GOTOOLDIR 指向 go1.23.6 的 compile 工具，与 go1.24.2 不匹配 | 使用独立的 go1.26.3 安装（GOROOT=/storage/Users/currentUser/usr/local/go1263），其工具链版本一致 |
| 2 | 系统默认 Go 的 compile 工具 permission denied | GOROOT=/storage/Users/currentUser/usr/local 的 pkg/tool/linux_arm64/compile 未 ELF 签名 | 使用 go1263 安装的已签名 compile 工具 |

## 依赖版本

- go 1.26.3 (GOROOT=/storage/Users/currentUser/usr/local/go1263)

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/spicetify --version
2.43.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| spicetify | 7.4MB | 静态编译的 ELF arm64 二进制 |

## 注意事项

- 必须使用 go1263（或版本匹配的 Go 安装），系统默认 go 的工具链版本不匹配会导致编译失败
- spicetify-cli 是 Spotify 客户端定制工具，在鸿蒙上主要用于开发者调试 Spotify UI
- 版本号必须通过 ldflags `-X main.version=2.43.2` 注入，否则显示 "Dev"
---

**编译结束**: 2026-06-01 19:58
**最终状态**: published
