# lpsolve 5.5.2.14 适配笔记

## 编译环境

- 构建系统: cmake（配方内生成 CMakeLists，对齐上游 lpsolve55/ccc 与 lp_solve/ccc 的源码集合与预处理定义）
- 编译日期: 2026-09-19
- 编译器: clang / clang++
- 平台: HarmonyOS aarch64（Linux/OHOS 双兼容，settings.os 校验仅允许 Linux 与 OHOS）
- 状态: built（待真机预检通过后由 HMBS 统一提交）

## 上游信息

- 上游仓库: https://github.com/lp-solve/lp_solve
- 源码包: https://github.com/lp-solve/lp_solve/releases/download/5.5.2.14/lp_solve_5.5.2.14_source.tar.gz
- SHA256: a4bbdc881128bdbe920a38e134c9add5db47f9aa814a0a018ba940b0f3c278c3
- 版本策略: 首次适配，使用上游原始版本号 5.5.2.14，无后缀
- 依赖: 无外部依赖，仅系统库 m、dl

## 编译步骤

1. `get()` 解压官方源码包（strip_root=True）。
2. 配方在 `build()` 内生成顶层 CMakeLists.txt，源码集合与宏定义对齐上游 ccc 脚本：YY_NEVER_INTERACTIVE、PARSER_LP、INVERSE_ACTIVE=INVERSE_LUSOL、RoleIsExternalInvEngine。
3. `cmake.configure()` + `cmake.build()` 构建静态/动态库 lpsolve55 与可执行文件 lp_solve。
4. `cmake.install()` 安装 lib、bin、include/lpsolve 全量头文件（含 shared、bfp、colamd 子目录）与 LICENSE。

## 上游测试审计

- 源码包顶层无 tests/、test/ 目录，无 CTest、make check 等测试目标。
- lpsolve55/ccc 与 lp_solve/ccc 仅编译库与 CLI，不构建任何测试可执行文件。
- demo 目录为使用示例，非自动化测试框架。
- 结论：上游 5.5.2.14 无自动化测试，test_package/MANIFEST.yml 已写入 upstream_tests_exist: false 与完整 upstream_test_audit，build() 输出 HMBS_UPSTREAM_TEST_RESULT status no_tests。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows 检出上游 main 失败 invalid path | archives/g/gama 历史文件含回车符文件名，Windows Win32 非法 | 设置 core.protectNTFS=false 后 read-tree 建索引，对问题文件置 skip-worktree，再 reset --hard 恢复工作树 |
| 2 | Windows 大小写冲突 libXext/libxext | 远端同时存在仅大小写不同的目录，Windows 同一目录合并 | 保持现状不提交无关改动，本 PR 仅含 archives/l/lpsolve 目录 |
| 3 | 上游无标准构建文件 | 仅提供 ccc shell 脚本 | 配方内生成等价 CMake，Conan 接管编译器与架构 |
| 4 | 真机 cmake 编译器识别失败：`CMAKE_C_COMPILER: /data/service/hnp/bin/clang` identification unknown | `generate()` 内 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"` 与 Conan CMakeToolchain 生成的 HarmonyOS 工具链冲突，破坏 HNP clang 的 sysroot/flags 注入 | 删除该覆盖，沿用 Conan 工具链原生 HarmonyOS 配置（"unknown to cmake" 仅为警告级，不阻塞 POSIX 库构建；同仓 lp_solve 配方与 ADAPTATION_GUIDE CMake 模板均不覆盖）；同步修复 test_package 以 `package_folder + bindirs` 绝对路径调用 lp_solve |
| 5 | 真机 `cmake.configure` 在 `project()` 处失败：`CMAKE_C_COMPILER: /data/service/hnp/bin/clang is not a full path to an existing compiler tool`（2026-09-20 预检，compile 阶段） | ohos-aarch64 profile 把 `tools.build:compiler_executables` 钉死在 `/data/service/hnp/bin/clang(++)`，该文件在当前预检 worker 上缺失，CMakeToolchain 将其原文烘焙进工具链文件；与 #4 的 SYSTEM_NAME 覆盖不同，本轮是编译器路径本身不存在 | 主配方与 test_package 均按 conf→PATH 顺序探测可用编译器（isfile 校验 + `shutil.which` 回退到 hmbs 前置 PATH），经 `CMAKE_C/CXX_COMPILER` 缓存变量强制传入并补丁工具链文件，同时在 `build()` 导出 `CC/CXX`；健康机上 resolved==钉死路径（无行为变化），缺失机上自动用 PATH clang 替代 |

