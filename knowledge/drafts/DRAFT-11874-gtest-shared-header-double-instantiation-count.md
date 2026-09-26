# DRAFT-11874-gtest-shared-header-double-instantiation-count — gtest 共享测试头双实例化的 N 申报口径

> 草稿知识项 — gtest 项目把 TEST 宏放共享头、被多个 .cc include 时，
> "源码宏实例数"与"gtest 运行条目数"出现系统性差值；N 申报需同时给出两个
> 口径与差值机理，否则触发 rule4 少报/多报误判。
> 来源：kea-hook-radius 3.0.3 适配（PR !11874，task 12795，2026-09-23）
> 同 stem 配对：`knowledge/drafts/DRAFT-11874-gtest-shared-header-double-instantiation-count.kv`

## 问题（现象 / error_signature）

审核端复核 PR 申报的"上游测试用例数 N"时发现数字对不上：

```
[==========] Running 424 tests from 19 test suites.
[  PASSED  ] 424 tests.
```

而源码宏统计是 428：

```
$ grep -h -c -E '^\s*(TEST|TEST_F|TEST_P)\(' tests/*.cc | awk '{s+=$1} END {print s}'
395
$ grep -c -E '^\s*(TEST|TEST_F|TEST_P)\(' tests/request_unittests.h
15        # 被 async_request_unittests.cc 和 sync_request_unittests.cc 各 include 一次 → 30
$ grep -h -c -E '^\s*(TEST|TEST_F|TEST_P)\(' libloadtests/*.cc | awk '{s+=$1} END {print s}'
3
# 合计 395 + 30 + 3 = 428 ≠ 运行条目 424 + 3 = 427
```

## 根因（root_cause）

1. gtest 生态常把一批用例宏放**共享头**（Kea：`tests/request_unittests.h`，
   15 个 TEST 宏），由同步/异步两个 .cc 各 `#include` 一次——预处理器
   展开两套**同名** `Suite.Test` 实例（15×2=30 份源码宏）。
2. gtest `TestRegistry` 对同名 Suite.Test 保留全部注册（执行两次），但
   `--gtest_list_tests` 与运行汇总行按"套件.用例"名合并显示——**运行条目数
   < 源码宏实例数**（本例差 1：共享头 15 宏双实例化后，同名套件在两处
   各贡献合并计 1 条）。
3. 审核端若用运行条目复核宏数 → 误判"多报"；用宏数复核运行数 → 误判
   "少报"（rule4）。两口径都真实，差值机理必须显式说明。

## 解决方案（solution）

**申报口径 = 源码宏实例数**（每宏每被 include 一次算一份），同时给出
运行条目数与差值机理：

```bash
# ① 源码宏实例计数
grep -c -E '^\s*(TEST|TEST_F|TEST_P)\(' tests/*.cc             # 直接宏
grep -c -E '^\s*(TEST|TEST_F|TEST_P)\(' tests/<shared>.h       # 共享头宏数 H
grep -n '#include "<shared>.h"' tests/*.cc                     # include 处数 K → H×K
# ② gtest 运行条目（对照）
./<testbin> --gtest_list_tests | grep -cE '^\s+\w'
```

PR 正文写法（!11874 实例）：
- 统计表"上游用例数"列：428（注明"源码宏口径：395 直接 + 30 共享头双实例化 + 3 libload"）
- "上游测试用例减少原因"段：运行条目 427 = 424 + 3，与源码口径 428 的差 1
  为 gtest 对共享头双实例化重名套件的运行期计数合并，非用例缺失
- 实测：`[  PASSED  ] 424 tests.` + `[  PASSED  ] 3 tests.`（全绿）

## 降级方案（fallback）

若审核端只认 gtest 运行条目数，则按运行口径申报，"减少原因"段写明源码宏
数更大、差值全部来自共享头双实例化的重名合并，附 `--gtest_list_tests`
原始输出与 grep 计数命令。**两个口径都合法，禁止只报其一。**

## 验证（verify_builds）

- CI 构建 #56775 / #56776（PR !11874，L1 门禁测试执行验证通过）
- 本地 conan create 全流程：`dhcp-radius-tests` 424 通过 0 失败 0 跳过 +
  `dhcp-radius-libloadtests` 3 通过（meson test Ok 2 / Fail 0）
- 同源先例：kea-hook-lease-query 3.0.3（!11379，同共享头结构）
- 适用面：任何含共享 gtest 头的 meson/cmake/ctest 项目（GTest 通用行为，
  非平台相关）

## 红线与限制

- 本条是**申报口径规范**，不是代码修复：不要为对齐数字去改上游测试
- `DISABLED_` 前缀用例与 `#ifdef HAVE_*` 条件块用例按"上游默认形态注册
  口径"另行说明，不与本差值混淆
