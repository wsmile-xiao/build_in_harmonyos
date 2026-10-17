# hsluv-c

[HSLuv / HPLuv](https://www.hsluv.org/) 色彩空间转换的 C 实现。

HSLuv 是一种"人眼友好"的 HSL 色彩空间：在相同的感知明度与饱和度下，颜色之间的感知差异比普通 HSL 更均匀。本库提供 HSLuv ↔ RGB 与 HPLuv ↔ RGB 的双向转换。

## OHOS 适配

- **构建系统**: CMake（上游 `add_library(hsluv-c STATIC)`，无 install 规则）
- **依赖**: 无（仅 libm）
- **适配要点**:
  - 上游 `cmake_minimum_required(VERSION 3.1)` 与 CMake 4.x 不兼容，配方 configure 注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（见知识 E187/E103）
  - 配方手动打包 `hsluv.h` + `libhsluv-c.a`（R26 静态交付）
  - 源码通过 ghfast.top 镜像通道下载（见知识 E017），conandata 保持官方 URL

## 功能验证

```bash
# 消费者验证（test_package 内）
./test_hsluv_consumer   # rgb2hsluv/hsluv2rgb 与官方 #ff0000 快照参考值对照
./test_hsluv_ohos       # 鸿蒙专项：灰度轴/端点/往返闭包/网格恢复

# 上游测试（acutest 4 用例 × 4096 快照）
./test_hsluv
```

## 参考

- 官网: https://www.hsluv.org/
- 源码: https://github.com/hsluv/hsluv-c
- 版本: 1.0.0