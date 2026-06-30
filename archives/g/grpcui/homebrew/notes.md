# grpcui homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-03
- 编译器: Go 1.26.3 (CGO_ENABLED=1, CC=clang)
- 状态: published

## 编译步骤

1. `init-build` 下载源码 (v1.4.3 tar.gz, 通过 ghfast.top 镜像下载)
2. 修正 manifest: system=custom, build_system=go
3. Go 编译:
   ```bash
   cd ~/tmp/builds/grpcui-homebrew.work
   export TMPDIR=/data/storage/el2/base/cache
   export CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct
   ~/usr/local/go1263/bin/go build -ldflags="-s -w -X main.version=v1.4.3" -o grpcui ./cmd/grpcui/
   ```
4. DESTDIR 安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/grpcui`
5. 本地安装: `cp grpcui ~/usr/local/bin/grpcui`
6. ELF 签名: `binary-sign-tool sign -inFile -outFile -selfSign 1`
7. 验证: `grpcui --version` → v1.4.3

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直接下载失败 (SSL/连接超时) | 网络环境限制 | 使用 ghfast.top 镜像 curl -kL 下载 |
| 2 | Python SSL 下载失败 | HarmonyOS CA 证书问题 | 手动下载 tarball 放入 ~/tmp/builds/ |
| 3 | 版本显示 "dev build <no version set>" | Go ldflags 未注入版本变量 | -ldflags="-X main.version=v1.4.3" |
| 4 | HMDFS 无法覆盖已有文件 | HMDFS 软链接限制 | rm -f 再 cp (R5铁律) |

## 源码修改

无源码修改，Go 编译不需要补丁。

## 依赖版本

- grpcurl: 本地已安装 (~/usr/local/bin/grpcurl)
- Go: 1.26.3 (~/usr/local/go1263/bin/go)
- CGO_ENABLED=1 (需要 C 编译器 clang)

## 验证结果

```bash
$ ~/usr/local/bin/grpcui --version
grpcui v1.4.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| grpcui-homebrew-ohos-aarch64.tar.gz | 26016KB | 预编译包 (含签名ELF) |

## 注意事项

- grpcui 依赖 grpcurl，运行时需要 grpcurl 在 PATH 中
- CGO_ENABLED=1 是必需的（grpcui 依赖 grpcurl 的 CGO 组件）
- 版本号通过 ldflags -X main.version 注入
- GitHub 下载需使用国内镜像（ghfast.top）
---

**编译结束**: 2026-06-03 10:36
**最终状态**: built
