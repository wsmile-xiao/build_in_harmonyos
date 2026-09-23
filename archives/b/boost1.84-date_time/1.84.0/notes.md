# boost1.84-date_time 1.84.0 适配笔记

## 背景
积分赛任务 6054：从 boost 1.84.0 元包（`archives/b/boost/1.84.0/`）拆出
date_time 组件包，包名 `boost1.84-date_time`，独立配方 + 独立测试。

## 形态选型：独立裁剪包（非 requires 元包）
- boost/1.84.0 元包把 date_time 声明为 header-only 组件
  （`cpp_info.components["boost_date_time"].libs` 为空，不产出
  libboost_date_time.a）——requires 元包拿不到 `libboost_date_time.a`。
- 元包与组件包若同用 cmake_file_name "Boost"，同工程共存时 CMakeDeps
  生成文件互相覆盖。本包用独立包名 `boost1.84-date_time` /
  cmake_file_name `boost1.84-date_time`，与元包可共存。

## 关键事实
1. **date_time 核心是 header-only**（Boost 1.69 起）。上游
   `libs/date_time/build/Jamfile.v2` 明确注释："date_time is now header
   only -- greg_month.cpp is a stub for backward compatibility"。本包编译
   greg_month.cpp 生成 `libboost_date_time.a`，保持传统
   `-lboost_date_time` 链接语句可用，其余功能全部由头文件提供。
2. **b2 在 OHOS 不可用**（E068，Boost.Build SHELL 执行机制失败）——沿用
   元包配方的手动编译路线（clang++ -c + llvm-ar rcs）。
3. **pthread_setcancelstate 补丁**：`boost/core/detail/sp_thread_sleep.hpp`
   在 OHOS musl 下无此 API。patch 0001 增加
   `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 特性宏守卫（R8 合规：非平台宏），
   编译期与 package_info 的 defines 同时下发。
4. **上游测试运行方式**：b2 不可用，改为在 build() 内手动编译上游测试源并
   真实运行（PR #8455 复审后扩充为 Jamfile.v2 注册的全部 59 个目标 + 5 个
   未注册可运行源 = 64 个目标；serialization 变体测试期编译
   libs/serialization/src 供链接，不打包）。LD_LIBRARY_PATH 通过
   `clang++ -print-file-name=libc++_shared.so` 编译器内省定位（无硬编码
   SDK 版本路径）。testtime_serialize_versioning_prev 必须先于 curr 运行
   （curr 读取 prev 在 cwd 生成的数据文件）。

## 编译产物
- `include/boost/*`：完整 boost 头文件树（date_time 及其传递依赖均在此树）
- `lib/libboost_date_time.a`：greg_month.o 单编译单元静态库

## 测试
- build() 上游测试（PR #8455 复审后扩充，处置上游 boost-1.84.0 libs/date_time/test/ 全部 66 个 .cpp）：
  - 纳入运行 64 个测试目标：
    - Jamfile.v2 注册的 55 个 run 目标全部复现（含 8 个 serialization 变体——测试期编译 libs/serialization/src 48 个 .cpp 为 libboost_serialization_test.a 供链接，不打包；含 testmisc_std_cfg / testtime_input_facet / testtime_formatters 等 STD_CONFIG 变体的 -D 宏；含 testtz_database / testlocal_time_facet 的 csv 数据文件参数）
    - 4 个 compile-fail 目标（按上游语义：编译必须失败才算 PASS）
    - 5 个未被 Jamfile 注册但可正常编译运行的上游测试源（extra_*：testint64_range / testcurrent_day / testlocal_time_input_facet / posix_time/testformatters / testtime_wstream）
  - 排除 7 个源（理由逐条见 conanfile.py EXCLUDED_UPSTREAM_TESTS 与 PR 描述）：
    1. self_contained_header.cpp — b2 头文件自检样板（逐头循环编译），非独立测试
    2. testfrom_facet.cpp — 上游注释明确不属于官方回归套件，且依赖 boost/algorithm_ext（超组件范围）
    3. gregorian/testfacet.cpp — 引用未定义符号 generate_locale/create_facet_def（Jamfile 未注册的上游遗留）
    4. gregorian/testformat_date_parser.cpp — musl 无完整 std::locale facets（编译错误，OHOS 平台限制）
    5. gregorian/testgreg_wstream.cpp — 宽字符流 wofstream，musl 宽 locale 模板实例化失败（OHOS 平台限制）
    6. posix_time/teststreams.cpp — 引用上游已删除的 greg_facet_creator（上游 1.84.0 自身编译错误）
    7. posix_time/testperiod.cpp — 上游 FILE OBSOLETE（硬编码 return 1，被 testtime_period.cpp 取代）
  - 测试通过判定：run 目标 rc=0；compile-fail 目标编译失败；报告写 upstream-tests-report.txt，任一失败即 build() 失败
- test_package/test_boost1_84_date_time.cpp（46 checks，移植自上游断言）：gregorian 日历、date 构造/运算、ptime/time_duration
- conan create（ohos-aarch64）实测：64/64 目标全部通过（2026-09-06）
