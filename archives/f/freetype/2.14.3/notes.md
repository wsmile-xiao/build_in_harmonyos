# freetype 2.14.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

autotools；禁全部可选依赖(harfbuzz 与 freetype 循环，须先建无 hb 版)→ 零外部依赖干净节点。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: error: cannot guess build type | 设备 uname -s=HarmonyOS，config.guess 不认 | recipe 加 uname-shim(build() 注入伪 uname 返回 Linux/aarch64) |
| 2 | 消费方(fontconfig/cairo) freetype2 版本判为 2.14.3 < 21.0.15 失败 | freetype2.pc 的 Version 是 libtool 号 26.6.20(version_info=26:6:20)，conan 默认写 recipe 版本 2.14.3 | cpp_info.set_property("system_package_version","26.6.20") |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- 无 conan 依赖（仅系统库）

## 验证结果

- 真机 conan create + dlopen libfreetype.so 通过
