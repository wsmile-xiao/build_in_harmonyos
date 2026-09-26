# notes.md — metaeuk 7-bba0d80 OHOS 适配笔记（DS-18，2026-09-21）

## 1. 任务与来源

- 平台任务 8821（活动：开源鸿蒙PC专项积分赛-依赖，activity_id=6）
- 上游：GitHub soedinglab/metaeuk tag 7-bba0d80（codeload 归档 tarball）
- worktree：`~/qzy/DS-18-metaeuk-7-bba0d80`，分支 `feat/metaeuk-7-bba0d80`
  （基线 origin/main=42a8cc8fd8，无提交）
- CONAN_HOME：`~/tmp/ch/home-ds18-metaeuk`
- 源码缓存：`~/tmp/uc2/ds18-metaeuk/metaeuk-7-bba0d80.tar.gz`
  （sha256 45eff3cb…）

## 2. W0 依赖核验

无外部依赖：MMseqs2 完整源码以 `lib/mmseqs/` **vendored 普通目录**形式内置于
上游 tag 归档（`tar tzf` 实测 `metaeuk-7-bba0d80/lib/mmseqs/src/` 前缀下 323
条目、其中 311 个是文件），随 tarball 完整发布，构建零 conan 依赖。
注意：GitHub codeload tag 归档**不含任何 submodule 内容**——根 `.gitmodules`
只声明两个子模块 `tests`（soedinglab/metaeuk-regression）与
`lib/mmseqs/util/regression`（soedinglab/MMseqs2-Regression），二者在 tarball
与解包树里都是**空目录**（`tar tzf | grep ^…/tests/` 仅 1 条目录条目、0 个文件；
`ls -A` 实测两处条目数均为 0）；`lib/mmseqs` 本身**不是** submodule
（`.gitmodules` 中无该项）。
conanfile `requirements()` 为空，经 PF4 依赖闸天然通过。

## 3. W0b 历史经验

`archives/m/` 无 metaeuk 历史（首适）。语言：cpp（CMake，纯 C++ 项目）。

## 4. 上游测试五维账本

| 维度 | 数值 | 口径 |
|---|---|---|
| N_static | 0 | 全源码树**没有任何测试注册入口**：`add_test(` / `enable_testing` / `include(CTest)` 三个模式在 `--include=CMakeLists.txt --include=*.cmake` 下命中 0/0/0，树内亦无 `Makefile.am`/`configure.ac`（automake `TESTS` 口径 0）。随包另有一棵 `lib/mmseqs/src/test/` 手工 harness（性质是上游自测程序，非注册可执行测试），其排除理由见下方「N_static 清点依据」；`tests/`（metaeuk-regression 回归数据集仓库）与 `lib/mmseqs/util/regression` 是未随 tarball 发布的空子模块；azure-pipelines/.cirrus 为外部下载驱动回归，非源码注册测试 |
| N_registered | 0 | 同上（无注册入口 ⇒ 无可注册用例） |
| N_executed | 0 | 无可执行上游套件（如实申报，不虚构） |
| 未执行分类 | 0 | — |
| N_consumer | 1 | test_package/metaeuk_consumer：5 项行为断言（裸 metaeuk 版本横幅含 7-bba0d80 / 帮助退出码 / 参数校验 / easy-predict 端到端产物名 / createdb 非空往返） |

### N_static 清点依据（2026-09-23 本机实测，源码树
`~/tmp/uc2/ds18-metaeuk/metaeuk-7-bba0d80`）

1. **注册入口为 0**：
   `grep -rIn "add_test(" --include=CMakeLists.txt --include=*.cmake .` → 0 命中；
   同口径 `enable_testing` → 0；`include(CTest)` → 0（全树唯一相近命中是
   `lib/mmseqs/src/test/CMakeLists.txt:1 include(MMseqsSetupTest)`，那是自定义
   module 名、不是 CTest）。放宽到任意文件类型再查
   `add_test *(\|enable_testing` 仍为 0。`find . -name Makefile.am` /
   `configure.ac` 均为 0 ⇒ 无 automake `TESTS`。
2. **`lib/mmseqs/src/test/` 的真实构成**（42 条目 = 36 个 `.cpp` +
   `CMakeLists.txt` + 名为 `0` 的文件 + `dataGap`/`dataGap.index`/`dataLinear`/
   `dataLinear.index` 四个测试数据文件）：36 个 `.cpp` 中 **35 个自带
   `int main`**（唯一例外 `TestOrf.cpp`），即每个文件是一个**独立手工自测程序**；
   `assert(` 仅出现在 3 个文件、共 29 处（TestTaxExpr 15 / TestUtil 10 /
   TestTinyExpr 4）。`CMakeLists.txt:3-36` 的 `set(TESTS ...)` 列出 32 项，其中
   首项 `#TestAdjustedKmerIterator.cpp` 被注释掉 ⇒ 实际 31 项，经
   `FOREACH → mmseqs_setup_test(${TEST})` 处理。
   **这批文件按性质应归类为"上游手工自测 harness（兼作回归工具）"，
   不属于"注册可执行测试"，故不折算成用例数。**
