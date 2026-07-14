# CharLS

CharLS 是 JPEG-LS 无损/近无损图像压缩标准的 C++ 实现。JPEG-LS 是一种低复杂度、高压缩比的无损压缩标准, 特别适用于医学图像和遥感图像。

## 功能概述
- JPEG-LS 无损压缩/解压缩
- 近无损压缩 (可配置最大误差)
- 支持 8/16 位灰度和彩色图像
- 支持多分量交织 (interleave mode)
- C 和 C++ 双 API
- 无第三方依赖, 仅需 C++14
- 被 DICOM 等医疗影像标准采用

## OHOS 适配
- C++14 库, 无第三方依赖, 构建简单
- CMake 构建为静态库 (默认)
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (OHOS 平台适配)
- 静态库消费者需定义 `CHARLS_STATIC` 宏 (由 package_info 自动添加)

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/team-charls/charls
- JPEG-LS 标准: ITU-T T.87
