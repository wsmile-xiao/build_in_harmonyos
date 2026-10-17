# DRAFT-ci-lowmem-worker-link-oom-mitigation：CI 低内存 worker 链接期 OOM 削峰——重模板测试 -g0 不够时降 -Os（仅测试降档，库保持 -O2）

> Contributor: calbee21 | Status: pending-editor-review | Updated: 2026-09-07
> Source: boost1.84-context 1.84.0 适配（PR #8651）；三次跨 PR 复现链（#8435 container / #8646 prg_exec_monitor / #8651 context）

## 背景
CI 集群存在内存配额偏低的 worker（实测 CI-007 / CI-019 / CI-021）。重模板类库的测试（Boost container 的 tree/vector 家族、context 的纤维/协程、prg_exec_monitor 的异常路径）经完整 boost 头树做大规模模板实例化，-O2 下链接期 clang/lld 内存峰值很容易超限。

## 错误特征
```text
clang++: error: linker command failed due to signal (use -v to see invocation)
```
CI 侧表现为 COMPILE_FAIL / "上游官方测试未通过"（ohpcd-robot 归为测试失败，实际是测试二进制链接期链接器被 SIGKILL）。

### 诊断特征（资源病 vs 配方错的判定）
- 同 commit 多机结果不一：boost1.84-context commit 49f3c088f 在 CI-026 全绿（#41267），同一 commit /rebuild 到 CI-021 五个测试全部被杀（#41383）——若是配方问题任何机器都该失败。
- 本地绿 CI 红：prg_exec_monitor #41251 @CI-019 四个测试全杀，本地 16G 开发机同 commit 4/4 全绿。
- 结论口径：两绿一红/彼绿此红 = CI worker 资源差异，不是配方问题。

## 根因
低内存 worker 的内存限额 < 重模板测试在 -O2 -g 下链接期的内存峰值（调试信息 + 模板实例化符号 + 优化中间数据结构）。链接器进程（lld）被 OOM killer SIGKILL，clang 汇报 "linker command failed due to signal"。

## 修复（削峰梯度：逐级降档，只动测试，库不降）
1. 第一档（基础）：Release 档测试编译统一 -g0——去调试信息，砍链接内存最大头（对多数包已够）。
2. 第二档（点名降档）：-g0 仍不够时，重模板测试名单 _HEAVY_TESTS 单独降 -Os -DNDEBUG -g0（-Os 为代码尺寸优先档，模板实例化更省内存；断言语义不受优化级别影响）。boost1.84-container 形态（commit 25f3a1638）：
   ```python
   _HEAVY_TESTS = frozenset({
       "tree_test.cpp", "unsynchronized_pool_resource_test.cpp",
       "uses_allocator_test.cpp", "vector_options_test.cpp", "vector_test.cpp",
   })
   if name in self._HEAVY_TESTS:
       flags = base_flags.replace("-O2 -DNDEBUG -g0", "-Os -DNDEBUG -g0")
   ```
3. 第三档（全量降档）：名单点名仍不够（context 的纤维/协程测试整包都吃链接内存）时，全部测试编译降 -Os -DNDEBUG -g0。boost1.84-context 形态（commit e5403b9bc）：
   ```python
   if self.settings.build_type == "Debug":
       test_flags = base_flags          # Debug 本就 -O0，不动
   else:
       test_flags = base_flags.replace("-O2 -DNDEBUG -g0", "-Os -DNDEBUG -g0")
   self._run_upstream_tests(boost_root, cxx, test_flags)
   ```

### 设计要点
- 仅测试降档，库本体保持 -O2：产物性能口径不受影响（libboost_context.a 仍 -O2 编译归档）。
- 测试逐个串行编译运行（for 循环单进程，无并行 fork——单测试内存峰值可控）。
- 不改测试逻辑/源码（测试 .cpp 逐字节未动），run-fail/断言判定不受优化级别影响。

## 验证/命令
三次跨 PR 复现链（全部真实 CI 构建）：
| PR | 失败 CI（低内存 worker） | 修复 commit | 修复后 CI |
|----|--------------------------|-------------|-----------|
| #8435 boost1.84-container | #41130 @CI-007、#41135 @CI-021（5 个重模板测试 linker signal） | 25f3a1638（-g0 + 5 重测试 -Os） | #41154 @CI-012 绿 |
| #8646 boost1.84-prg_exec_monitor | #41251 @CI-019（4 个测试 linker signal） | 049f42da9（4 测试全量 -Os -g0） | #41278 @CI-017 绿 |
| #8651 boost1.84-context | #41267 绿 @CI-026 → 同 commit #41383 红 @CI-021（-g0 已有仍不够） | e5403b9bc（测试全量 -Os，库 -O2） | #41599 @CI-036 绿 |

本地复验：conan create 全绿（context：上游测试 5/5 + test_package 1/1）。

## 降级方案
病机轮换：/rebuild 重触发让 CI 调度到常规内存 worker（实测同 commit 换机即绿——#8435 两红一绿、#8651 红后绿均为此模式）；仍不够时个别极端测试可再降 -O1/-O0。不建议给库本体降档（影响产物性能口径）、不建议跳过测试（违反上游测试集成规则）。

## 与现有条目的关系
- E266 的 error_signature 字面含 "clang.*error: linker command failed due to signal"，但其根因是 OHOS lld 缺 libxml2.so.16 运行时依赖（链接器起不来），修法是换 GNU ld——与本条"低内存 worker 链接内存峰值超限"根因不同、修法不同。
- E292 覆盖 CTest 运行期 OOM（allocator/overcommit），不覆盖链接期 linker signal。
- E368 是 meson 故障注入（人为模拟 OOM），非真实资源边界。
- E429（draft）是测试防过度优化（-fno-* 阻断），方向与本条相反（主动降档削峰）。

## 关键词
linker command failed due to signal, linker signal, COMPILE_FAIL, 低内存 worker, 削峰, -Os, -g0, 重模板, 模板实例化, 链接内存峰值, CI worker, OOM, boost container, boost context, fiber, coroutine, prg_exec_monitor, OHOS
