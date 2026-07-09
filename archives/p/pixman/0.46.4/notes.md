# pixman 0.46.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

meson setup(禁 tests/demos/gtk/libpng/openmp) → ninja。核心库仅依赖 libm+pthread 系统库。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 报 Unknown linker: llvm-ar/ar not found | conan MesonToolchain 不把 compiler_executables 的 ar 写进 native file，meson 按 PATH 探归档器失败 | generate() 里 tc.generate() 后手工把 ar/ranlib 注入 conan_meson_native.ini 的 [binaries] |
| 2 | test_package 编译报 pixman-version.h not found | 头装在 include/pixman-1/，pixman.h 内部 #include <pixman-version.h> | cpp_info.includedirs=["include/pixman-1","include"] |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- 无 conan 依赖（仅系统库）

## 验证结果

- 真机 conan create + dlopen libpixman-1.so 通过
