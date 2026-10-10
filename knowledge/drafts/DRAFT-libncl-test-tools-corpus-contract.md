# libncl：测试工具、非空语料与执行次数必须一起接入

状态：路径 B 知识草稿；适配证据来自 [PR #12588](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12588)，该 PR 已于 2026-09-28 16:47:39（北京时间）合入，固定代码此前通过官方 CI #61823。本草稿不声明已获得 B 积分。

## 问题与适用范围

有些 C/C++ 库提供两套并不等价的构建入口：CMake 默认只构建库，上游测试却依赖另外的命令行工具和磁盘语料。把旧 Python 测试驱动移植到 Python 3，并不能证明这套测试已被正确接入。

本例固定于 libncl `2.1.21-git20210811.b1213a7`，上游 [mtholder/ncl@b1213a78003629483426d83258d8ab9e43ab20b1](https://github.com/mtholder/ncl/tree/b1213a78003629483426d83258d8ab9e43ab20b1)。原版 CMake 只定义 `ncl_shared`、`ncl_static`；上游语料测试还需要 `NEXUSnormalizer`、`NCLconverter`、`ncltest`、`NEXUStranslate`。`test/roundTripNCLTest.py` 在 glob 未发现输入时打印 `No files to test` 并返回 0。

因此有三个不同的验收条件：**工具构建成功、预期语料实际发现、预期程序调用实际执行且结果正确**。任何一项都不能由其他两项推断。

适用于有独立原生测试工具、文件语料和外部脚本驱动的库。已有完整 CTest 注册并严格检查测试发现/执行结果的库，不必照搬这套接入；正常允许零输入的业务程序也不应一律改为失败。

知识匹配入口将 `error_signature` 按 `|` 分段并作字面子串匹配。本条用驱动实际的失败提示识别空语料、上游驱动失败、调用数或总量不符；`NCL_BUILD_TEST_TOOLS=ON` 和成功日志里的 `expected_executions=... rc=0` 只是上下文，不能单独判为错误。`No files to test` 只在预期非空的上游语料测试中表示缺口；原版驱动曾对同一提示返回 0，仍须结合输入范围和退出状态判断。

## 根因与最小方案

1. **构建图缺测试工具。** 在库的 CMake 中加入默认关闭的 `NCL_BUILD_TEST_TOOLS`，开启时构建四个上游工具并链接 NCL；Conan 测试构建显式开启。工具仅用于测试，不因此加入库包的安装接口。
2. **迁移解释器后仍有零语料成功分支。** 保留上游语料及断言语义，迁移 `cStringIO`、旧文件/迭代接口等 Python 2 用法；当本应有语料的测试组没有输入时返回非零状态。此项与 Python 语法迁移分开验证。
3. **发现数不等于执行数。** 测试调用者按固定上游的实际测试分组核对输入数、工具调用数及预期输出，不只读取最终退出码。合法样例的归一化往返通常调用两次；非法样例预期拒绝，不能全部要求子进程 rc0；转换器还应比较预期输出。

对应实现全部在关联适配 PR 的固定提交 [`0a0d0c429947e2a123ce3c9d513542a3a3a4f737`](https://atomgit.com/orrkri/build_in_harmonyos/commit/0a0d0c429947e2a123ce3c9d513542a3a3a4f737)：

- `archives/l/libncl/2.1.21-git20210811.b1213a7/patches/0001-CMakeLists.txt.patch`：测试工具构建入口。
- 同目录 `patches/0002-test-roundTripNCLTest.py.patch`：Python 3 迁移及空语料失败。
- 同目录 `upstream-tests.py` 与 `conanfile.py`：工具/语料/调用数接入实际 Conan 构建。

本知识补充不修改上述配方、补丁或测试。

## 最小前后对照

源码归档 SHA-256：`fa83172b928036be212e1422cd14f7d242063e7a829fff9d325aed20d4995f7f`。

使用完整原版驱动及固定补丁，在 Windows/Python 3 的隔离空目录中做机制对照；这不是修前鸿蒙真机测试。

| 输入状态 | 实测结果 | 能证明的事实 |
|---|---|---|
| 完整原版驱动 + 空语料目录 | rc1，`ModuleNotFoundError: No module named 'cStringIO'` | 原版先在导入阶段失败，尚未进入空语料分支 |
| 应用 Python 3 补丁，但在临时副本中仅恢复原来的空语料 `sys.exit(0)` | rc0，`No files to test (looking for *.nex *.tre files)` | 仅迁移 Python 运行时，仍会将缺语料误判成功 |
| 完整候选补丁 + 相同空目录 | rc1，相同提示 | 候选对空语料按失败处理 |

复现方式：从上述固定归档解包，用关联 PR 的 `0002` 原始补丁；执行 `python3 test/roundTripNCLTest.py <现存可执行文件绝对路径> <空输入目录> <空输出目录>`。该可执行文件参数可用当前 Python 本身，因为空语料路径不会调用它。第二行只在临时副本恢复那一处退出码，其他字节及参数保持一致。

原版默认 CMake 不含四工具的结论来自完整源码中的构建声明检查，不写成已运行的配置测试。原始 Python 3 导入失败也不能写成“原版真机测试曾全绿”。

## 已有鸿蒙验证与计数边界

关联适配的 H1-009 在 OHOS aarch64、Clang 15/libc++ 环境构建默认静态包。原始 Conan 日志包含四工具链接及下列结果：

```text
normalizer-nts-valid: discovered=31 executed=62 expected_executions=62 rc=0
normalizer-nts-invalid: discovered=1 executed=1 expected_executions=1 rc=0
converter-expected-xml: discovered=1 executed=1 expected_executions=1 rc=0
SUMMARY status=passed discovered=52 executed=97
LIBNCL_CONSUMER_PASS assertions=10
```

这里的 rc 是相应测试组的判定结果，非法语料组的成功意味着工具按预期拒绝了输入。上游 52 个唯一输入分为 11 组，记录 97 次调用；脚本按驱动的命令输出行计数，并结合返回值及预期输出验证，不是操作系统进程跟踪。消费者是另一个程序、10 条断言。这三种计数不相加作为上游用例数。上游原有但未被 Makefile 接入的 `NTSInvalidIn/multitax.nex` 已计入 52 个输入，不能写成新增自创样例。

原始结果包 SHA-256：`3745782eae1c00616668e32c156a02b6d3c4341dcf26f8e727d35ea234ed834d`。W3 的 `setup.sh` 和 `build_and_test.sh` 均 rc0；历史完整 `finish` rc1、PF9/W4 例外仍以关联 PR 披露为准，本知识稿不改写为完整流程通过。

当前固定代码的[官方 CI #61823](https://ohpcd.atomgit.com/ci?id=61823)报告 Conan test_package、L0、L1 通过；该回执证明官方执行通过，不替代上述 52/97/10 的原始明细。知识文件本身不改变受测代码，本轮复用这些历史真机证据。

## 与已有知识的区别

| 近邻 | 已解决的事情 | 本条补充的条件 |
|---|---|---|
| E269 | Python 2 测试驱动迁移到 Python 3 | 迁移后还须把独立工具加入实际构建图，并让空语料及调用数缺口成为失败 |
| E321 | lite 系 header-only 配方与 CTest 入口恢复 | 本例是有原生库、外部 CLI、磁盘语料的非 CTest 驱动，不能套用单一 `cmake.test()` |
| E231 | 测试发现绑定已校验的源码归档 | 即使来源正确，构建图和执行次数仍可能没有覆盖已发现的语料 |
| E363 | Bash 环境准备/汇总失败产生零测试假绿 | 本例的 Python 驱动显式以零退出码接受空 glob，且测试 CLI 不在默认构建图 |
| DRAFT-doctest-partial-target-zero-case-false-green | 缺测试翻译单元导致框架注册零用例 | 本例不依赖 doctest 注册，核查对象是外部工具、文件语料和往返调用 |
| DRAFT-trimmed-build-vs-full-build-test-runnability | 精简构建关闭程序时，须恢复完整构建或必要工具，并证明测试实际执行 | 本例的默认 CMake 根本未声明四个工具，恢复默认配置无效；须参考上游另一构建入口补目标，并另行修复 Python 3 迁移后的空 glob 成功分支及逐组往返调用计数 |

“恢复测试工具、证明实际执行”已有近邻覆盖。本条的增量是**默认 CMake 与另一套上游测试入口脱节时，补齐目标，并检查脚本迁移后的空语料分支和每个输入的调用次数**，不是泛称“测试数量不能为零”。若维护者认为应并入近邻条目，可合并这部分证据，不重复计分。

## 使用时避免

- 不通过删除语料、放宽断言或只跑消费者来代替上游测试接入。
- 不把进程 rc0、脚本可导入、工具文件存在单独当成上游测试通过。
- 不把 97 次调用写成 97 个唯一用例，也不把 10 条消费者断言写成 10 个消费者程序。
- 不硬编码别的版本的 52/97；从该版本上游分组、输入和预期行为重新建立计数。

作者：orrkri。日期：2026-09-27。正式知识编号、纳入与积分由维护者确认。
