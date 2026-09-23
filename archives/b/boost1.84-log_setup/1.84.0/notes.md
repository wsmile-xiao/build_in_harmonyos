# boost1.84-log_setup 1.84.0 适配笔记

## 背景
从 boost 1.84.0 元包（`archives/b/boost/1.84.0/`）拆出 log_setup 组件包，
包名 `boost1.84-log_setup`，独立配方 + 独立测试。log_setup 与 log 同源
（`libboost_log_setup` 是 Boost.Log 的配置解析部分，位于
`libs/log/src/setup/`），故本包同时产出三个静态库。

## 关键事实
1. **产物构成**（镜像上游 `libs/log/build/Jamfile.v2`）：
   - `libboost_log.a`：核心 31 个编译单元（BOOST_LOG_COMMON_SRC）+
     posix/object_name.cpp、posix/ipc_reliable_message_queue.cpp（非
     Windows 平台分支）+ syslog_backend.cpp（可移植 UDP socket 实现，
     依赖 header-only 的 Boost.Asio）。x86 SIMD 单元（dump_ssse3/
     dump_avx2）在 aarch64 上排除。
   - `libboost_log_setup.a`：`libs/log/src/setup/` 10 个编译单元
     （BOOST_LOG_SETUP_COMMON_SRC + 默认 filter/formatter 工厂）。
   - `libboost_thread.a`：`libs/thread/src` pthread 分支 3 个编译单元
     （thread.cpp/once.cpp/future.cpp）。Boost.Log 的线程特定存储依赖
     `boost::detail::get_tss_data/set_tss_data/add_thread_exit_function`，
     这些符号只在编译型 libboost_thread 中。
2. **b2 在 OHOS 不可用**（E068，Boost.Build SHELL 执行机制失败）——沿用
   元包配方的手动编译路线（clang++ -c + llvm-ar rcs）。
3. **pthread_setcancelstate 补丁**：`boost/core/detail/sp_thread_sleep.hpp`
   在 OHOS musl 下无此 API。patch 0001 增加
   `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 特性宏守卫（R8 合规：非平台宏），
   编译期与 package_info 的 defines 同时下发。
4. **依赖 boost/1.84.0 元包**：Boost.Log 链接 boost_filesystem /
   boost_regex / boost_iostreams（元包已发布，W0 已验证 binary 在仓）。
   spirit/phoenix/asio/date_time/interprocess 等均为 header-only，由完整
   头文件树提供。
5. **settings 解析器的值语法**：非引号值仅允许 `[A-Za-z0-9_+.-]`
   （上游 `parser_utils.cpp` 的 `parse_operand`）。含 `%` 的值（如
   FileName 的轮转占位符）必须用双引号包裹——上游行为，非适配偏差。

## 编译产物
- `include/boost/*`：完整 boost 头文件树
- `lib/libboost_log.a`、`lib/libboost_log_setup.a`、`lib/libboost_thread.a`

## 测试
- 上游 `libs/log/test/`（b2/Jamfile 驱动）在 OHOS 无法直接运行；核心断言
  移植为 `test_package/test_log_setup.cpp`（14 check），涵盖 settings
  解析、init_from_settings 落盘、filter/formatter 解析、严重级过滤、
  text_file_backend 轮转、syslog UDP 后端。
- 配方内上游测试 smoke（conan create 时自动运行，报告
  `upstream-tests-report.txt`）：**11/11 通过**——
  - `libs/log/test/compile/` 4 个编译用例（上游 Jamfile compile 规则），
    编译+签名+运行 rc=0；
  - `boost/log` 全部 7 个一级公共头的 self_contained_header 逐头编译
    （上游 Jamfile BOOST_LOG_TEST_HEADER 模板）。
- 本地完整 conan create 验证（清缓存后真实构建）：43 个编译单元
  （31 log core + 2 posix + 10 setup）全部编译通过；链接元包
  filesystem/regex/iostreams + 自编 thread 后消费者测试全部通过
  （设置解析→文件 sink 实际写入→trivial 日志输出）。

## 接管修复记录（2026-09-06）
前任配方 `_run_upstream_smoke` 存在两处缺陷，本地实测修复：
1. **self_contained_header 宏重复前缀**：`-DBOOST_LOG_TEST_HEADER=log/{header}`
   拼上模板宏 `<boost/log/BOOST_LOG_TEST_HEADER>` 后变成
   `boost/log/log/{header}` 找不到文件（实测 0/11 全挂）。修复为
   `-DBOOST_LOG_TEST_HEADER={header}`。
2. **smoke 可执行文件未签名无法运行**：OHOS 二进制必须先
   llvm-objcopy --remove-section .codesign + binary-sign-tool 签名，
   且 LD_LIBRARY_PATH 需前置工具链 libc++_shared.so 目录（经
   `clang++ -print-file-name=libc++_shared.so` 推导，无硬编码），
   否则运行 rc=127。修复后 4 个 compile 用例 PASS rc=0。

## rule4 口径修复（2026-09-06，PR #8548）
审核指出：PR 正文"单元测试 N=0"与上游注册数不符（boostorg/log
boost-1.84.0 注册 54 个测试目标，Septest 实测 N=54），且 11/11 的
smoke 口径把 52 个 run 断言测试全部排除在 N 之外——口径混乱。
修复：`_run_upstream_smoke` 重写为 `_run_upstream_tests`，手动复刻
上游 test/Jamfile.v2 的 test_all 规则，N=54 全量真跑：
- **run 规则 52 项**：libs/log/test/run/*.cpp 原样编译运行，rc=0 判过。
  依赖的 boost_unit_test_framework 按上游 b2 语义从同源码树自编
  （UTF_SOURCES 19 TU 静态链接，unit_test_main.cpp 提供 main；
  宏 BOOST_TEST_STATIC_LINK）；辅助头 -I libs/log/test/common
  （Jamfile project requirements <include>common）；-pthread
  （<threading>multi）。
- **example 工程 2 项**：basic_usage/advanced_usage 真编真跑（上游
  build-project ../example 的两个 exe 目标）。
- **compile 规则 4 项 + compile-fail 规则 1 项**：按上游语义执行
  （compile 应编译运行成功；attr_functor_void_return 应编译失败，
  rc=1 实测符合预期）。
- **~hdr/ 自包含头系列**：上游对 203 个公共头各注册一个 compile
  目标，本包沿用 7 个一级公共头抽样（log 交付面）。
- **链接图**：-lboost_log_setup -lboost_log -lboost_thread（本包
  产物）+ 元包 -lboost_filesystem -lboost_regex -lboost_iostreams
  （<library> 依赖）+ 自编 -lboost_chrono（util_ipc_reliable_mq 的
  steady_clock 依赖，元包未提供 chrono，从 libs/chrono/src/chrono.cpp
  自编 1 TU）+ UTF。
- **并行编译**：concurrent.futures 线程池 8 并发（CI conanbuild PATH
  无 bash，不能用 shell 作业控制——第一轮 conan create 实测
  FileNotFoundError('bash') 后改线程池）。
- conan create 实测：66/66 通过（N=54 全过 + compile 4 + compile-fail
  1 + self_contained_header 7），消费者测试 14 checks 0 failures。
