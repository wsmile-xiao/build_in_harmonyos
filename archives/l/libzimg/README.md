# libzimg (zimg)

zimg 是一个图像处理库（缩放、色彩空间转换、深度转换），提供简单、线程安全的 C/C++ API，是 vapoursynth 生态的核心依赖。

- 上游：https://github.com/sekrit-twc/zimg
- 许可证：WTFPL
- 构建系统：Autotools（本配方走完整 bootstrap + configure + make + make check 上游测试闭环）
- 依赖：无（纯 C++ 数学库，线程/pthread 由系统提供）

仓内另有 `archives/z/zimg/3.0.6`（同上游源的 direct clang++ 直编配方，未跑上游测试，制品仓包名 `zimg/3.0.6`）。本目录是平台任务 #13534 的 `libzimg` 包：autotools 标准构建 + 上游 gtest 单元测试真跑（122 用例），两个包名并存互不冲突。
