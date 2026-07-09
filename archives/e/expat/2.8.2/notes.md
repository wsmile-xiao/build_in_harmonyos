# expat 2.8.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

GitHub 源码 tag 归档无预生成 configure → 用 CMake；CMakeLists 在子目录 expat/(build_script_folder="expat")。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xmlparse.c 报 no high quality entropy / dlopen 缺 writeRandomBytes_dev_urandom 符号 | OHOS libc 无 getrandom 符号，expat 默认 EXPAT_WITH_*=OFF 不启用任何熵源 | -DEXPAT_WITH_GETRANDOM=ON(设备 cmake 能检出 getrandom)，由构建系统一致定义，勿手工 -DXML_DEV_URANDOM 造悬空符号 |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- 无 conan 依赖（仅系统库）

## 验证结果

- 真机 conan create + dlopen libexpat.so 通过
