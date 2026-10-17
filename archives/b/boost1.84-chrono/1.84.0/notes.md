# boost1.84-chrono 1.84.0 编译笔记

## 编译开始时间
2026-09-05 14:00

## 编译系统
手动编译（Boost.Build 不可用，同底稿 archives/b/boost/1.84.0 方案）

## 源码
- URL：https://downloads.sourceforge.net/project/boost/boost/1.84.0/boost_1_84_0.tar.gz
- SHA256：a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724
- 与元包 boost/1.84.0 完全同源（组件独立裁剪打法）

## 适配方案（继承底稿已验证结论）

底稿 archives/b/boost/1.84.0 已证明：
1. b2 构建系统在 OHOS 上 SHELL 执行机制失败（E068），不可用
2. CMake superproject 模式无法独立构建
3. 手动编译 select 库源文件 → libboost_*.a 是可行方案

本组件包按同样打法只编译 chrono：
- libs/chrono/src/chrono.cpp
- libs/chrono/src/process_cpu_clocks.cpp
- libs/chrono/src/thread_clock.cpp

编译标志：
```
-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC -I<boost_root>
-DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED
-DBOOST_CHRONO_VERSION=2
-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE   # 配合 0001 补丁（OHOS musl 无 pthread_setcancelstate）
```

## 上游测试（2026-09-05 实测）

b2 不可用 → 手动编译 libs/chrono/test/ 各测试源文件，链接 libboost_chrono.a 直接运行：

| 组 | 测试 | 断言数 | 结果 |
|---|---|---|---|
| clock | clock_pass.cpp | 11 | PASS |
| duration | arithmetic_pass | 41 | PASS |
| duration | duration_cast_pass | 2 | PASS |
| duration | comparisons_pass | 43 | PASS |
| duration | constructor_pass | 7 | PASS |
| duration | rounding_pass | 45 | PASS |
| duration | duration_values_pass | 4 | PASS |
| duration | typedefs_pass | 0 | PASS（compile-only 型） |
| duration | types_pass | 0 | PASS（compile-only 型） |
| duration | default_ratio_pass | 0 | PASS（compile-only 型） |
| duration | ratio_alias_pass | 0 | PASS（compile-only 型） |
| time_point | arithmetic_pass | 15 | PASS |
| time_point | arithmetic_ext_pass | 7 | PASS |
| time_point | time_point_cast_pass | 2 | PASS |
| time_point | comparisons_pass | 25 | PASS |
| time_point | constructor_pass | 5 | PASS |
| time_point | min_max_pass | 1 | PASS |
| io | duration_input | 7 | PASS |
| io | duration_output | 14 | PASS |
| io | time_point_input | 18 | PASS |
| io | time_point_output | 25 | PASS |

TOTAL 21: 21 passed / 0 failed

说明：4 个 compile-only 型测试在上游 Jamfile 中定义为 chrono-compile（编译验证，
源文件无 main 函数），按上游语义以编译通过计。

## 遇到的问题

无新增问题。chrono 源码在 OHOS musl + libc++ 下无平台障碍（补丁 0001 是
smart_ptr 的通用 OHOS 修复，chrono 编译链路上的头文件会引用）。

## 运行时注意

本机运行测试二进制需要 LD_LIBRARY_PATH 指向 OHOS SDK 的 libc++_shared.so：
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++
（conan test_package 环境由 conanrun.sh 自动处理）
---

**编译结束**: 2026-09-05 19:32
**最终状态**: built

<!-- validated: 2026-09-05 conan create PASS, W3 local CI PASS, upstream tests 21/21 -->
