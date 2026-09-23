# gtest 1.17.0.2 适配笔记（元数据修复版）

## 编译环境

- 构建系统: CMake（C++17）
- 平台任务: contrib-13504（gtest 1.17.0.2），claimer Ember5843，认领 2026-09-15T09:47Z
- 目标平台: HarmonyOS PC arm64（clang 15 / libc++），本机原生构建
- 依赖: **无外部依赖**（上游测试套件自带）
- 上游: https://github.com/google/googletest （tag v1.17.0）
- 源码 sha256: `65fab701d9829d38cb77c14acdc431d2108bfdbf8979e40eb8ae567edf10b27c`
- 语言实测（R47 lang-preflight）: C++ 测试框架（.cc/.h 主体）

## 本版本修复内容（审查员 clancyxie 对 pistache #9605 的前置要求）

`package_info()` 为四个分量补齐 **pkg_config_name**（gtest / gtest_main / gmock / gmock_main）：

- 分量声明与 `GTest::*` cmake 目标名在 1.17.0.1 已具备；
- 缺 pkg_config_name 时 conan 生成的 `.pc` 分量名不带该属性，下游以 pkg-config
  探测 `gtest_main` 时找不到 → 构建失败；
- 本 PR **不改变构建产物**，仅补元数据。

## 上游测试面（与 1.17.0.1 基线一致，源码零变化）

- `gtest_build_tests=ON` + `gmock_build_tests=ON`：googletest + googlemock 编译出
  65 个测试二进制（97 个测试源文件，数千 TEST 用例）
- 1.17.0.1 期真机实跑 59/65 通过；6 项未通过为框架特定编译配置/场景要求，已在彼 PR 归因
- 本版本源码与构建配置零变化，该基线继续有效

## 消费者测试

test_package 链接 `GTest::gtest_main` 与 `GTest::gmock`，执行断言与 HasSubstr 匹配器（2 项）。

## 状态

- [x] 配方（conanfile.py / conandata.yml / patches / test_package）
- [x] manifest.yaml + notes.md（本次补齐——审查员 clancyxie 2026-09-18 指出缺失）
- [x] 设备实机 conan create + conan-verify
- [x] push / PR（#10179）/ 平台绑定
