# libpng 1.6.58 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

autotools(非 CMake：避 CMake 在 OHOS 的无-SONAME 坑 ML-0035，libtool 自管 SONAME libpng16.so.16)。zlib 经 AutotoolsDeps 注入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: error: cannot guess build type | uname -s=HarmonyOS，config.guess 不认 | uname-shim |
| 2 | AC_CHECK_LIB([z]) 找不到 zlib | 需注入 zlib 的 -I/-L/-lz | --autotools-deps(AutotoolsDeps+PkgConfigDeps)；native 编译 conftest 链接探测通过 |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- zlib/1.3.1.1

## 验证结果

- 真机 conan create + dlopen libpng16.so 通过
