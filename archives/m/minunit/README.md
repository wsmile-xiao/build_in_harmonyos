# minunit

## 简介
minunit 是 siu（David Siñuela Pastor）维护的极简单元测试框架：整个库只有
一个头文件 `minunit.h`，提供 MU_TEST / MU_TEST_SUITE 测试定义宏、MU_RUN_TEST /
MU_RUN_SUITE 驱动宏、mu_check / mu_assert / mu_assert_int_eq / mu_assert_double_eq /
mu_assert_string_eq 五个断言宏 + mu_fail、MU_REPORT 统计输出（含 real/proc 计时）
与 MU_EXIT_CODE（= 失败计数）返回。零依赖（仅 C99 标准库 + POSIX 计时器头）。

## OHOS 适配
- **构建系统**: 无（header-only；上游根目录无 CMakeLists/Makefile，ci/Makefile
  仅为官方 CI 编译 example 的辅助入口）
- **依赖**: 无（W0 实测零依赖）
- **产物**: 仅 `include/minunit.h`，CMake 目标 `minunit::minunit`，
  system_libs = m（mu_assert_double_eq 用 fabs/log10）

## 上游测试
官方 CI 入口 `.travis.yml` / `appveyor.yml` script：`(cd ci && make && ./check_example.sh)`
— 编译 `minunit_example.c`（11 用例 / 11 断言，6 个故意失败演示用例）并断言
**退出码 == 6** 即 PASS（非零退出码是官方 PASS 判据）。配方 build() 内真跑同款。

## 依赖
- 无

## 版本
| 版本 | 状态 |
|------|------|
| 0.0-git20230524 | built（2026-10-02） |
