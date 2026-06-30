# SDL3_ttf

## 简介

SDL3_ttf 是 SDL3 的 TrueType 字体渲染库，提供了在 SDL3 应用程序中渲染 TrueType 字体的功能。它是 SDL2_ttf 的继任者，支持高质量文本渲染和复杂的文本布局。

## OHOS 适配

- 使用 CMake 构建系统
- 需要设置 `CMAKE_PREFIX_PATH` 指向依赖库的安装路径
- 依赖项：
  - SDL3 3.4.8+（必须）
  - Freetype 2.13.3+（必须）
  - HarfBuzz 14.2.0+（必须）
- 可选后端：plutovg、plutosvg（编译时未启用）
- 编译选项：
  - `-DSDLTTF_VENDORED=OFF`：禁用内嵌依赖
  - `-DSDLTTF_SAMPLES=OFF`：禁用示例程序

## 依赖

- SDL3 >= 3.2.6
- Freetype >= 2.10.0
- HarfBuzz >= 2.3.1

## 功能验证

```bash
# 检查库文件
ls -l ~/usr/local/lib/libSDL3_ttf.so
# 检查 pkg-config
pkg-config --modversion sdl3-ttf
# 检查头文件
ls ~/usr/local/include/SDL3_ttf/
```

## 参考

- 官网: https://github.com/libsdl-org/SDL_ttf
- 源码: https://github.com/libsdl-org/SDL_ttf
- 文档: https://wiki.libsdl.org/SDL3_ttf