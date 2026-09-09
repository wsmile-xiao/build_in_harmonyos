# png++

png++ 是对 libpng 的 header-only C++ 封装，提供类型安全的像素、图像读写、颜色空间转换和流式生成接口。

## 版本

- 0.2.10（2026-09-07）— built ✅

## HarmonyOS PC 适配

- 使用 OHOS Clang 提供的通用字节序宏，补齐 musl 平台检测。
- 以 `png/0.2.10` Conan 引用归档，对应 Conan Center 的 `pngpp/0.2.10`。
- header-only 包安装 29 个头文件，公开 CMake 目标为 `png::png`。
- 精确依赖 `libpng/1.6.58.2`。
- 已完成 arm64 OHOS Conan 交叉编译/链接，以及 HarmonyOS 6.0 x86_64 虚拟机运行测试。

## 使用

```cpp
#include <png++/png.hpp>

png::image<png::rgb_pixel> image(64, 64);
image.write("output.png");
```

使用 CMake 时链接 `png::png`，libpng 依赖由 Conan 自动传递。

## 参考资料

- 官网：https://www.nongnu.org/pngpp/
- Savannah：https://savannah.nongnu.org/projects/pngpp
