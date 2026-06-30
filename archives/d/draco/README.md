# draco — 3D 几何压缩库

## 软件简介

**draco** 是 Google 开发的用于压缩和解压缩 3D 几何网格和点云的库。它可以显著减少 3D 图形数据的大小，同时保持视觉质量，非常适合网络传输和存储优化。

### 主要功能
- 3D 网格压缩与解压缩
- 点云数据压缩
- 支持多种格式（OBJ, PLY, STL）
- 高压缩率（可达 90% 以上）

### 应用场景
- WebGL / WebAssembly 应用
- AR/VR 内容传输
- 3D 游戏资源优化
- 科学数据压缩

## 编译信息

| 项目 | 内容 |
|------|------|
| 版本 | 1.5.7 |
| 构建系统 | cmake |
| 编译器 | Clang 15.0.4 |
| 编译日期 | 2026-05-20 |
| 状态 | ✅ 已发布 |

## 安装说明

### 预编译包安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- draco 1.5.7
```

### 安装验证
```bash
draco_encoder --help
draco_decoder --help
pkg-config --modversion draco
```

## 使用示例

### 编码（压缩）
```bash
# 将 OBJ 文件压缩为 DRC 格式
draco_encoder -i input.obj -o output.drc

# 高压缩率（级别 10）
draco_encoder -i input.obj -o output.drc -cl 10

# 指定量化精度
draco_encoder -i input.obj -o output.drc -qp 14 -qt 12
```

### 解码（解压缩）
```bash
# 将 DRC 文件解压缩为 OBJ 格式
draco_decoder -i input.drc -o output.obj
```

### 库调用（C++）
```cpp
#include <draco/compression/encode.h>
#include <draco/compression/decode.h>

// 编码
draco::Encoder encoder;
encoder.SetEncodingOptions(options);
draco::EncoderBuffer buffer;
encoder.EncodeMesh(mesh, &buffer);

// 解码
draco::Decoder decoder;
auto decoded_mesh = decoder.DecodeMesh(buffer.data(), buffer.size());
```

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.5.7 | ✅ published | 2026-05-20 |

## 参考资料

- 官方仓库: https://github.com/google/draco
- 文档: https://google.github.io/draco/
- 构建指南: BUILDING.md
- CMake 配置: CMAKE.md