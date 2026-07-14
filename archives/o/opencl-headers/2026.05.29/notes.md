# opencl-headers 2026.05.29 编译笔记（HarmonyOS PC）

## 定位
- 纯头文件库（header-only），产出 include/CL/ 下的 OpenCL API 头文件。

## 关键适配
- 无需编译 .so，无需签名，无需 OHOS toolchain
- package() 直接 copy 源码 CL/ 目录下的 *.h 到 include/CL/
- 平台检测保留（R32 规程要求）

## 状态
pending — 配方已写，待鸿蒙 PC 真机 conan create + test 验证
