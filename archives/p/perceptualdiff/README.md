# perceptualdiff

## 简介
perceptualdiff 是一个图像比较工具，使用基于人眼感知的图像度量（Yee 感知度量，Journal of Graphics Tools 2004）判断两张图片是否"看起来相同"，常用于渲染/图形程序的回归测试。项目同时提供 `pdiff` 库与 `perceptualdiff` 命令行工具。

## 功能概述
- 比较两张图片（PNG/TIFF/BMP/JPEG 等，经 FreeImage 加载），输出 PASS/FAIL 与差异像素数
- 可调参数：视场角 `--fov`、阈值像素 `--threshold`、gamma、白点亮度 `--luminance`、色彩权重 `--colorfactor`
- 支持降采样 `--downsample`、尺寸缩放 `--scale`、只比较亮度 `--luminanceonly`、误差求和 `--sum-errors`
- 可输出差分图 `--output o`
- 提供库 API：`pdiff::read_from_file` / `pdiff::yee_compare` / `RGBAImage::write_to_file`（`#include <perceptualdiff/metric.h>`）
- OpenMP 并行加速（OHOS 上实测启用）

## OHOS 适配
- 构建系统为 CMake，配方使用 CMakeToolchain/CMakeDeps，交叉编译目标 aarch64-linux-ohos
- 唯一补丁 `0001-cmake-ohos-conan-adaptation.patch`：
  - `cmake_minimum_required` 抬到 3.5 并前移（CMake 4.x 拒绝 < 3.5）
  - `CMAKE_BUILD_TYPE` 不再被上游硬编码 Debug 覆盖
  - FreeImage 改走 Conan 提供的 `freeimage::freeimage` imported target
  - 补全 `pdiff` 静态库与公共头文件的安装规则（可供库方式消费）
- 图像 IO 依赖 FreeImage：直接使用制品仓成品包 `freeimage/3.18.0`，未重写 IO 后端
- 上游回归套件 `test/run_tests.bash`（7 个图像对 + 19 个 CLI 断言）在 OHOS 上原样全通过，未修改任何上游测试文件
- 命令行工具链接后无 RPATH，运行时依赖 `conanrun` 环境提供 `libfreeimage.so.3` 路径

## 依赖关系
- 编译/运行依赖：`freeimage/3.18.0`
- 运行时：`libc++`（OHOS 系统库）、`libfreeimage.so.3`（Conan 包内）

## 参考资料
- 上游仓库：https://github.com/myint/perceptualdiff
- 度量论文：Hector Yee, "A Perceptual Metric for Production Testing", Journal of Graphics Tools 9(4), 2004
