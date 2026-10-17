# picotool 2.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS SDK，clang 15，profile ohos-aarch64）
- conan: 2.29.1（OHOS 适配版），remote ohpcd
- 状态: published

## 编译步骤

1. `conan create archives/p/picotool/2.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
   - `source()`: conan `get()` 下载 picotool-2.3.0.tar.gz + pico-sdk-2.3.0.tar.gz（官方 GitHub URL，sha256 校验）
   - `generate()`: CMakeToolchain + `buildenv_info.prepend("LD_LIBRARY_PATH", <SDK llvm lib>)`
   - `build()`: 兜底注入 LD_LIBRARY_PATH 与 `PICO_SDK_PATH=<source_folder>/pico-sdk`，CMake configure + build
   - `package()`: `cmake.install()`（bin/picotool）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 编译器测试报 "C compiler broken" | SDK lld 的 DT_NEEDED 含 libxml2.so.16（llvm/lib/ 下），不在 loader 默认搜索路径 | generate() 用 `buildenv_info.prepend` 注入 LD_LIBRARY_PATH 进 conanbuild 环境 + build() os.environ 兜底（libseccomp/picotool 2.2.0 先例） |
| 2 | CMake 找不到 pico-sdk（picotool 2.3.0 需要 PICO_SDK_PATH） | pico-sdk 制品仓无包，picotool 构建必需（pico_sdk_version.cmake、src/rp2350/hardware_regs 头文件） | 从上游官方源 vendor 配套版本 2.3.0（conandata.yml `pico_sdk` 条目），build() 设 PICO_SDK_PATH 指向解压目录（2.2.0 先例） |
| 3 | 上游无单元测试套件，R51 测试口径 | 上游验证 = CI workflow 无硬件冒烟 + bdev_test.sh（需真机） | test_package 复刻 .github/workflows/test.yml 无硬件冒烟全量命令；bdev_test.sh 以"需真实 RP2040/RP2350 硬件"记录跳过原因（见 test_package/MANIFEST.yml） |
| 4 | test_package 源内构建产物（UF2/测试二进制/env 脚本）污染归档树；nuke UF2 下载 404 | conan 2 test_package 默认 in-source 构建；上游第三个 UF2 的 release 文件名为 nuke_universal.uf2（本地保存名 flash_nuke.uf2），非 flash_nuke.uf2 | test_package layout() 将 build_folder 重定向到 build/ 子目录（提交前清理）；UF2 下载列表改为 (上游文件名, 本地保存名) 二元组对齐上游 CI |

## 源码修改

无补丁（patches_applied: []）。上游源码零修改，全部适配在配方层完成。

## 依赖版本

- libusb/1.0.27（制品仓 ohpcd 已发布，`conan download` 实测验证）
- pico-sdk/2.3.0（上游官方源 vendor，构建期 PICO_SDK_PATH 方式，非 conan 包）

## 验证结果

- conan-verify 8 道门禁（G0-G4 + L2/L4/L5）：见 reports/
- W3 本地 CI（W2 结构 + R36 依赖 + conan create）：见 `.ci-result.json`
- test_package：ELF 校验 + 上游 CI 同款无硬件冒烟（version 2.3.0 断言 / help / help load|save|erase / info -a ×3 官方 UF2）

## 注意事项

- pico-sdk 版本与 picotool 官方配套（均为 2.3.0）；升级 picotool 时需同步 pico-sdk 配套版本
- picotool 的 USB 设备功能（load/save/erase/reboot）运行时需系统侧 USB 主机权限；纯文件模式（info -a、help、version、elf2uf2）无此依赖
- commands.json 已登记 2.3.0（hicmd 格式，L0k 门禁）
---

**编译结束**: 2026-09-21 17:09
**最终状态**: built
