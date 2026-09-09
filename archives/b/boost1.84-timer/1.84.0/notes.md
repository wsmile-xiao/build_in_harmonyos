# boost1.84-timer 1.84.0 编译笔记

## 任务背景

- 平台分支：`feat/boost1.84-timer-1.84.0`，积分赛活动
- 认领人：2404_87638649
- 底稿：仓库 main 的 `archives/b/boost/1.84.0/` 元包（filesystem/regex/program_options/iostreams 四库手动编译）
- worktree：`~/huawei/wt-boost-timer`（独立 worktree，多会话隔离规范）

## 形态选型（组件包形态评估）

**结论：独立裁剪包（自编译 libboost_timer.a + 完整头文件树），不 requires 元包。**

评估过程（2026-09-05，boost1.84-atomic 并行任务尚无 notes/PR 产出，无法参考，独立评估）：

### 方案 A：requires 元包（boost/1.84.0）

**否决**，两个硬伤：
1. **元包不含 timer**：`archives/b/boost/1.84.0/conanfile.py` 只手动编译了
   filesystem/regex/program_options/iostreams 四个库的 .a，`libs/timer/src/` 未参与
   编译——requires 元包根本拿不到 libboost_timer.a，必须自己编译源码。
2. **cmake_file_name 冲突**：元包声明 `cmake_file_name = "Boost"`。若组件包也
   声明 "Boost"，同一工程同时依赖元包+组件包时，CMakeDeps 生成的
   `BoostConfig.cmake` 互相覆盖，只有后装者生效（conan-center 对 boost 生态的
   官方拆分同样要求各组件独立包名）。组件包改名 `boost1.84-timer` 即可共存。

### 方案 B：独立裁剪包（选定）

- timer 编译部分极小：`libs/timer/build/Jamfile.v2` 仅定义 2 个源文件
  （auto_timers_construction.cpp、cpu_timer.cpp）
- 依赖全部 header-only：boost/config、boost/io、boost/predef（CMakeLists.txt
  的 boostdep 依赖图确认）
- **不需要 chrono 编译库**：boost/timer/timer.hpp 的 cpu_timer 走 POSIX
  `times()`/`sysconf(_SC_CLK_TCK)` 取时钟（musl 支持），不经 boost/chrono
  的 process_cpu_clocks 路径
- 复用元包的 0001-ohos-pthread-cancel-fix.patch（R8 合规：特征检测宏守卫，
  timer 源码不经 sp_thread_sleep 路径，但完整头文件树的下游消费者可能需要）

## 编译过程

- 源码：boost_1_84_0.tar.gz（SHA256 与元包 conandata.yml 一致：
  a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724）
- 方式：沿用元包的手动编译路线（b2 在 OHOS SHELL 执行机制不兼容，E068；
  Boost CMake 是 superproject 模式不支持独立构建——元包 notes.md 已验证）
- 编译命令：clang++ -std=c++17 -stdlib=libc++ -fPIC -I<root>
  -DBOOST_ALL_NO_LIB -DBOOST_TIMER_NO_LIB -c libs/timer/src/*.cpp，
  llvm-ar rcs 归档为 libboost_timer.a
- 打包：完整 boost/ 头文件树 + libboost_timer.a

## 遇到的问题

无新增问题。timer 源码不使用 OHOS 缺失 API（times/sysconf/memcpy 均在 musl），
无需额外补丁。

## 上游测试

b2 不可用，沿用元包"手动编译上游测试源文件并真实运行"的做法。
清单对齐上游 libs/timer/test/Jamfile.v2 注册的全部 7 个测试目标
（2026-09-06 从 boostorg/timer boost-1.84.0 实测；rule4 修订：初版只跑了
cpu_timer_test/original_timer_test 2 项属少报，本次补全为 7 项全量）：

| # | 测试目标 | Jamfile 类型 | 结果 |
|---|---------|-------------|------|
| 1 | example/auto_cpu_timer_example.cpp | run | PASS rc=0 |
| 2 | cpu_timer_info.cpp | run | PASS rc=0 |
| 3 | cpu_timer_test.cpp | run | PASS rc=0（"No errors detected."） |
| 4 | example/timex.cpp（传参 echo "Hello, world"） | run | PASS rc=0 |
| 5 | original_timer_test.cpp | compile | PASS（编译通过） |
| 6 | chrono_conflict_test.cpp | run | PASS rc=0 |
| 7 | progress_display_test.cpp | run | PASS rc=0（"No errors detected."） |

通过率 7/7（100%）。inspect（explicit 工具目标）、cmake_install_test/
cmake_subdir_test（CMake 安装验证目录）、msvc10/（MSVC 专用）不计入。

### chrono_conflict_test 的 chrono 静态库处理

上游 Jamfile 要求该测试链接 /boost/chrono//boost_chrono 且 <link>static。
libboost_chrono.a 不在本包交付范围（timer 实现不依赖 chrono），但 boost 源码树
自带 libs/chrono/src：按 <link>static 语义，用与本包 timer 库完全相同的
cxxflags 将 chrono 的 3 个上游源文件（chrono.cpp、process_cpu_clocks.cpp、
thread_clock.cpp，与 boost1.84-chrono 组件包文件集一致）编译成构建期辅助
静态库 libboost_chrono.a 供测试链接，不随包交付（package() 只打包
libboost_timer.a）。实测 chrono v1（上游 b2 默认）/v2 两种宏配置下
chrono_conflict_test 均链接运行通过。

## W0 依赖检查

- boost/1.84.0 元包：已发布（conan download --only-recipe 确认，本包最终未 requires）
- zlib/1.3.1：已发布（timer 不需要 zlib，仅底稿参考）
- 本包 requirements：**无**（timer 依赖全部 header-only，随源码包自带）

## 结论

独立裁剪包形态，手动编译 libboost_timer.a，上游测试 7/7 通过（2026-09-06
rule4 修订补全），test_package smoke test 8 断言通过。适配完成于
2026-09-05，测试补全于 2026-09-06。
