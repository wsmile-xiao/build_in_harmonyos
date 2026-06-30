# PlutoVG

Tiny 2D vector graphics library in C.

## 简介

PlutoVG 是一个轻量级的纯 C 语言 2D 矢量图形库，提供以下功能：
- Canvas 绘图 API（路径、填充、描边）
- 渐变（线性/径向）
- 图像合成与混合模式
- 字体渲染（内嵌 FreeType 简化版）
- 矩阵变换
- PNG 输出

## 已编译版本

| 版本 | 状态 | 日期 | 预编译包 |
|------|------|------|----------|
| 1.3.2 | published | 2026-06-13 | ✅ plutovg-1.3.2-ohos-aarch64.tar.gz |

## 构建信息

- **构建系统**: cmake
- **语言**: C
- **编译器**: clang 15.0.4
- **产物类型**: 静态库 (libplutovg.a)
- **依赖**: 无外部依赖（仅 pthread）

## 安装产物

| 文件 | 说明 |
|------|------|
| `include/plutovg/plutovg.h` | 公共 API 头文件 |
| `lib/libplutovg.a` | 静态库 |
| `lib/pkgconfig/plutovg.pc` | pkg-config 描述文件 |
| `lib/cmake/plutovg/` | cmake 查找模块 |

## 使用方式

### pkg-config

```bash
pkg-config --cflags plutovg   # → -DPLUTOVG_BUILD_STATIC -I.../include/plutovg
pkg-config --libs plutovg     # → -L.../lib -lplutovg
```

### cmake

```cmake
find_package(plutovg REQUIRED)
target_link_libraries(myapp plutovg)
```

## 上游信息

- **主页**: https://github.com/sammycage/plutovg
- **作者**: Samuel Ugochukwu
- **许可证**: MIT
