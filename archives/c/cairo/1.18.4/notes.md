# cairo 1.18.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-07
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built（真机 conan create -pr ohos-native 通过）

## 编译步骤

meson；依赖全经 conan pkg-config 提供；wrap_mode=nodownload 禁 meson 偷下子项目。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson ar not found | conan 不写 ar 进 native file | 注入 ar/ranlib 到 native file |
| 2 | 链接 libcairo.so 报 z_errmsg recompile with -fPIC | 远端 zlib 是非-PIC 静态 libz.a | 改用本仓 fPIC 版 zlib(见 z/zlib/1.3.1.1) |
| 3 | dlopen libcairo.so Permission denied | meson install 重写 rpath → 自签失效 | package() 后 binary-sign-tool -selfSign 重签 |
| 4 | cairo 源码从 gitlab 47MB 归档下载超时 | 设备到 gitlab.freedesktop.org 大文件网络不稳 | 改用 cairographics.org 官方 .xz；source() 优先用预推到 ~/Download 的暂存件 |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- pixman/0.46.4
- libpng/1.6.58
- freetype/2.14.3
- fontconfig/2.18.1
- zlib/1.3.1.1

## 验证结果

- 真机 conan create + dlopen libcairo.so 通过(SONAME libcairo.so.2)；全链 7 包 ALL_PASS
