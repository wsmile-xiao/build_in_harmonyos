# libgd2

## 简介
GD Graphics Library — 开源图像处理库。本配方（conan 包名 `libgd2`）适配核心内存图像 C API：
真彩色/调色板图像创建、绘制、像素操作与内置格式编解码（GIF/GD/GD2/WBMP/BMP 等）。

## OHOS 适配
- CMake 构建，默认静态库，零外部依赖
- PNG/JPEG/TIFF/WebP/AVIF/HEIF/XPM/Freetype/Fontconfig 等可选栈首轮关闭（`requires` 为空）
- 上游测试常开：`build()` 在可运行目标机执行 `ctest --output-on-failure`（约 79 项）
- CLI helper 与 docs 首轮不打包（未经验证）

## 依赖
- 编译依赖：无
- 运行依赖：无（`libm` 由配方自动声明）

## 功能验证
```bash
conan create archives/l/libgd2/2.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考
- 官方网站：https://libgd.github.io/
- GitHub：https://github.com/libgd/libgd
