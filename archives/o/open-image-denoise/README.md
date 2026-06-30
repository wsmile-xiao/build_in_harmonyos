# open-image-denoise

Open Image Denoise (OIDN) 是 Intel 开发的高性能图像降噪库，支持光线追踪渲染器的降噪。

- **Homepage**: https://github.com/OpenImageDenoise/oidn
- **License**: Apache-2.0
- **Category**: graphics
- **Version**: 2.4.1

## 注意事项

- 当前编译禁用了 CPU 设备（OIDN_DEVICE_CPU=OFF），因为 ISPC 编译器无法在 HarmonyOS 上执行
- 库包含完整的 API（oidn.h, oidn.hpp）和核心库，但不含 CPU 降噪设备实现
- 依赖 TBB 2021.13.0