3. **为何在本包配置下永不可达**（两级锁死）：
   - 根 `CMakeLists.txt:6` `set(FRAMEWORK_ONLY 1 CACHE INTERNAL "" FORCE)`，
     随后 `:8 add_subdirectory(lib/mmseqs)`（根文件实测共 11 行，
     `wc -l` = 11）；`lib/mmseqs/CMakeLists.txt:7` 的
     `set(FRAMEWORK_ONLY 0 CACHE BOOL ...)` **无 FORCE**，按 CMake 语义不能覆盖
     已存在的 INTERNAL 缓存项 ⇒ FRAMEWORK_ONLY 恒为 1。
   - `lib/mmseqs/src/CMakeLists.txt:243` 起 `if (NOT FRAMEWORK_ONLY)` 整块
     （含 `:253 if (HAVE_TESTS)` / `:254 add_subdirectory(test)`）在本包配置下
     永不进入；`HAVE_TESTS` 自身在 `:2` 也默认为 0。
   - **即便强行开启也不产生 CTest 用例**：`lib/mmseqs/cmake/MMseqsSetupTest.cmake`
     的 `mmseqs_setup_test()` 函数体只有 `include(MMseqsSetupDerivedTarget)` +
     `string(...)` + `add_executable(${BASE_NAME} ${NAME})` +
     `mmseqs_setup_derived_target()` + `target_link_libraries(... version)`，
     **不含 `add_test()`** ⇒ 只造可执行文件、不注册测试，需人工逐个运行。
4. **子模块侧**：`tests/`（metaeuk-regression，回归数据集与比对脚本）与
   `lib/mmseqs/util/regression`（MMseqs2-Regression）在 tarball 内是空目录，
   且其内容是外部下载驱动的回归比对流程，不构成源码注册的静态用例。

⇒ 上述四点合起来支撑 **N_static = 0**（不是"上游没有测试代码"，而是
"上游测试代码没有任何注册进 CTest/automake 的入口，且在本包配置下不参与构建"）。

### 实测段（2026-09-23 conan-verify 回填）

- `conan-verify metaeuk 7-bba0d80`：**G0-G4 全 PASS**（verdict PASS）。
  本轮 `conan create` **命中 binary cache**（配方未改，未重编主包 258 个 C++ TU），
  主包真编译证据在 `~/tmp/uc2/zhuli1-metaeuk/g2-pass-build-20260923T0302/`
  （本轮 create 日志不作为"编译过"证据）。
- test_package/consumer.cpp 经包内 clang++ 编译 + `conan test` 执行，输出
  `consumer test passed: 5 assertions OK`。5 项断言逐项实测：
  1. 裸 `metaeuk`（无 tty / popen）rc=0 且 stdout 含 `metaeuk Version: 7-bba0d80`；
  2. `metaeuk -h` rc=0；
  3. `metaeuk --no-such-option-xyz` rc!=0；
  4a. `easy-predict` 合成 contigs/targets rc=0 且按实测产物名 `predictions.fa.fas`
      生成（合成序列零命中 → 产物 0 字节，仅证工作流跑通，**不证预测正确性**）；
  4b. `createdb` 合成 FASTA rc=0 且序列库 `db`(140B)/头文件 `db_h`(48B) **非空**
      （自含、可证伪，不依赖外部 target 数据库）。

## 5. 适配要点

1. **CMake 4 兼容**：上游 `cmake_minimum_required(2.8.12)`，设备 CMake 4.1.2
   直接拒绝；按知识库 `knowledge/drafts/DRAFT-E321-cmake4-policy-version-minimum.kv`
   （该条目 `# Software:` 实测为 **etcd-cpp-apiv3 0.15.4**，即其原始验证实例；
   知识库内不存在「cpputest + `CMAKE_POLICY_VERSION_MINIMUM`」条目）以命令行
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cmake.configure(variables=...)）
   注入——`tc.variables` 写 toolchain 文件时序无效，必须在任何 CMakeLists
   解析前生效。本包是该机制在 CMake 2.8.x 老基线上的再次命中。
2. **版本注入**：tag tarball 无 .git，上游 GetGitRevisionDescription 会编译出
   "unknown" 版本；按上游支持的机制传 `VERSION_OVERRIDE=7-bba0d80`。
   注：`--version` 并非合法子命令（会以非零退出），实测裸 `metaeuk`
   （非 tty）rc=0 且 stdout 含 `metaeuk Version: 7-bba0d80`，消费者测试
   断言据此取自裸调用。
3. **SIMD 固定**：`NATIVE_ARCH=0 + HAVE_ARM8=1` → `-march=armv8-a+simd`，
   避免 CI worker 主机探测差异；aarch64 基线 NEON。
4. **资源编译**：data/ 的 easypredict.sh 等 shell 工作流经
   MMseqsResourceCompiler 编译为资源头随二进制分发，无外部工具依赖。
5. 单二进制 `metaeuk` + 内嵌子命令（easy-predict/predictexons/...），
   R38 commands.json 已声明。

## 6. 产物

- bin/metaeuk（单二进制，含全部子命令与内嵌资源脚本）
- licenses/LICENCE.md

## 7. 已知边界

- 上游回归框架（`tests/` = soedinglab/metaeuk-regression，及
  `lib/mmseqs/util/regression` = MMseqs2-Regression）是**未随 tag tarball 发布的
  子模块**（见 §2 实测），运行需外部下载数据集，不在源码测试口径内；
  `lib/mmseqs/src/test/` 的上游手工自测 harness 在本包配置下不参与构建、
  也不注册进 CTest（见 §4「N_static 清点依据」）。两轨都不是"已注册用例"，
  故如实记 N_static=0，消费者测试以真实运行补位。
- MMseqs2 大体量源码，jobs=2 构建预计 30-60 分钟；CI 超时预算若不足需
  `timeout set metaeuk 7-bba0d80 <秒>`（以实测为准）。
---

**编译结束**: 2026-09-23 07:57
**最终状态**: built
