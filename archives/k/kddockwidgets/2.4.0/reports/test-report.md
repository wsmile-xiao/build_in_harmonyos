# Upstream Test Report — kddockwidgets 2.4.0（R51 第 3 步）

- **命令**：`ctest --timeout 900`（CTEST_OUTPUT_ON_FAILURE=1）
- **执行环境**：真实 OHOS PC 设备（通道 3，clang 15/libc++，ctest 4.1.2），
  `QT_QPA_PLATFORM=offscreen`（qt5-qtbase/5.15.2.2 自带 offscreen QPA 插件，OHOS 无 xcb）、
  `QT_PLUGIN_PATH=<qt5>/plugins`、LD_LIBRARY_PATH 前置构建树 `lib/`
  （OHOS musl 加载器忽略 ELF RUNPATH，只认 LD_LIBRARY_PATH——首轮全挂踩坑后修复，
  详见 notes.md R51 三步法条目）。
- **结果**：**24/24 通过（100%），CTEST-EXIT=0**，总耗时 743.50 s。
- **盘点清单**：reports/upstream-test-inventory.txt（真机 `ctest -N`，24 例）；
  **二进制哈希**：reports/upstream-test-binary.txt。

| # | 用例 | 结果 | 耗时 (s) |
|---|------|------|----------|
| 1 | tst_qtwidgets | Passed | 114.45 |
| 2 | tst_docks | Passed | 179.37 |
| 3 | tst_docks_slow1 | Passed | 166.53 |
| 4 | tst_docks_slow2 | Passed | 73.32 |
| 5 | tst_docks_slow3 | Passed | 45.93 |
| 6 | tst_docks_slow4 | Passed | 9.22 |
| 7 | tst_docks_slow5 | Passed | 28.16 |
| 8 | tst_docks_slow6 | Passed | 62.66 |
| 9 | tst_docks_slow7 | Passed | 48.89 |
| 10 | tst_multisplitter | Passed | 1.32 |
| 11 | tst_viewguard | Passed | 0.66 |
| 12 | tst_view | Passed | 1.53 |
| 13 | tst_window | Passed | 0.86 |
| 14 | tst_droparea | Passed | 0.70 |
| 15 | tst_platform | Passed | 0.64 |
| 16 | tst_group | Passed | 0.61 |
| 17 | tst_titlebar | Passed | 0.66 |
| 18 | tst_stack | Passed | 0.65 |
| 19 | tst_tabbar | Passed | 0.63 |
| 20 | tst_separator | Passed | 0.61 |
| 21 | tst_floatingwindow | Passed | 0.83 |
| 22 | tst_dockwidget | Passed | 1.31 |
| 23 | tst_docks_slow8 | Passed | 3.81 |
| 24 | tst_native_qpa | Passed | 0.12 |

## 说明

- `tst_docks_slow1`…`tst_docks_slow8` 为上游慢速套件（真实交互时序），在 offscreen
  QPA 下按上游设计全量执行并通过；核心快速套件（#10-#22）均在 2 秒内通过。
- `tst_native_qpa` 上游设计即「仅原生 QPA 全量执行」：每个用例自带 offscreen 平台
  提前返回守卫（上游 tests/tst_native_qpa.cpp），offscreen 下各用例直接跳过并退出 0
  ——与上游在 Linux CI 的 offscreen 环境行为一致。
- 首轮全量执行 24 例在 0.05-0.09 s 内速败（`Error loading shared library
  libkddockwidgets.so`）：OHOS musl 加载器忽略 ELF RUNPATH，conanrun.sh 只带依赖包
  库目录、不含本包构建树 `lib/`。修复（ctest 脚本显式前置 `$BUILD/lib`）后本报告
  为第二轮全量执行结果；修复前单测预检 tst_native_qpa EXIT=0 已实证库加载与 QPA
  插件可用。
- 消费者测试 12/12 断言 PASS（G2 test_package 实跑，见 reports/conan-create.log 尾部
  `test_kddockwidgets: all 12 assertions passed`）。
