# smhasher 1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游自带 src/CMakeLists.txt）
- 编译日期: 2026-09-15
- 编译器: clang/clang++
- 状态: built（首轮工作树，待 HMBS 真机预检验证）

## 编译步骤

1. 源码下载：aappleby/smhasher 固定 commit 快照 07bb4de（与仓内 MurmurHash3/0.0.1 同快照、可复现）。
2. 打补丁：0001 提升 CMake 最低版本 2.4→3.15；配方 source() 用内容锚定替换向 main.cpp 注入 `--selftest-only` 速检开关（曾为 0002 补丁，因手写 hunk 行号 326 与上游实际 550 不符导致无法应用，改用 replace_in_file）。
3. `cmake.configure(build_script_folder=<source>/src)` → `cmake.build()`（构建 SMHasherSupport 库 + SMHasher 主程序）。
4. `build()` 内运行 `SMHasher --selftest-only`：上游 SelfTest 对 g_hashes[] 全部 25 个条目做固定验证值检查（3 个 donothing 基准 + 22 个真实哈希）；第 26 个交付哈希 MurmurHash1 由 test_package 覆盖。
5. `package()` 手工 copy：全部 `src/*.h` → include；构建产物 `.a`/`.so` → lib（上游无 install 规则；不安装测试主程序）。
6. test_package：ctest 运行 test_vectors（13 断言）+ test_hashes（38 断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 release/tag，版本 1.0 无官方归档 | SMHasher 是 git-only 仓库 | 引用固定 commit tarball（07bb4de，与 MurmurHash3/0.0.1 同快照，sha256 已被 sibling 配方验证） |
| 2 | 上游 `cmake_minimum_required(VERSION 2.4)` 在新 CMake 上配置失败 | CMake 4.x 移除了对 <3.5 的兼容 | 0001 补丁提升到 3.15（纯版本号改动，无平台宏） |
| 3 | SMHasher 主程序默认跑数小时级随机分布套件，不适合 conan create | main() 写死 g_testAll=true | 0002 补丁加 `--selftest-only` 开关，自检后直接退出（平台无关，与 OHOS 无关） |
| 4 | 上游 CMakeLists 没有 install() 规则 | 上游只管构建，不管安装 | package() 用 copy() 手工安装库与头文件 |

## 源码修改

- `patches/0001-src-cmakelists-minimum-version.patch`：CMake 最低版本 2.4→3.15。
- ~~`patches/0002-src-main-selftest-only-flag.patch`~~（已删除）：`--selftest-only` 改由 conanfile `source()` 经 `replace_in_file` 注入（锚定 `#include <time.h>` 与 `SelfTest();` 后空行，无行号依赖）；同样附带 `#include <string.h>`。
- 两处均为可移植性补丁，未引入 `__OHOS__` 平台宏。

## 依赖版本

无外部依赖，纯 C/C++。

## 验证结果

```bash
# 待 HMBS 真机预检（conan create）：SMHasher --selftest-only + ctest（test_vectors/test_hashes）
```

## 注意事项

- 与 MurmurHash3/0.0.1 同源（同一上游仓库、同一 commit 快照），但交付物不同：本包交付全部 26 个哈希实现的 SMHasherSupport 库（g_hashes[] 25 项 + MurmurHash1）。
- 数小时级随机分布套件（avalanche/cyclic/sparse/permutation/window/zeroes/seed）是 printf 统计分析、无通过率计数，未在门禁内运行；确定性验证部分（SelfTest 25 项 + test_package 内 MurmurHash1 与 51 断言）全量运行。
- 纯库包：不安装 SMHasher 测试主程序，无需 commands.json。
