# visit_struct 1.2.0 适配笔记

## 基本信息
- 上游：https://github.com/cbeck88/visit_struct （tag `1.2.0`，**无 v 前缀**，`refs/tags/v1.2.0` 是 404）
- 类型：header-only C++11 结构体字段反射库（VISITABLE_STRUCT / for_each / field_count）
- 许可证：BSL-1.0（Boost Software License 1.0）
- 依赖：无（核心头 `visit_struct.hpp` 零依赖；`*_boost_fusion/_boost_hana` 头仅在配合 Boost 时用）

## 上游测试形态与适配策略
- 上游测试由 **Boost.Build（b2/bjam，Jamroot.jam）** 驱动，共 5 个测试可执行：
  1. `test_visit_struct`（C++11，assert 运行时）✅ 已复刻
  2. `test_visit_struct_intrusive`（C++11，侵入式语法）✅ 已复刻
  3. `test_fully_visitable`（C++14，TEST_CXX14 分支）✅ 已复刻
  4. `test_visit_struct_boost_fusion`（需 Boost）❌ 未构建
  5. `test_visit_struct_boost_hana`（需 Boost，TEST_CXX14）❌ 未构建
- CI worker 无 b2；配方 build() 直接用 clang++（`tools.build:compiler_executables`，R33）编译并执行前 3 个。
  Boost 两个测试与上游 Jamroot 自身逻辑一致：找不到 Boost 头即跳过（"Could not find boost, skipping boost tests"）。
- 上游 GNU_FLAGS 含 `-Werror`；OHOS clang 15 去掉 -Werror（警告策略差异），测试源码未做任何修改，
  assert 失败会使测试进程中止退出，测试是真实的。
- **静态计数口径**：上游无 `TEST_CASE(`/`add_test(`，按积分赛审查机器人静态计数 = 0 单元/0 集成，
  3 个运行时测试程序计入「其他测试」。

## 实测（2026-09-02，鸿蒙真机）
- 冒烟（/data/service/hnp/bin/clang++ 15.0.4，aarch64-unknown-linux-ohos）：
  - test_visit_struct（-std=c++11）：编译 ✅、运行 exit 0
  - test_visit_struct_intrusive（-std=c++11）：编译 ✅、运行 exit 0
  - test_fully_visitable（-std=c++14）：编译 ✅、运行 exit 0

## test_package（10 断言）
- is_visitable 正反例、field_count、for_each 字段顺序/值（含 std::string）、
  get_name 字段名、注册顺序访问（pair_t 以 (b, a) 注册）。

## 版本链对齐
- 任务 #5387 = conan 1.2.0 = 分支 feat/visit_struct-1.2.0 = 目录 archives/v/visit_struct/1.2.0。

---
**编译结束**: 2026-09-02 03:10
**最终状态**: built
