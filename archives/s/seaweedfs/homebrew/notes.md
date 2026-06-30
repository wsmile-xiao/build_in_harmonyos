# SeaweedFS — Homebrew (master) 编译笔记

## 软件信息
- **名称**: seaweedfs
- **版本**: homebrew (master branch)
- **构建系统**: Go (go build)
- **平台**: OpenHarmony aarch64
- **Go版本**: go1.26.4 linux/arm64

## 编译过程

### 1. 源码获取
- 来源: https://codeload.github.com/seaweedfs/seaweedfs/tar.gz/refs/heads/master
- 由于 `weed` 同时是一个 Go package 目录和一个预期的输出文件名，`go build -o weed ./weed` 会将二进制放入 `weed/weed`

### 2. 编译命令
```bash
cd $BUILD_SRC_DIR
export GOPROXY=https://goproxy.cn
export CGO_ENABLED=0
go build -o weed ./weed
```

### 3. 安装
- Staging: `cp weed/weed $TEST_PREFIX/$DEFAULT_PREFIX/bin/weed`
- 本地安装: `cp weed/weed $DEFAULT_PREFIX/bin/weed`

### 4. 验证
```
version 30GB 4.34  linux arm64
```
- ELF 64-bit LSB executable, ARM aarch64, statically linked
- CGO_ENABLED=0 确保纯静态链接，无需 RPATH

## 注意事项
- Go 项目无需 configure/make，直接 `go build`
- 使用 `GOPROXY=https://goproxy.cn` 加速国内下载
- `CGO_ENABLED=0` 生成纯静态二进制，无外部库依赖
- 二进制大小约 189MB（含调试信息），strip 后可减小

## 编译结束
**最终状态**: published
---

**编译结束**: 2026-06-22 02:47
**最终状态**: built