## test_package 设计

- test_lpsolve.c 调用真实公共 C API：make_lp、set_obj_fn、add_constraint、solve、get_objective、get_variables、read_LP、delete_lp。
- 场景 1：求解两变量线性规划，校验最优值 10.0 与解 (2.0, 2.0)。
- 场景 2：故障注入 --fault-missing-model，要求 read_LP 对缺失文件返回 NULL。
- 场景 3：运行打包产物 lp_solve -h，验证 CLI 可执行。
- test() 输出 HMBS_TEST_PACKAGE_RESULT，discovered=3、passedCount=3。

## 验证结果

- 本地：Windows 环境不运行 conan，按任务守则等待 HMBS 真机预检。
- 真机：待 HMBS 后台同步代码树后执行 conan create，证据轮回填通过率。

## 补充说明

- 参考同类归档 archives/l/lp_solve/5.5.2.14 的源码集合与测试模型，新建 archives/l/lpsolve/5.5.2.14 并按现行 HMBS 门禁补齐 markers 与审计字段。
- 申请人：waylong，队伍：龙骑士。

## 2026-09-27 rule4 纠正（人工审查：上游 N=46，旧声明 N=0 少报）

- 旧审计只看了 release 源码包顶层，漏掉了 Git 仓库 `extra/UnitTest/` 回归套件，
  误报 `upstream_tests_exist: false`。复核结论：以 tag 5.5.2.14 为准，
  `extra/UnitTest/UnitTest.c` 的 `main()` 共调用 48 个测试入口
  （UnitTest1..UnitTest46 共 46 个编号用例 + UnitTest1presolve/UnitTest2presolve
  两个 presolve 变体），`void UnitTest*(` 定义数与 `main()` 调用数均为 48（已用脚本双向核对）。
- 审查口径 N=46 = 46 个编号用例；48 口径 = 46 编号 + 2 presolve 变体。
  本次声明 `upstream_test_total: 48`（`auto` 口径：单一自定义 harness，
  按 `main()` 调用计数），46 <= 48 不少报；可运行 46 个，2 个 presolve 因上游缺
  数据文件跳过并附 gaps 证据。
- 关键核实（tag 5.5.2.14 与 main 双查）：
  1. release 源码包确实不含测试（`build-targz-source.sh` 明确 `--exclude=extra`），
     所以把同 tag 的 `extra/UnitTest` 按原字节 vendor 到 `upstream_tests/`
    （UnitTest.c + 36 个模型/数据文件 + PROVENANCE.txt），不编造、不改断言。
  2. `UnitTest1presolve.lp` 在 tag 与 main 的 44 条目录清单中都不存在，
     两个 presolve 测试在任何平台都无法运行（`assert(lp != NULL)` 必 abort）。
     配方在构建副本上对这两处 `main()` 调用加 `fopen` 守卫并打印 SKIP 行，
     提交的 UnitTest.c 保持原字节；46 个可运行项不受影响。
  3. 代码读 `UnitTest42.lp`，tag 发货名为 `Unittest42.lp`（大小写差异）。
     配方在构建副本上复制为正确大小写后运行（Windows 工作树大小写不敏感，
     故该副本只存在于真机构建目录，不进提交）。
