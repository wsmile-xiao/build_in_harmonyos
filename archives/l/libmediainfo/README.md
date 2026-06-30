# libmediainfo 26.05 — OpenHarmony 编译记录

## 基本信息
- **软件**: libmediainfo
- **版本**: 26.05
- **构建系统**: cmake
- **目标平台**: ohos-aarch64 (HarmonyOS)
- **编译状态**: built
- **编译日期**: 2026-05-26

## 软件简介
libmediainfo 是 MediaInfo 库的核心组件，提供多媒体文件元数据解析功能。它支持读取视频、音频、图片等多种媒体格式的技术信息。

### 主要功能
- 解析多媒体文件元数据（编码、分辨率、时长等）
- 支持多种媒体格式：MP4、MKV、AVI、MP3、FLAC 等
- 提供 C/C++ API 和静态库
- 跨平台支持

## 编译指导

### 前置要求
- HarmonyOS/OpenHarmony aarch64 系统
- clang 编译器
- cmake 构建工具
- zlib 1.3.1
- libzen 0.4.41

### 编译步骤（快速）
```bash
# 1. 安装依赖
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libzen 0.4.41

# 2. 下载源码
wget https://mediaarea.net/download/source/libmediainfo/26.05/libmediainfo_26.05.tar.xz
tar xf libmediainfo_26.05.tar.xz

# 3. 进入构建目录（关键！源码结构嵌套）
cd MediaInfoLib/Project/CMake
mkdir build && cd build

# 4. Configure
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
         -DCMAKE_PREFIX_PATH=$HOME/usr/local \
         -DZLIB_ROOT=$HOME/usr/local

# 5. 编译
make -j4

# 6. 安装
make install
```

### 特殊说明
1. **源码结构嵌套**：tarball 包含 MediaInfoLib/Project/CMake 目录，必须从 Project/CMake 目录运行 cmake
2. **静态库**：libmediainfo 只生成静态库（.a），无共享库和可执行文件
3. **依赖路径**：需要通过 cmake 参数或 PKG_CONFIG_PATH 指定 zlib 和 libzen 路径

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 干净构建 | ⚠️ 警告 | Python subprocess 平台限制，手动验证通过 |
| G1 二进制完整性 | ✅ PASS | 静态库完整 |
| G2 功能可用性 | ✅ PASS | pkg-config 正常 |
| G3 可移植性 | ✅ PASS | RPATH/签名正常 |
| G4 档案完整性 | ✅ PASS | 文件完整 |

## 已知限制
- 仅静态库，无可执行文件
- 编译需从 Project/CMake 目录运行 cmake
- G0 干净构建验证因平台限制显示警告（实际已手动验证）

## 依赖版本
| 软件 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1 | 基础库 |
| libzen | 0.4.41 | MediaInfo 基础库 |

## 产物信息
- **静态库**: libmediainfo.a (90MB)
- **头文件**: MediaInfo/*.h
- **pkg-config**: libmediainfo.pc

## 验证方法
```bash
# 验证 pkg-config
pkg-config --modversion libmediainfo
# 输出: 26.05

# 验证静态库
ls ~/usr/local/lib/libmediainfo.a
```

---

**归档日期**: 2026-05-26