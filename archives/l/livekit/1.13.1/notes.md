# livekit 1.13.1 适配笔记

## 编译环境
- 构建系统: custom (Go project)
- 编译日期: 2026-06-11
- 编译器: go 1.26.4 (arm64)
- 状态: published

## 编译步骤

1. **下载源码**: 从 GitHub 获取 livekit v1.13.1 源码（通过 ghfast.top 镜像加速下载）
   - URL: https://github.com/livekit/livekit/archive/refs/tags/v1.13.1.tar.gz
   - 因 GitHub 直连超时，使用 ghfast.top 镜像完成下载

2. **Go 依赖下载**:
   ```bash
   cd /data/storage/el2/base/cache/builds/livekit-1.13.1.work
   export GOPROXY=https://goproxy.cn,direct
   go mod download
   ```

3. **编译构建**:
   ```bash
   export CGO_ENABLED=0
   export GOOS=linux
   export GOARCH=arm64
   export GOPROXY=https://goproxy.cn,direct
   go build -ldflags="-s -w" -o livekit-server ./cmd/server/
   ```

4. **安装到 staging 目录** (DESTDIR模式):
   ```bash
   STAGING=/data/storage/el2/base/cache/test-install-livekit-1.13.1/storage/Users/currentUser/usr/local
   mkdir -p ${STAGING}/bin
   cp livekit-server ${STAGING}/bin/livekit-server
   chmod 755 ${STAGING}/bin/livekit-server
   ```

5. **打包**: 使用 ohc-run.py package 工具化打包
6. **收尾**: 使用 ohc-run.py finish 完成归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码下载超时 | 中国大陆网络直连 GitHub 受限 | 使用 ghfast.top 镜像加速下载 |
| 2 | init-build 无法自动识别 Go 项目 | 软件注册表中无 livekit 条目 | 手动指定 --url 参数，修正 BUILD_SYSTEM 为 custom |
| 3 | 标准构建驱动不支持 Go 项目 | driver.py 仅支持 autotools/cmake/meson/makefile/perl/python | 手动执行 Go 编译命令并创建 staging 目录 |

## 源码修改

无源码修改。Go 项目 CGO_ENABLED=0 编译为纯静态二进制，无需修改源码适配 OHOS。

## 依赖版本

- Go 1.26.4 (arm64)
- 无 C/C++ 依赖（CGO_ENABLED=0）

## 验证结果

```bash
livekit-server --version
# 输出: livekit-server version 1.13.1

file livekit-server
# 输出: ELF executable, 64-bit LSB arm64, static, BuildID=..., stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| livekit-1.13.1-ohos-aarch64.tar.gz | 48259KB (~47MB) | 主预编译包（含 livekit-server） |
| livekit-1.13.1-ohos-aarch64-debug.tar.gz | 77KB | 调试符号包 |

## 注意事项

- livekit 是 Go 语言编写的实时音视频服务器，CGO_ENABLED=0 编译为纯静态二进制
- 由于是静态二进制，无需收集外部共享库依赖（step4 collect_deps 结果为 0）
- 无需设置 RPATH（静态二进制不依赖外部 so）
- GOPROXY=https://goproxy.cn,direct 为中国大陆必需配置
- 部署路径: /storage/Users/currentUser/usr/local/bin/livekit-server
---

**编译结束**: 2026-06-11 14:32
**最终状态**: published
