# faad2 2.11.2 — OpenHarmony 编译记录

## 基本信息
- 软件: faad2 (Freeware Advanced Audio Decoder 2)
- 版本: 2.11.2
- 构建系统: cmake
- 目标: ohos-aarch64
- 编译状态: ✅ 成功

## 功能简介

faad2 是一个开源的 MPEG-4 和 MPEG-2 AAC 音频解码器，支持:
- AAC-LC (Low Complexity)
- HE-AAC (High Efficiency AAC)
- HE-AAC v2
- AAC-LD (Low Delay)
- AAC-ELD (Enhanced Low Delay)
- DRM (Digital Radio Mondiale) 格式

## 编译指导

### 环境要求
- CMake 3.10+
- C 编译器 (Clang/GCC)

### 编译步骤

```bash
# 配置
cmake -B build -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_BUILD_TYPE=Release

# 编译
cmake --build build -j$(nproc)

# 安装
cmake --install build --prefix $PREFIX
```

### 运行时配置

如需运行 faad 命令，需设置库路径:
```bash
export LD_LIBRARY_PATH=$PREFIX/lib:$LD_LIBRARY_PATH
```

## 补丁清单

无补丁

## 已知限制

1. **无测试套件**: 上游未提供自动化测试
2. **部分库未安装**: libfaad_fixed.so 和 libfaad_drm_fixed.so 未被 CMakeLists.txt 安装

## 功能验证

```bash
# 查看版本
faad

# 查看 AAC 文件信息
faad -i input.aac

# 解码 AAC 到 WAV
faad -o output.wav input.aac
```

## 安装产物

| 文件 | 路径 |
|------|------|
| libfaad.so | lib/ |
| libfaad_drm.so | lib/ |
| faad | bin/ |
| faad.h | include/ |
| neaacdec.h | include/ |
| faad2.pc | lib/pkgconfig/ |
| faad.1 | share/man/man1/ |