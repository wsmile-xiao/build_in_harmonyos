# easylogger 2.2.0 适配笔记

## 编译环境
- 构建系统: custom (CMake 生成，嵌入式 C 库，上游无库构建目标)
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS aarch64 profile)
- 状态: built
- 官方源: https://github.com/armink/EasyLogger (tag 2.2.0，无 v 前缀)
- SHA-256: bfe9044ea8209958a8292bec37c5aacf1b0eaa5e78acfe7445d33d3fb0f4af44

## 编译步骤

EasyLogger 是嵌入式 C 日志库：官方 tag 源码无 configure、无库级构建目标
（`easylogger/src/*.c` 为核心源码，`easylogger/inc/*.h` 为公开头，
`easylogger/port/elog_port.c` 为逐平台空壳模板）。配方按 linenoise 先例
生成小型 CMakeLists.txt，编译核心 4 源文件（elog.c/elog_async.c/
elog_buf.c/elog_utils.c）为静态库 libeasylogger.a，安装 inc 与 plugins 头：

```
conan create archives/e/easylogger/2.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

- 编译验证: demo/os/linux `make CC=clang` 编译链接成功，`EasyLoggerLinuxDemo`
  运行正常输出各级别日志（无限循环示例，timeout 杀进程为预期）
- 运行链路验证: 直通 port（printf）下 log_a/log_e/log_w/log_i/log_d/log_v/
  elog_raw 全部正常输出
- conan-verify: G0-G4/L2/L4/L5 全通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套检测把 demo/os/linux 提升为源码根 | F068 误判：仓库根无构建标记，demo 子目录含 Makefile 被提升 | 手动重建 .orig/.work：仓库根为源码根（LICENSE/README/demo/docs/easylogger），核对 .tarball-sha256 |
| 2 | 默认 easylogger/port/elog_port.c 是空壳，日志无输出 | 上游 port 模板需逐平台移植 | test_package 提供测试 port（printf+捕获缓冲），demo port 验证运行链路 |
| 3 | 默认 elog_cfg.h 开启 ELOG_ASYNC_OUTPUT_ENABLE，test_package 首次 G2 失败（captured=0） | 异步线程消费需要时间，test 立即校验捕获缓冲 | test 增加 usleep(1s) 等待异步线程消费（E298 建议 virtual-run-env 不适用于静态库场景） |
| 4 | Makefile 硬编码 `cc`（环境无 cc 只有 clang） | 上游 demo Makefile 兼容性问题 | `make CC=clang` 命令行覆盖；不支持环境变量传递（Makefile 内 `CC = cc` 覆盖环境） |
| 5 | demo Makefile `out/*.o` 通配符链接失败、out 被误建为文件 | 无 out/ 目录时 mv 对象改名为 out 文件；make 目标链接时通配符不展开 | rm -f out && mkdir out 后重建；链接按对象逐个传入 |

## 源码修改

无补丁（patches/ 为空）。配方通过生成 CMakeLists.txt 提供构建目标，
不修改上游源码；OS 适配仅影响 port（由消费者/测试提供，非库内编译）。

## 依赖版本

- 无第三方依赖（纯 C 标准库 + pthread；Threads::Threads 由配方链接）
- 依赖发布检查 W0: 无需发布前置依赖

## 上游测试申报表（R51 全量枚举，2026-09-19）

### 枚举方法
解压官方 tag 源码 `easylogger-2.2.0.tar.gz`（552 条目），全仓扫描：
- 目录: 无 `test*`/`unittest`/`fuzz`/`benchmark`/`bench`/`examples` 测试目录
- 文件: 无 `*test*`/`*check*` 测试源文件；无测试脚本（sh/py/pl 均无）
- 注册: 无 CTest（add_test）/GTest/pytest/make check 目标（全仓唯一 Makefile
  为 demo/os/linux 示例，无 check 目标，仅 all/clean）
- 框架/断言: `ELOG_ASSERT`/`elog_assert` 是库内部运行时断言宏（elog.h），
  非独立可执行用户用例

### 台账（覆盖测试源/框架头/样例/基准/fixture/脚本/构建目标）

| 条目 | 类型 | 是否独立上游用例 | 实际运行 | 结果/原因 |
|------|------|------|------|-----------|
| demo/os/linux (main.c+Makefile) | 样例 | 否（示例程序，非测试套件） | 是 | 编译链接成功；运行输出全部日志级别正确（无限循环，timeout 杀为预期） |
| demo/non_os/stm32f10x (EWARM 工程) | 样例 | 否（STM32 固件工程，EWARM 专有，无 OHOS 可用入口） | 否 | 平台不可运行：IAR EWARM 工程 + CMSIS/STM32 外设库，无 linux/OHOS 构建入口 |
| demo/os/rt-thread/stm32f10x | 样例 | 否（RT-Thread BSP 示例） | 否 | 依赖 RT-Thread 内核，非独立可执行用例 |
| demo/os/windows | 样例 | 否（MSVC 工程） | 否 | Windows 平台工程，OHOS 不可运行 |
| easylogger/src/*.c (4 核心源) | 库源码 | 否 | 编译通过 | 已编译进 libeasylogger.a |
| easylogger/inc/elog.h | 框架头 | 否 | - | ELOG_ASSERT 为库内部断言宏 |
| easylogger/port/elog_port.c | port 模板 | 否（空壳占位） | 否 | 上游留待平台移植 |
| easylogger/plugins/file、flash | 插件源码 | 否（需用户配置 ELOG_FILE_* 宏） | 否 | 缺 ELOG_FILE_NAME 等强制配置，非独立用例 |
| docs/ | 文档 | 否 | - | 无测试提及 |
| ctest -N / GTest 注册项 | 测试注册 | 无 | - | 无 CTest/GTest 注册 |

### 双口径统计

- source_declared_total（官方 tag 源码声明的独立测试用例总数）: **0**
- configured_executable_total（当前 OHOS 配置实例化的独立可执行用例数）: **0**
- executed_passed_total: **0**（无上游用例可执行）
- 失败数: 0；未运行/未实例化数: 0（非实例化，是上游无声明）
- 全量通过率: **0/0（上游无独立测试声明）**

说明: EasyLogger 2.2.0 官方 tag 未包含任何独立可执行测试套件
（无 tests/、无 ctest/GTest 注册、无 make check、无脚本）。demo 仅是可运行
示例，非断言化测试，不计入上游用例分母（按任务规则：user 测试源中的独立
TEST_CASE 才算，框架宏/样例/基准不得误算）。上游无测试属上游事实，本库实际
运行验证由 test_package 消费者测试 + 鸿蒙专项测试承担（见下节与 test-report）。

## 验证结果

```bash
# conan-verify 全门禁通过
conan create archives/e/easylogger/2.2.0 ... -> G0-G4/L2/L4/L5 PASS
# 消费者测试（test_package，7 级日志标记 + 版本横幅 8 断言全过）
ctest --test-dir test_package/build -> 1/1 passed
```
---

**编译结束**: 2026-09-19 03:59
**最终状态**: built（conan-verify 全门禁通过，制品上传待 PR 合并后 CI release 流水线执行）
