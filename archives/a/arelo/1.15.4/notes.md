# arelo 1.15.4 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ + Go 1.25.3 (内嵌工具链)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/makiuchi-d/arelo/archive/refs/tags/v1.15.4.tar.gz
   - sha256: f687e04187145aa6ccaf68fc995f9e8297387a2f27871ccb132625e0635cf15d
   - 使用 gh-proxy.com 镜像下载（GitHub直连失败）
2. 解压到 /storage/Users/currentUser/builds/arelo-1.15.4.work
3. 检查 go.mod: 要求 go 1.24.0
4. 下载 Go 工具链: go1.25.3.linux-arm64.tar.gz
   - URL: https://golang.google.cn/dl/go1.25.3.linux-arm64.tar.gz
   - sha256: 1d42ebc84999b5e2069f5e31b67d6fc5d67308adad3e178d5a2ee2c9ff2001f5
   - 解压到 ~/tmp/go-sdk/go
5. 签名 Go SDK 二进制 (OHOS平台必须):
   ```bash
   /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 \
     -inFile go -outFile go.signed -signAlg SHA256withECDSA
   ```
   签名对象: go, gofmt, pkg/tool/linux_arm64/* (asm, cgo, compile, cover, link, preprofile, vet)
6. Go 编译命令:
   ```bash
   export GOROOT=~/tmp/go-sdk/go
   export GOPATH=~/tmp/go-path
   export CGO_ENABLED=0
   export GOOS=linux
   export GOARCH=arm64
   export GOPROXY=https://goproxy.cn,direct
   export GOTOOLCHAIN=local
   export GOFLAGS=-mod=mod
   # 关键: GOTMPDIR/GOCACHE 必须在 hmfs 上，不能在 tmpfs 上
   export TMPDIR=/data/storage/el2/base/haps/entry/files/arelo-go-work/tmp
   export GOTMPDIR=/data/storage/el2/base/haps/entry/files/arelo-go-work/tmp
   export GOCACHE=/data/storage/el2/base/haps/entry/files/arelo-go-work/go-build-cache
   go mod download
   go build -trimpath -ldflags="-w" -o arelo .
   ```
7. 签名编译产物:
   ```bash
   /data/service/hnp/bin/binary-sign-tool sign -selfSign 1 \
     -inFile arelo -outFile arelo.signed -signAlg SHA256withECDSA
   ```
8. DESTDIR staging安装:
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   cp arelo $TEST_PREFIX/$DEFAULT_PREFIX/bin/arelo
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/licenses
   cp LICENSE $TEST_PREFIX/$DEFAULT_PREFIX/licenses/
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载失败 | 网络问题 | 使用 gh-proxy.com 镜像下载 |
| 2 | Go 二进制无法执行 (permission denied) | OHOS 平台 ELF 必须签名 | 使用 binary-sign-tool 签名所有 Go SDK 二进制 |
| 3 | Go linker "mapping output file failed: permission denied" | Go linker 使用 mmap 创建输出文件，OHOS SELinux 策略在 tmpfs 上禁止 mmap | 将 GOTMPDIR/GOCACHE 设置到 hmfs 路径 (/data/storage/el2/base/haps/entry/files/) |
| 4 | init-build 检测构建系统为 autotools | Go 项目无 configure 脚本 | 手动修正 manifest.yaml: system=custom, build_system=go |
| 5 | CGO_ENABLED=1 时找不到 gcc | 系统只有 clang | 使用 CGO_ENABLED=0 (arelo 是纯 Go 项目，不需要 CGO) |

## 源码修改

无补丁，纯Go编译无需源码修改。

## 依赖版本

- Go 1.25.3 (内嵌工具链，linux-arm64)
- 无 conan 依赖
- 无系统依赖 (CGO_ENABLED=0)

## 验证结果

```bash
arelo --version
# 输出: arelo version (devel)

arelo --help
# 输出: Usage: arelo [OPTION]... -- COMMAND
#       ... (选项列表)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| arelo | ~2.4MB | Go编译的arm64 ELF静态二进制 |

## 注意事项

- Arelo是Go项目，构建系统应为custom/go，非autotools
- CGO_ENABLED=0 即可编译（arelo是纯Go项目，syscall通过golang.org/x/sys实现）
- Go linker 在 OHOS 上需要 hmfs 路径作为临时目录（tmpfs 上 mmap 会失败）
- Go SDK 和编译产物都必须在 OHOS 上签名才能执行
- GOPROXY=https://goproxy.cn,direct 加速依赖下载
---

**编译结束**: 2026-08-07 15:17
**最终状态**: built
