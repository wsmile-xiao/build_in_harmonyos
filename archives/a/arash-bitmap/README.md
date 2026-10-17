# arash-bitmap

The C++ Bitmap Library — 24-bit per pixel bitmap image reader/writer by Arash Partow.

- 官网: http://partow.net/programming/bitmap/index.html
- 上游: https://github.com/ArashPartow/bitmap
- 许可: MIT
- 类型: header-only C++ 库 (单头文件 bitmap_image.hpp, 零外部依赖)

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20260924 | built/published | 首轮适配 (master commit a03765d38698a138dbf162b0cc127fc17d6fc0c2) |

## 能力

+ 24-bit BMP 图像读写
+ 像素/行/列批量编辑、RGB/YCbCr 色彩转换
+ 缩放 (subsample/upsample)、9 种色彩映射、纹理生成 (checkered/plasma)
+ 图形绘制接口 (line/circle/ellipse/rectangle 等)
+ cartesian canvas、PSNR 图像比较、Mandelbrot/Julia 分形

## 适配要点

- 单头文件库：Conan 配方按 header-only 处理 (`package_type=header-library`)
- 上游测试 20/20 通过 (bitmap_test.cpp, 需用库自身 API 生成 image.bmp 夹具)
- 详细见 20260924/notes.md 与 20260924/reports/