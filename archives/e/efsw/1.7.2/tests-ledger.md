# efsw 1.7.2 — 测试枚举台账（HarmonyOS PC / aarch64）

任务: efsw-1.7.2-r01-pc1-11-20260901T182829Z
worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc1-11-efsw-1.7.2
源码: /storage/Users/currentUser/tmp/builds/efsw-1.7.2.work
分支: feat/efsw-1.7.2  HEAD: b7549b1e62ba6c8bf38b861439478e6f0069b578

## 统计口径
- 全量口径: 用户测试源（src/unit_tests/*.cpp）中独立 TEST_CASE 总数 = 49
- 全量通过率: 49/49 = 100%（49 全部实际运行并 PASSED）
- 实际执行口径: 49/49 = 100%（无未运行项）

## 逐项枚举台账

| 入口 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果 / 不能运行原因 |
|---|---|---|---|---|---|
| src/unit_tests/main.cpp | 测试入口 | 否（入口而非用例） | utest 调用入口，注册 UTEST_STATE | 是 | 与各测试源一起编译链接，驱动 49 用例 |
| src/unit_tests/add.cpp | 用户测试源 | 是（Add.* 用例） | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/cross_dir_and_watcher.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/delete.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/emoji.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/inotify_overlapping_watches.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/modified.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/moved.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/rename_and_local_move.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/symlink.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/unwatched_to_watched.cpp | 用户测试源 | 是 | 上游独立 TEST_CASE | 是 | PASSED |
| src/unit_tests/utest.h | 框架头 | 否 | 第三方 sheredom/utest.h 单测框架宏，非用户用例 | 是 | 框架头，编译即用 |
| src/unit_tests/test_util.hpp | fixture/工具 | 否 | 公共测试工具/WatcherGuard 辅助，非独立用例 | 是 | 辅助代码 |
| src/test/efsw-test.cpp | 样例/demo | 否 | 交互式 demo 应用（C++ API 演示，等待 ^C 退出），非自动化用例 | 是 | 运行正常，交互等待，超时退出（EXIT=124），不计入通过率 |
| src/test/efsw-test.c | 样例/demo | 否 | 交互式 demo 应用（C API 演示），非自动化用例 | 是 | 运行正常，交互等待，超时退出（EXIT=124），不计入通过率 |
| scripts/build.reldbginfo.sh | 构建脚本 | 否 | 调试信息构建脚本，非测试 | 否 | 非测试入口，不运行 |
| premake4.lua / premake5.lua | 构建脚本 | 否 | 备选 premake 构建配置，非测试 | 否 | 非测试入口，不运行 |
| CMakeLists.txt (BUILD_TEST_APP) | 构建目标 | 否 | efsw-test / efsw-test-stdc 构建目标定义 | 是 | 目标编译链接成功 |

## 独立用例计数汇总
- 发现独立上游用例总数: 49（位于用户测试源 src/unit_tests/）
- 实际运行: 49
- 通过: 49（100%）
- 失败: 0
- 未运行 / 不可运行: 0
- 硬阻塞: 0

## 运行命令与结果
- 编译: `clang++ -std=c++17 -I../../include -I. -I../ -I../efsw main.cpp add.cpp ... unwatched_to_watched.cpp ../../build/libefsw-static.a -lpthread -o efsw-unit-tests` → exit 0
- 运行: `./efsw-unit-tests` → `[==========] 49 test cases ran. [  PASSED  ] 49 tests.` exit 0
- 结果摘要: 49/49 PASSED（inotify + generic 双后端全部通过）