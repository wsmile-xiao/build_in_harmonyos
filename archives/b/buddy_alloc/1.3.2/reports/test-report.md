# buddy_alloc 1.3.2 verification report (R01)

## Environment

- OpenHarmony PC aarch64 device (armv8)
- Clang 15.0.4 (`/data/service/hnp/bin/clang`), CMake 4.1.2, Make 4.4.1
- Conan 2.29.1, profile `ci/conan/profiles/ohos-aarch64` (os=OHOS 6.0, clang 15, libc++)
- Source: official tag `v1.3.2` — https://github.com/spaskalev/buddy_alloc/archive/refs/tags/v1.3.2.tar.gz
- SHA-256: `5c1b045cf500deb8f43454b5cc699ba55718fa90efde74a0dddbc6f168b7c025`（init-build EXPECTED_SHA256 校验 + 独立 sha256sum 双重核验）

## Upstream test full enumeration ledger (R51)

| 入口 | 分类 | 是否独立上游用例 | 是否实例化 | 实际运行 | 结果 |
|---|---|---|---|---|---|
| `tests.c` — 165 个 `test_*` 函数（自定义 assert 框架，main() 逐一声明调用全部 165 个） | 用户测试源 | ✅ 是（165 个独立用例） | ✅ CMake `buddy_tests` 目标 / 直接 clang 编译 | ✅ `./buddy_tests` | rc=0 全过（160 例经 START_TEST 打印，5 例无打印宏但执行通过：highest_bit_position / ceiling_power_of_two / popcount_byte / demo / demo_embedded） |
| `testcxx.cpp` — C++11 翻译单元（以 C++ 包含 buddy_alloc.h 实例化实现） | 用户测试源 | ✅ 是（1 个独立用例） | ✅ CMake `buddy_cpp_translation_unit` / clang++ 编译 | ✅ 运行 | rc=0 通过 |
| `test-fuzz.c` — fuzz 驱动（读 stdin 的分配/释放/断言循环） | fuzz 驱动（非离散用例） | ❌ 否（驱动型，不计数） | ❌ 上游 CMake/Makefile 主目标均未包含 | ⚠️ 独立编译尝试失败 | 失败：`call to undeclared function 'buddy_tree'`——头文件仅前向声明 `struct buddy_tree;` 无 `buddy_tree()` 函数（上游缺陷，非本库问题）；按台账记录不计数 |
| `bench.c` — 基准程序（1GiB arena 分配往返计时） | 基准（非用例） | ❌ 否（基准不计数） | ✅ CMake `buddy_bench` / clang 编译 | ✅ 运行 | rc=0（总耗时约 23s，Allocation/Freeing 输出正常） |
| `Makefile` targets：`test`（需 cppcheck+llvm-cov+gcov）、`test-multiplatform`（需 powerpc64/aarch64/i686/powerpc 交叉 gcc）、`test-cppcheck`、`check-recursion`（cflow）、`test-cpp-translation-unit` | 测试脚本/工具链目标 | 见说明 | ❌ 本平台缺失工具链 | ❌ 未运行 | cppcheck/gcov/交叉 gcc 均不可用（`command -v` 实测 NO；cflow 存在但 test 主目标仍缺 cppcheck）；已用等价 clang 直编 + CMake 双路径覆盖 166 个真实用例 |

统计口径（可复制枚举规则：`grep -E '^void (test_\w+)\('` 于官方 tag 源码，main() 调用集合程序化比对）：

- `source_declared_total` = **166**（tests.c 165 个独立 `test_*` 用例 + testcxx.cpp 1 个 C++ TU 用例；fuzz 驱动与基准不计独立用例）
- `configured_executable_total` = **166**（当前 OHOS 配置下 CMake/直接编译均实例化全部 166；ctest -N 注册 = 0，执行走直接运行路径）
- `executed_passed_total` = **166**；failed = **0**；uninstantiated = **0**
- 全量通过率 = **166/166 (100.0%)**；当前配置可执行集合通过率 = **166/166 (100.0%)**

逐项映射（源码声明 → 条件 → 目标 → 注册 → 日志）：
- `tests.c` 165 函数 → 无互斥宏（全量进入 main 调用，脚本核验 defined==called==165）→ `buddy_tests` → ctest 未注册（直接执行）→ `$HOME/tmp/buddy_tests_run.log`（rc=0）
- `testcxx.cpp` → C++11 无条件分支 → `buddy_cpp_translation_unit` → 直接执行 → rc=0
- `test-fuzz.c` → 上游未纳入构建目标 → 无目标 → 独立编译失败日志（buddy_tree 未声明，首错+恢复条件：上游修复头文件声明或该入口供 fuzz 工具链使用）

## HarmonyOS 专项测试 + test_package + 消费者

- `test_package/test_ohos.c`（鸿蒙专项，独立于上游）：64B 对齐 arena 返回指针按 64 对齐、embed 内嵌元数据、resize 扩张+can_shrink、safe_free 双重释放保护（first=SUCCESS second=2）、256MiB 大 arena 往返——独立编译运行 rc=0，断言全过（`$HOME/tmp/test_ohos` 日志）。
- `test_package/test_consumer.c`（消费者用例）：仅经公开头文件+公开 API（buddy_init/malloc/free/alloc_size/arena_free_size）的上层业务模拟——独立编译运行 rc=0（`$HOME/tmp/test_consumer` 日志）。
- test_package 经 conan create 在 ohos-aarch64 profile 下编译链接运行：G2 conan create PASS（reports/conan-create.log）。

## Conan / finish / W2 / W3

- conan-verify：G1 PASS（header-only 显式 build()）、G2 conan create PASS（经 ghfast.top 官方镜像取源，sha256 一致）、G3 PASS（无系统同名库）、G4 PASS；L2/L4/L5 按脚本执行（reports/conan-verify-report.md）。
- finish：W2 结构 PASS、R36 依赖 PASS（无依赖）、W3 本地 CI 模拟 PASS（reports/w3-local-ci.log）；状态 built。
- 上游测试统计（双口径）：见上表，166/166 (100.0%)。

## W2/W3 基线隔离复验证据（其他库基线文件）

finish W3 首次失败命中 main 基线已提交的其他库空标记文件（JC1+JC5，full 模式 `git ls-files` 索引扫描）。隔离复验四步：

- 路径：`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`
- pre_sha256（隔离前）：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（三处均空文件）
- isolation_command：`git rm --cached archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified archives/k/kics/2.1.20/.staging-verified`
- rerun_command：`python3 scripts/ohc-run.py finish buddy_alloc 1.3.2 built`；rerun_exit_code：0（W3 PASS）
- restore_command：`git reset -q HEAD -- <3 paths>` + `cp` 恢复工作区空文件
- post_sha256（恢复后）：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` == pre_sha256 ✅
- 当前库 diff/staged/PR 不含上述路径（`git diff HEAD --name-only` 无 cloog/kics）✅
- 未修改、未提交、未写入知识库/PR 这些基线文件 ✅

## Result

- 配方在 OpenHarmony aarch64 实测通过（conan-verify G1-G4 + finish W2/W3），上游测试 166/166 (100.0%)，鸿蒙专项与消费者用例实跑通过。
- 归档状态：built（远端 CI 发布流水线合并后由 upload 升级 published）。
