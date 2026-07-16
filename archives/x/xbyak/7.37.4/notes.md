# xbyak 7.37.4 编译笔记（HarmonyOS PC）

## 定位
- 纯头文件库（header-only），产出 include/xbyak/ 下的 C++ JIT 汇编器头文件。

## 关键适配
- 无需编译 .so，无需签名，无需 OHOS toolchain
- package() 直接 copy 源码 xbyak/ 目录下的 *.h 到 include/xbyak/
- 平台检测保留（R32 规程要求）
- x86/x64 JIT 汇编器，在 aarch64 上仅验编译（cross_building 跳过运行时）
- test_package 使用 DontSetProtectRWE 避免 mprotect 调用，仅验证 CodeGenerator 可实例化

## 状态
pending — 配方已写，待鸿蒙 PC 真机 conan create + test 验证
