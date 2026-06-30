# GStreamer for HarmonyOS

## 概述

GStreamer 在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**可用版本**:
- **1.28.3** (最新稳定版): 使用 meson 构建系统，需修复 Python 脚本执行问题

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | GStreamer |
| 官网 | https://gstreamer.freedesktop.org/ |
| 下载 | https://gstreamer.freedesktop.org/data/src/gstreamer/ |
| 许可证 | LGPL |

## 版本状态

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 1.28.3 | built | meson | 最新稳定版，需修复 Python 脚本执行 |

## GStreamer 1.28.3 编译

### 编译步骤

```bash
# 1. 下载源码
curl -k -L -o gstreamer-1.28.3.tar.xz \
  "https://gstreamer.freedesktop.org/data/src/gstreamer/gstreamer-1.28.3.tar.xz"

# 2. 解压
tar -xf gstreamer-1.28.3.tar.xz
cd gstreamer-1.28.3

# 3. 配置（使用 meson）
CC=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang \
CXX=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++ \
meson setup build --prefix=~/usr/local \
  --buildtype=release \
  -Dnls=disabled \
  -Dexamples=disabled \
  -Dtests=disabled \
  -Dbenchmarks=disabled \
  -Ddoc=disabled \
  -Dintrospection=disabled \
  -Dgst_parse=false

# 4. 编译
ninja -C build

# 5. 安装（DESTDIR 模式）
DESTDIR=~/tmp/test-install-gstreamer-1.28.3 ninja -C build install
```

### 关键问题

1. **Python 脚本执行权限**
   - HMDFS/SELinux 环境下 Python 脚本无法直接执行
   - 需修改 meson.build，使用 python3 解释器调用脚本

2. **glib-mkenums 工具**
   - 需通过 python3 间接调用 glib-mkenums

### 依赖

- glib-2.0 (2.88.0+)
- meson (1.4+)
- ninja