# libwacom 2.13.0 适配笔记

## 编译环境
- 构建系统: meson (1.5.x)
- 编译日期: 2026-09-25
- 编译器: clang 15 (OHOS SDK, aarch64-linux-ohos)
- 状态: built
- worktree: ~/huawei/worktrees/j669539/libwacom-2.13.0

## 软件简介

libwacom 是 Wacom 数位板识别库：data-driven 数据库（data/*.tablet +
stylus.dict），提供 libwacom_database_new/libwacom_new_from_name 等 API，
供 GNOME/Wayland 输入栈识别数位板型号与特性（按键/触控环/压感笔列表）。

## 依赖（W0，R35 conan download 口径核验）

- libgudev/238 ✅（提供 gudev-1.0.pc）
- libevdev/1.13.7 ✅（提供 libevdev.pc）
- glib/2.84.0.1 ✅（libgudev 传递依赖；PkgConfigDeps 生成 glib-2.0.pc）

## 适配要点

1. **tests=enabled**：上游 C 测试（test-load/test-dbverify/
   test-tablet-validity/test-stylus-validity + 无条件 test-ltversion）
   在本机 arm64 OHOS 通过 `meson test` 真跑。
2. **pytest 套件不注册**：test_data_files.py/test_libwacom.py/
   test_svg.py/test_udev_rules.py 需要 find_program('pytest-3','pytest')
   + pymod.find_installation(modules:['libevdev','pyudev','pytest'])——
   OHOS 环境无这些 python 模块，meson configure 阶段就会因
   modules 检查失败而中止。豁免理由与本地补跑尝试见 PR 正文。
3. **files-in-git 豁免**：该测试 find_program('test/check-files-in-git.sh')
   要求源码是 git checkout（逐文件核对 git ls-files），tarball 源码
   形态必然失败，非平台问题。
4. **LIBWACOM_DATA_DIR**：上游测试与消费者通过该 env 定位 DB
   （test/test-load.c 同款机制）；test_package 指向安装的 share/libwacom。
5. **签名**：package 后 binary-sign-tool 签 .so（libgudev/glib 先例）。
6. **ar/ranlib/pkg-config 注入**：conan_meson_native.ini 补齐
   （libgudev 238 配方同款）；glib pc 文件补 glib_mkenums 变量
   （json-glib/libgudev 先例）。

## 上游测试（N 申报口径）

meson.build 在 tests=enabled 形态下注册：
- test-load（ecm 风格 data-driven 加载测试）
- test-dbverify
- test-tablet-validity
- test-stylus-validity
- test-ltversion（无条件注册，非 tests 开关控制）
- files-in-git（无条件注册；git 树检查，tarball 形态豁免）
- pytest × 4（test_data_files/test_libwacom/test_svg/test_udev_rules；
  需 python 模块，OHOS 不可注册）

本机（arm64 OHOS）conan create 内 meson test 实跑 5 项 C 测试；
files-in-git 与 pytest 4 项豁免（逐项理由见 PR 正文减少原因段）。
