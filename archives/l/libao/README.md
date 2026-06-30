# libao - Cross-platform Audio Output Library

## 简介

libao 是一个跨平台的音频输出库，提供统一的 API 用于在不同平台播放音频。它支持多种音频输出后端（OSS, ALSA, PulseAudio, ESD 等），通过插件机制实现平台适配。

## 版本信息

- **当前版本**: 1.2.2
- **发布日期**: 2016-11-14
- **源码地址**: https://gitlab.xiph.org/xiph/libao

## 功能特性

- 跨平台音频输出 API
- 插件架构（动态加载音频驱动）
- 支持多种音频后端：
  - OSS (Open Sound System)
  - ALSA (Advanced Linux Sound Architecture)
  - PulseAudio
  - ESD (Enlightened Sound Daemon)
  - ALS, NAS, IRIX, macOS CoreAudio 等

## OpenHarmony 适配

### 已编译版本
- **版本**: 1.2.2
- **状态**: published
- **编译日期**: 2026-05-20
- **架构**: aarch64-ohos

### 平台适配内容
1. **config.guess/config.sub**: 添加 aarch64-ohos 平台识别
2. **os_types.h**: OHOS 平台类型定义
3. **ltmain.sh**: libtool 适配 OHOS 链接器
4. **构建 hook**: autogen.sh 生成 configure 脚本

### 编译产物
- `libao.so.4.1.1`: 主库文件（51KB）
- `liboss.so`: OSS 音频插件（22KB）
- 头文件: ao.h, plugin.h, os_types.h

### 使用方法

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/.../install.sh | sh -s -- libao 1.2.2

# pkg-config 验证
pkg-config --modversion ao  # 输出: 1.2.2

# 编译链接
gcc -o myapp myapp.c $(pkg-config --cflags --libs ao)
```

## 依赖

- **无外部库依赖**: 仅依赖系统 libc
- **构建依赖**: autotools (automake, autoconf, libtool)

## 注意事项

1. 源码包缺少 configure 脚本，需先运行 autogen.sh
2. 当前仅编译 OSS 插件（其他插件缺少对应音频库依赖）
3. 无测试套件（make check），验证依赖 pkg-config 和 ELF 检查

## 归档位置

`archives/l/libao/1.2.2/`

## 相关链接

- [官方文档](https://xiph.org/ao/)
- [API 参考](https://xiph.org/ao/doc/)
- [源码仓库](https://gitlab.xiph.org/xiph/libao)