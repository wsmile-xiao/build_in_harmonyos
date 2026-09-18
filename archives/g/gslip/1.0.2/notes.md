# gslip 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools（automake 1.x，TAP 测试套件）
- 编译日期: 2026-09-15
- 编译器: clang 15 / clang++（OHOS aarch64，libc++）
- 状态: published
- 设备 worktree: ~/qzy/GLM-27-gslip-1.0.2（分支 feat/gslip-1.0.2）
- 平台任务号: 13464

## 编译步骤

配方 build() 实际执行（conan create 干净构建通过，W3）：

1. `apply_conandata_patches`：应用 E011 umask 补丁与 TestUtilities 显式 .str() 补丁
2. 源码拷入 build 目录（in-source 构建）
3. `./configure --prefix=/`（CONFIG_SHELL=/bin/sh，CXXFLAGS 追加 -std=gnu++11）
4. `make -j1`（构建 libgslip.a）
5. `make -j1 check`（上游 TAP 测试套件，在 build() 内真实执行）
6. `make -j1 install DESTDIR=<stage>`；package() 从 stage 取 lib/ 与 include/gslip/

## 测试账本（四维，R51/§10.1）

| 维度 | 数值 | 说明 |
|---|---|---|
| 上游源码静态声明总数 N_static | **21** | src/test/SlipTest.cc main() 的 tests[] 数组逐项清点为 20 个测试函数（testAllocation/testDatum/testEnqueue/testPush/testPop/testDequeue/testHeaderMisc/testGetSpace/testIntrinsics/testSplitLeft/testSplitRight/testMoveLeft/testMoveRight/testReplace/testDList/testReader/testSequencer/testOperators/testIO/testErrors），程序自印 TAP 计划 `1..(totalTests+1)` = 21 个测试点（含完成断言点） |
| 构建系统注册目标数 | 1 | src/test/Makefile.am 的 `TESTS = SlipTest`（TAP 驱动，VERBOSE=yes） |
| 实际执行数 N_executed | **21** | `make check` 真实执行（配方 build() 内），TAP 汇总 `# TOTAL: 21 / # PASS: 21 / # FAIL: 0 / # SKIP: 0 / # ERROR: 0` |
| 未执行/跳过数 | 0 | 无 |
| 新增消费者测试 N_consumer | 1 | test_package/consumer.cpp：slipInit 初始化 → new SlipDatum((LONG)0x15) → operator LONG() 读回 → 断言值一致（3 项断言），编译+链接 libgslip.a+运行 |

上游测试修改：src/test/TestUtilities.cc 2 处 `logFile << pretty;` → `logFile << pretty.str();`（libc++ 下 stringstream 无隐式转换；仅测试驱动，语义不变），见 0002 补丁。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: `can't create ./confXXX/subs1.awk: Permission denied` | E011：HMDFS 下 umask 077 临时目录不可写 | 补丁 configure：umask 077 → 022 |
| 2 | `configure: error: working directory cannot be determined` | E386：conan spawn 的 shell 继承 HMDFS 冷节点 cwd，首次 getcwd 必败；profile [buildenv] 强制 CONFIG_SHELL=bash 且覆盖顺序晚于工具链脚本 | 每条构建命令先 `cd /` 恢复再进入工作目录；命令内 `export CONFIG_SHELL=/bin/sh SHELL=/bin/sh` |
| 3 | `lex.Slip.cc:988: error: ISO C++17 does not allow 'register'` | profile cppstd=17 使 -std=c++17 收尾；预生成 flex 代码含 register 存储类（C++17 移除） | 环境 CXXFLAGS 末尾追加 -std=gnu++11（与上游 AM_CXXFLAGS 的 -std=gnu++11 一致，最后一个 -std 生效） |
| 4 | TestUtilities.cc 两处编译错误（ofstream << stringstream） | libc++ 无 stringstream→string 隐式转换 | 补丁为显式 `.str()` |

## 源码修改

见 patches/：
- 0001-configure.patch（E011，2 行）
- 0002-src-test-TestUtilities.cc.patch（libc++ 兼容，2 处 +2/-2，测试驱动代码）
---

**编译结束**: 2026-09-15 01:57
**最终状态**: built
