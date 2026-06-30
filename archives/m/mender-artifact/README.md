# mender-artifact

## 简介

mender-artifact 是 Mender IoT 设备管理系统的组件，用于创建和管理 Mender artifacts（软件更新包）。它支持：
- 创建、读取、验证和修改 Mender artifacts
- 支持多种更新类型（应用程序、根文件系统、模块更新）
- 签名和验证 artifacts 的完整性
- 管理设备组更新策略

## 编译版本

- **当前版本**: 4.4.0
- **编译日期**: 2026-06-08
- **构建系统**: Go + Makefile（非autotools）
- **状态**: built（编译成功，已通过G1-G3门禁）

## 编译信息

### 依赖
- Go 1.22.5（必需，用于编译Go源码）
- OpenSSL 1.1.1w（必需，用于签名验证）
- clang 15.0.4（CGO编译器）

### 编译选项
```bash
export PATH=$HOME/usr/local/go/bin:$PATH
export CC=clang
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
export CGO_CFLAGS="-I$HOME/usr/local/include"
export CGO_LDFLAGS="-L$HOME/usr/local/lib"
make build
```

### 特殊说明
1. 这是Go语言项目，不使用autotools构建系统
2. 需要在编译前签名Go工具链的所有可执行文件（ELF签名）
3. Go项目使用CGO，需要C编译器和相应的库
4. OpenSSL库必须通过CGO_CFLAGS和CGO_LDFLAGS指定路径
5. Go项目的install将文件安装到GOPATH/bin，不是DESTDIR
6. 需要手动创建staging目录并复制文件

## 使用方法

```bash
# 查看帮助
mender-artifact --help

# 创建artifact
mender-artifact write rootfs-image --artifact-name my-update \
  --device-type my-device --file-path my-image.mender

# 验证artifact
mender-artifact validate my-update.mender

# 查看artifact信息
mender-artifact read my-update.mender
```

## 许可证

Apache License 2.0

## 官方链接

- 官网: https://mender.io
- GitHub: https://github.com/mendersoftware/mender-artifact
- 文档: https://docs.mender.io