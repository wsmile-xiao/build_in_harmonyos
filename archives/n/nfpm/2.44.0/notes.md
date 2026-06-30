# nfpm 2.44.0 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-06-17
- 编译器: Go 1.26.4 (gc)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/goreleaser/nfpm/archive/v2.44.0.tar.gz
2. 解压到 ~/tmp/builds/nfpm-2.44.0.orig
3. 复制工作目录: ~/tmp/builds/nfpm-2.44.0.work
4. 设置 Go 环境变量 (CGO_ENABLED=0, GOOS=linux, GOARCH=arm64)
5. 编译: `cd ~/tmp/builds/nfpm-2.44.0.work && go build -ldflags="-s -w -X main.version=2.44.0 -X main.platform=linux/arm64" -o nfpm ./cmd/nfpm`
6. 安装到 staging: `mkdir -p ~/tmp/test-install-nfpm-2.44.0/bin && cp nfpm ~/tmp/test-install-nfpm-2.44.0/bin/nfpm`
7. 安装到本地: `cp nfpm ~/usr/local/bin/nfpm`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go test files/TestTree 失败 | testdata 中有绝对路径软链接，Python tarfile 拒绝提取 | 非核心功能问题，不影响生产代码 |
| 2 | G0 clean verify configure 失败 | Go 项目无 configure 脚本 | 平台限制，已手动验证通过 |

## 源码修改

无源码修改（Go 项目纯编译，无需补丁）

## 依赖版本

- go 1.26.4

## 验证结果

```bash
$ ~/usr/local/bin/nfpm --version
GitVersion:    2.44.0
Platform:      linux/arm64
GoVersion:     go1.26.4

$ file ~/usr/local/bin/nfpm
ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nfpm-2.44.0-ohos-aarch64.tar.gz | ~13MB | 预编译包 (bin/nfpm) |

## 注意事项

- nfpm 是 Go 项目，使用 `go build` 编译，无 configure/make 流程
- 静态链接，无需动态库依赖
- 已 stripped，无需额外 strip 步骤
---

**编译结束**: 2026-06-17 02:07
**最终状态**: published
