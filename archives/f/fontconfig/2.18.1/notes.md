# fontconfig 2.18.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

meson；freetype 经 pkg-config(freetype2)、expat 经 xml-backend。cache-build 关键关闭(免构建期跑 aarch64 fc-cache)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson ar not found | 同 pixman(conan 不写 ar 进 native file) | 注入 ar/ranlib 到 conan_meson_native.ini |
| 2 | dlopen libfontconfig.so Permission denied | meson install 重写 rpath 改动链接后 .so → 链接器自签失效 → XPM 拒 | package() 后 binary-sign-tool -selfSign 重签 |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- freetype/2.14.3
- expat/2.8.2

## 验证结果

- 真机 conan create + dlopen libfontconfig.so 通过