- 配方改动（`archives/l/lpsolve/5.5.2.14/conanfile.py`）：
  `exports_sources = "upstream_tests/*"`；`build()` 在 cmake 构建后编译
  上游 harness（二进制 `upstream_test`，与 `ccc` 同源文件、同宏、
  同头文件目录，`-O1 -lm -ldl`），以数据目录为 cwd 运行，逐行解析
  `^UnitTest<name>$` / `^SKIP` / `^Done$` 并自检
  `passed + failed == executed`、`executed + skipped <= discovered` 后输出
  `HMBS_UPSTREAM_TEST_RESULT`（discovered=48 静态审计，executed/skipped 来自日志，
  无字符串数数、无算术修补分支）；结果同时落盘
  `hmbs_upstream_result.json` 并随包发布到 `share/lpsolve/`。
- `test_package/conanfile.py` 的上游标记改为从包内 relay 文件原样复述
  （`_relay_upstream_result`）；relay 缺失时报 `failed` 说明原因，
  永不回退到 `no_tests` 虚假声明。
- `test_package/MANIFEST.yml`：`upstream_tests_exist: true`、
  `upstream_test_total: 48`、`upstream_test_count_method: auto`、
  `upstream_test_in_build: true`，附 48 项清单（46 passed + 2 skipped）与结构化审计。
- 本地 Windows 环境不运行 conan；等待 HMBS 真机预检回填实测数字。
  若预检出现非零失败项，按日志逐项补 gaps 证据，不凑数。
- 申请人：waylong，队伍：龙骑士。

## 2026-09-28 聚焦修复轮（rule4 打回复核 + 计数逻辑加固）

- 复核：工作树 main() 调用数 48（UnitTest1..UnitTest46 共 46 编号 + 2 presolve 变体），void 定义数 48，release 包排除 extra 故 vendor 同 tag 原字节，UnitTest1presolve.lp 双分支缺失，Unittest42.lp 大小写差异；声明 upstream_test_total 48 覆盖审查口径 N=46，不少报。
- 加固 _parse_upstream_log 失败分支：删除 skipped = discovered - executed 算术修补，executed/skipped 只来自日志行解析；非零退出且 executed>0 时 failed=1、passed=executed-1，其余失败保持 failed=0、passed=executed；恒等式自检保留，不凑数。
- 用模拟日志双用例校验：46 starts + 2 SKIP + Done 且 rc=0 报 passed 46/48；10 starts + 2 SKIP 无 Done 且 rc=1 报 executed=10、skipped=2、passed=9、failed=1，恒等式成立。
- 无关改动说明：archives/l/libXext 与 libxext 在 Windows 大小写不敏感文件系统上互映，工作树差异为环境遗留，未触碰，不进本 PR。
- 申请人：waylong，队伍：龙骑士。

## 2026-09-29 rule4 缺口覆盖修复（executed=45/skipped=2/缺口3但gaps只报2）

- 真机证据：discovered=48, executed=45, passed=45, failed=0, skipped=2, return_code=0；gaps 仅覆盖 2 项 presolve，缺 1 项未说明，判 incomplete。
- 静态核查：main() 48 项有序期望与 UnitTest.c 一致；全部 .lp/.mps 引用除 UnitTest1presolve.lp 外均已 vendor；单测起止行由 main() 打印，缺 1 起始行说明有 1 个期望项既无 start 也无 SKIP。
- 修复（conanfile.py）：新增 _UPSTREAM_EXPECTED 有序期望，仅用于命名缺口；_parse 计算 missing_names 与 unaccounted=discovered-executed-skipped，对 unaccounted>0 追加一条 gaps（exit!=0 或无 Done 判 test_failure，否则判 environment，detail 写明缺失名、exit 与 Done，evidence 写执行/跳过/退出码与 Done 状态）；fallback 计数改用 discovered-passed；保留单源计数与恒等式自检，不凑数。
- 诊断加固（构建副本）：main() 首行加 setvbuf(stdout,NULL,_IONBF,0)，保证 abort 时已有行落盘；提交的 UnitTest.c 保持原字节，不改断言。
- 下轮待真机回填缺失项真名与 Done 状态；若缺失项稳定复现，按日志定位该单测 OHOS 行为后再补根因。
- 申请人：waylong，队伍：龙骑士。
