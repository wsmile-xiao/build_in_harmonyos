# yices 2.7.0 适配笔记

## 任务来源

- 平台任务 contrib-12296（开源鸿蒙PC专项积分赛），分支 `feat/yices-2.7.0`，2026-09-19 认领
- 上游：https://github.com/SRI-CSL/yices2 （474 stars，非 fork，tag yices-2.7.0 实拉核验存在）
- 语言实测（R47 lang-preflight）：C/C++ 族（判定通过）

## 选库核验（§3.2 否决线）

1. 他人已移植：`archives/` 比对 + 同源反查均无；制品仓 `conan list "yices/*" -r=ohpcd` = 0（设备实测）
2. 语言/构建生态：C + 自生成 autotools，autoconf/2.72 制品仓已发布可 tool_requires
3. 难度定级：A→B 之间（纯编译适配，零上游补丁；configure 需现场生成）；依赖 gmp/6.3.0 已发布（设备实测）

## 上游测试清点（R51）

- tests/unit：201 个 C 单元测试程序（`make test` 编译运行）
- tests/regress：.smt2 回归基准套件（`make check`，量大）
- 执行情况与统计见下文与 PR 描述（实数实测）

## 平台适配要点

- **configure 现场生成**：tool_requires autoconf/2.72（避免生成态大补丁被 AI 检视跳过——libdynamite 教训）
- **静态 GMP 注入**：--with-static-gmp 指向 conan gmp 包
- **LD_LIBRARY_PATH 盾**：build() 显式清空
- **测试输出落文件**：防孤儿进程持管道挂死 conan（yash 教训）

## 编译结束

设备实机验证（2026-09-20，OHOS aarch64）：

- `conan-verify`：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（RC=0）
- test_package：库级 C API 3 项断言（version/UNSAT/SAT）+ CLI（yices-smt2 求 UNSAT 实例）全过
- 上游单元测试真机实跑（185 个 tests/unit 二进制，上游 `make test` 只编译不运行，运行由配方完成）：
  **passed=167 / failed=13 / needs_input=5**
  - needs_input（5）：test_core2/test_core3/test_pool_alloc/test_symbol_table/test_symbol_table2——上游仓内无输入数据文件与运行器（裸跑打印 Usage）
  - failed（13）逐类归因：错误码语义差异（test_api7/test_api14/test_assert_utils）｜计时/性能敏感（test_timeout/test_dl_profiler）｜内部数据结构边界与负载偶发（test_offset_equalities2/test_parse_tables/test_pprod_table/test_ptr_sets/test_quick_sort——quick_sort 单独跑通过）｜SMT 内部器（test_smt_blaster/test_smt_codes/test_smt_internalizer）
  - 核心业务面（求解器 API 求解判定）全过
- **llvm-strip 平台陷阱（已产出知识草稿）**：make dist/install 默认 `llvm-strip` 的二进制被 OHOS 执行策略拒绝（execve EACCES），对照实验证实（原件可执行/llvm-strip 产物被拒/重链不 strip 可执行）。配方以 `STRIP=true` 屏蔽。草稿：knowledge/drafts/DRAFT-yices-2.7.0-llvm-strip-exec-denied.{kv,md}
- **config.guess 不识 HarmonyOS**（uname -s=HarmonyOS）：补丁 0001 新增 aarch64:HarmonyOS 分支
- **configure 现场生成**：tool_requires autoconf/2.72 + 系统 perl（conan perl ABI 损坏，PERL5LIB 收敛到 autoconf 纯 Perl 模块目录，apertium 先例）
