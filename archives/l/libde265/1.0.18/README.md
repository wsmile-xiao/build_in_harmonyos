# libde265 1.0.18

**H.265/HEVC视频解码库**

libde265 是一个开源的H.265/HEVC视频编解码器实现，专注于解码功能。

## 特性

- 完整的H.265/HEVC解码支持
- 多线程解码能力
- 高性能优化（ARM/SSE汇编）
- 简洁的C API

## 编译信息

- **构建系统**: cmake
- **编译器**: clang 15.0.4
- **目标平台**: HarmonyOS aarch64
- **许可证**: LGPL-3.0-or-later

## 安装位置

- 库文件: lib/libde265.so
- 头文件: include/libde265/
- 工具: bin/dec265

## 使用说明

```bash
# 设置库路径（如需要）
export LD_LIBRARY_PATH=/path/to/lib:$LD_LIBRARY_PATH

# 使用dec265解码H.265视频
dec265 input.h265 -o output.yuv
```

## 集成到项目

```cmake
find_package(libde265 REQUIRED)
target_link_libraries(your_target libde265)
```

## 相关链接

- 主页: https://github.com/strukturag/libde265
- 文档: https://github.com/strukturag/libde265/wiki