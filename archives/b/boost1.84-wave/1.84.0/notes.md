# boost1.84-wave 1.84.0 适配笔记

## 任务信息
- 组件拆分包：boost1.84-wave（Boost.Wave 组件，来自 boost 1.84.0 官方 tarball）
- 认领人：2404_87638649
- 分支：feat/boost1.84-wave-1.84.0
- 底稿：仓库 main 的 archives/b/boost/1.84.0/（元包，手动编译 filesystem/regex/
  program_options/iostreams 4 个库）

## 编译系统
Boost Build (b2) — 在 OHOS 上不可用（E068：Boost.Build SHELL 执行机制失败，
见元包 notes.md 与知识库）。本组件包沿用元包做法：**手动 clang++ 编译源文件 +
llvm-ar 打静态库**，绕过 b2。

## 包内容（为什么带 filesystem/thread/program_options）
wave 的上游构建定义（libs/wave/build/Jamfile.v2）声明 boost_wave 依赖
boost_filesystem + boost_thread；wave 的上游测试程序 testwave 还需要
boost_program_options。boost/1.84.0 元包（制品仓 recipe 存在但无 binary 包）
只含 filesystem/regex/program_options/iostreams，**没有 thread**，且无已发布
binary 可引用——因此本组件包从同一 upstream tarball 一并编译：
- libboost_wave.a（12 源文件：8 个 grammar 实例化 + token_ids +
  wave_config_constant + re2clex 的 aq.cpp/cpp_re.cpp）
- libboost_filesystem.a（9 源文件，跳过 windows_file_codecvt.cpp）
- libboost_thread.a（pthread 变体 3 源文件：pthread/thread.cpp、pthread/once.cpp、
  future.cpp；跳过 win32 目录与 tss_null.cpp）
- libboost_program_options.a（10 源文件，跳过 winmain.cpp；testwave 测试所需）
- boost_system：1.69 起 header-only，无二进制，仅保留 CMake component
- 完整 boost/ 头文件目录

注意：wave 源码本身不 include <boost/thread/*>（grep 验证为空）；但链接
testwave/quick 等测试时需要 boost::thread_detail::enter/commit/rollback_once_region
和 boost::detail::get/set_tss_data 符号（经 smart_ptr/spinlock_pool 与
pool_alloc 的 default_mutex 依赖链引入），故 thread 二进制必需——与上游
Jamfile 的显式依赖一致。

## 源码
- URL: https://downloads.sourceforge.net/project/boost/boost/1.84.0/boost_1_84_0.tar.gz
  （备用 https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz，
  与元包 conandata.yml 相同）
- sha256: a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724
  （与本地缓存 /storage/Users/currentUser/tmp/boost184-dl/boost_1_84_0.tar.gz
  实测 sha256sum 一致）

## 补丁
- patches/0001-ohos-pthread-cancel-fix.patch：与元包相同。sp_thread_sleep.hpp
  用 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫
  pthread_setcancelstate（OHOS musl 无此符号），R8 合规（非 __OHOS__ 平台宏）。
  配方编译时传 -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE，并以
  package_info defines 传播给下游。

## 平台适配要点（OHOS）
1. **-fwrapv（本包新发现）**：wave 的整数溢出检测
   （boost/wave/grammars/cpp_expression_value.hpp 的 operator+= 等）依赖
   有符号加法回绕语义判断进位；clang -O2 把有符号溢出当 UB 优化掉检测分支，
   导致上游 t_6_015~t_6_018 四个"期望报 integer overflow"的测试失败
   （漏报，且测试继续跑不崩）。**加 -fwrapv 后 226/226 全过**。
   上游 b2 测试跑 debug variant 无此问题；这是个值得沉淀的编译器语义差异。
2. pthread_setcancelstate 缺失（补丁 0001，同元包）。
3. /tmp 只读（E002）：工具临时文件全部走 $TMPDIR；conan create 由 conan 管理。
4. 本机为 OHOS aarch64，直接运行产物需 SDK libc++_shared.so：
   export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

## 上游测试（规则 5）
绕过 b2，手动编译运行上游测试（全部真编译真运行，非空壳）：
- testwave.cpp + testwave_app.cpp：上游完整 wave 测试套件，按 Jamfile.v2 的
  参数跑 testfiles/test.cfg（226 个测试文件，期望输出/报错注记在 .cpp 内）。
  实测 **226/226 通过**（`testwave: 226 of 226 test(s) succeeded.`）。
- testwave/quick.cpp：预处理 #if 0/#else/#endif 小输入，通过（输出 3.14）。
- testwave/default_hooks.cpp：默认 hooks 覆盖（#LINE 指令检查），通过。
- testlexers/test_re2c_lexer.cpp：re2c lexer + cpp_tokens.hpp 测试数据，
  通过（No errors detected.）。
报告由 conanfile.py 的 _run_upstream_tests() 写入
build_folder/upstream-tests-report.txt 并以 output.info 输出末尾摘要。

## 验证结果
- conan create（W3）: PASS（见 .ci-result.json / reports/）
- 上游 testwave 套件：226/226（-fwrapv 之后；之前 222/226，4 个溢出检测漏报）
- test_package L1 smoke：通过

## 历史/关联
- 元包 boost/1.84.0（本仓 main）：只编译 filesystem/regex/program_options/
  iostreams，无 wave/thread——本组件包补 wave 场景。
- 并行任务：boost1.84-atomic、boost1.84-url 等同系列组件拆分包。
---

**编译结束**: 2026-09-05 17:26
**最终状态**: built
