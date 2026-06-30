# libaom - AV1 视频编解码器参考实现

## 项目简介

libaom 是 Alliance for Open Media (AOM) 开发的 AV1 视频编解码器的官方参考实现。AV1 是一种开源、免版税的视频编码格式，旨在提供比现有编解码器（如 H.265/HEVC）更高的压缩效率。

## 技术特点

- **AV1 编码**：支持高效的 AV1 视频编码
- **AV1 解码**：完整的 AV1 视频解码支持
- **纯静态库**：编译为静态库（libaom.a），便于集成
- **跨平台**：支持多种平台和架构

## 主要用途

libaom 是 libavif（AV1 图像格式库）的关键依赖，用于：
- AVIF 图像的编码和解码
- 视频流处理
- 媒体转换工具

## 已编译版本

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|---------|---------|
| 3.8.0 | ✅ published | CMake | 2026-05-19 |

## 编译要点

### 关键配置参数

```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DENABLE_TESTS=OFF \
      -DENABLE_EXAMPLES=OFF \
      -DENABLE_DOCS=OFF \
      -DCONFIG_RUNTIME_CPU_DETECT=0 \
      ..
```

### 特殊要求

1. **必须使用 CMake 构建**：不支持 autotools
2. **建议在子目录构建**：避免污染源码目录
3. **禁用运行时 CPU 检测**：OpenHarmony 兼容性问题（CONFIG_RUNTIME_CPU_DETECT=0）
4. **禁用测试和示例**：减少编译时间

### 已知问题

- **SSL 证书下载失败**：使用 curl -k 或本地文件解决
- **CMake 平台识别**：HarmonyOS 未被 CMake 识别，回退到 generic target

## 产物清单

每个编译版本的产物包括：

| 文件 | 说明 |
|------|------|
| libaom.a | 静态库 |
| include/aom/*.h | 头文件（10 个） |
| lib/pkgconfig/aom.pc | pkg-config 文件 |

## 依赖关系

libaom 无外部依赖，仅需要：
- cmake（构建工具）
- clang（编译器）
- perl（构建辅助）

## 使用示例

```bash
# 通过 pkg-config 编译链接
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
gcc -o myapp myapp.c $(pkg-config --cflags --libs aom)

# 直接链接
gcc -o myapp myapp.c -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -laom -lm -lpthread
```

## 参考链接

- 官方仓库：https://github.com/aomedia/aom
- 发布页面：https://storage.googleapis.com/aom-releases/
- 文档：https://aomedia.googlesource.com/aom/

## 维护者

OpenHarmony 三方库编译团队

最后更新：2026-05-19