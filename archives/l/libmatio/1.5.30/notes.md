# matio 1.5.30 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-04
- 编译器: clang/clang++（clang-15，OHOS aarch64 设备工具链）
- 状态: built

## 上游核验
- 上游项目: https://github.com/tbeu/matio（作者 Thomas Beu，matio 官方仓库）
- 1.5.30 tag: https://github.com/tbeu/matio/releases/tag/v1.5.30
- 源码 URL: https://github.com/tbeu/matio/releases/download/v1.5.30/matio-1.5.30.tar.gz
- SHA256: `8bd3b9477042ecc00dd71c04762fa58468e14cccc32fd8c6826c2da1e8bc3107`（与 GitHub API 官方 digest 一致）
- License: BSD-2-Clause（COPYING：Copyright (c) 2015-2026, The matio contributors; 2012-2014 Christopher C. Hulbert）
- 真实依赖（configure.ac:308 `MATIO_CHECK_ZLIB`、:310 `MATIO_CHECK_HDF5`）: zlib + HDF5（MAT v7.3 必需）+ libaec（hdf5 的传递依赖）
- 构建系统: 上游同时支持 autotools 与 CMake，双入口等价（CMake 优先：依赖接线走 CMakeDeps，与 hdf5/netcdf 先例一致）

## 上游测试审计
- test/test_mat.c（4620 行，测试驱动程序）+ test/test_snprintf.c（145 行）
- test/tests/*.at：37 个 .at 文件、**3338 个 AT_SETUP** 用例、5389 个 AT_CHECK 断言
  - 单元/集成测试按格式分组：mat4_*（8 文件）、mat5_uncompressed_*（6）、mat5_compressed_*（6）、mat73_*（10）、
    cell_api / struct_api / subscript_api（3 个 API 级）
  - BE/LE 数据集（test/datasets/ 17 个 .mat 文件、test/results/ 预期输出）由 test_mat 驱动程序消费
- 双入口同源：autotools `make check` 与 CMake `cmake.test()` 都消费 test/tests/*.at（后者经 convert_at_to_ctest.py 转 ctest）
- CMake 路线的 ctest 条目数：**8197**（3338 AT_SETUP 展开为多步链式用例，如 copy→delete→whos 对比）
- 链式用例有顺序依赖：`ctest -I` 分段跑会切断 _1→_N 链导致假失败，须完整顺序跑

## 编译步骤
```bash
conan create archives/l/libmatio/1.5.30 --profile:build default --profile:host ohos-aarch64-device --build=libmatio/1.5.30
```
1. `cmake.configure()`（CMAKE_SYSTEM_NAME=OHOS、MATIO_WITH_HDF5=ON、MATIO_WITH_ZLIB=ON、MATIO_MAT73=ON、MATIO_BUILD_TESTING=ON）
2. `cmake.build()`
3. `cmake.test()` — 上游官方测试（8197 个 ctest 条目）
4. `cmake.install()` + 鸿蒙代码签名（libmatio.so + matdump，binary-sign-tool 经 shutil.which 解析）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan 默认 CMAKE_SYSTEM_NAME="HarmonyOS" 无平台文件 | cmake 只有 Platform/OHOS.cmake | generate() 里带 os 守卫强制 OHOS |
| 2 | 上游测试依赖 Python3（转换 .at → ctest） | cmake/test.cmake find_package(Python3) | OHOS 设备 /data/service/hnp/bin/python3 存在，实测通过 |
| 3 | find_package(HDF5) 命中 CMakeDeps 但 include 为空 | 上游 thirdParties.cmake 目标级联只认 hdf5::hdf5-shared/-static 与 HDF5::HDF5，CMakeDeps 只生成扁平 hdf5::hdf5 | 补丁 0001：thirdParties.cmake 新增 Conan 2 CMakeDeps 分支直接链接 hdf5::hdf5 |
| 4 | 391/8197 个 ctest 条目（readwrite_delete_variables 链）失败 | src/mat.c Mat_mktemp 模板硬编码 /tmp 且缓冲区 21 字节：OHOS /tmp 只读 + 长 TMPDIR 被 snprintf 拒绝 | 补丁 0002：TMPDIR 优先解析 + 缓冲区 PATH_MAX（4096 回退） |
| 5 | package() 签名失败（Error 127） | /data/service/hnp/bin/ 下无 binary-sign-tool（本机装在 /usr/local/bin） | shutil.which 按 PATH 解析，回退 CI 标准路径 |
| 6 | test_package 二进制启动即挂 | 本次 OHOS 实测：不加 LD_LIBRARY_PATH 时加载器找不到 libmatio.so.14 及其 hdf5/zlib 依赖 | test() 用 self.run() 显式注入被测包+依赖 lib 目录（LD_LIBRARY_PATH） |

## 源码修改
- patches/0001-hdf5-conan2-cmakedeps-target.patch（patch_type: conan）
- patches/0002-mktemp-tmpdir-env.patch（patch_type: portability）
两补丁对全新解包源码 `patch -p1 --dry-run` 干净应用，不依赖本地缓存/手工修改。

## 依赖版本
- hdf5/1.14.6（MAT v7.3 支持必需）
- zlib/1.3.1.1（MAT v5 压缩必需）
- libaec/1.1.7（hdf5 传递依赖）
- 三者 OHOS aarch64 二进制均已实测从 ohpcd 拉取

## 验证结果
- 上游测试（口径：3338 AT_SETUP 用例 / 5389 AT_CHECK 断言 / 8197 ctest 执行条目）：
  `100% tests passed, 0 tests failed out of 8197`（ctest 条目 Total 8197 / Pass 8197 / Fail 0 / Skip 0）
- 适配后测试用例总数：**3339**（3338 上游用例 + 1 个 test_package 用例）
- test_package：`100 checks, 0 failures`（程序化生成 MAT 数据，公开 API 消费安装包：
  v4/v5 未压缩/v5 压缩/v7.3 未压缩/v7.3 压缩 5 组回环 × 16 断言 + 错误输入 6 + 长 TMPDIR 删除回归 14）
- ELF 验证：
  - libmatio.so.1.5.30: `ELF shared object, 64-bit LSB arm64`
  - matdump: `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`
- 实机运行：test_libmatio 与 matdump 均在本机 HarmonyOS PC（HongMeng Kernel）真实执行成功

## 知识产出
- E559（草稿）：C 库临时文件模板缓冲区按硬编码 /tmp 路径长度定长计算 → 长 TMPDIR 被拒绝或截断
  （knowledge/drafts/E559-draft-E861.{kv,md}，经 graph add --draft 创建，待主编审核）

## 注意事项
- matio 的 matdump 为可执行文件，已登记 commands.json（R38）；bin/ 下 ELF 须签名。
- MAT v7.3 支持依赖 HDF5；若未来拆出 mat73 开关需同步调整 test_package 的 v7.3 验证。
- 长时间 ctest（8197 条，~15 分钟）在 CI 须整体顺序跑；链式用例（_1→_N）不能分段。

## 最终状态

编译结束（COMPLETED）：conan create 全流程通过——上游 8197/8197 ctest 全过、test_package 100 checks 0 failures、
ELF64 AArch64 验证通过、实机运行通过、补丁对全新源码干净应用、知识草稿 E559 已提交待审。
