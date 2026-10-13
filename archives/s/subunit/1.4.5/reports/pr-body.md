## PR 信息

- **三方库名称**：subunit（C binding / libsubunit）
- **上游版本**：1.4.5
- **上游仓库地址**：https://github.com/testing-cabal/subunit
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战候选）
- **使用知识库**：DRAFT-E571、E547；E2026100501 草稿，知识补充至 [PR 9499](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9499)，不重复申报 TEMP 机理。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 541 | 原 C/Check 六个注册 ID，加原 Python/Shell check-local 实际535个独立运行 ID；下面分别给出两套原始证据 |
| 集成测试 | 0 | 原 Python/Shell 的协议子案例已逐 ID 计入上行，不重复累计外层包装器 |
| 其他测试 | 0 | test_progress 内四个操作不拆成四例；不计宿主合成控制或重复执行 |
| **合计** | **541** | C 6 + Python/Shell 535；完整产品原上游覆盖清单，不是声称同一次 W3 运行541项 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 541 | 不变 | C 6/6 与 Python/Shell 535/535 均真实执行、零失败/零跳过；两套独立入口与事务分别核验 |
| 集成测试 | 1 | +1 | 安装包公开 API 的完整 test:/success: 流，精确长度/字节比较与描述符回收 |
| 鸿蒙特有测试 | 1 | 新增 | 原生 __OHOS__/aarch64 守卫，任务私有签名库动态载入，HMDFS 中文协议独占写读、投影属主校验与清理 |
| **合计** | **543** | **+2** | 原上游541项、消费者1项、专项1项；保留各自入口、事务及原始分母，不累计重复运行 |

test_skip 是执行成功的 skip 协议 API 用例，不是框架跳过。框架原始 XML 六个 ID 全部成功，注册与实际运行集合精确相等。配方仍只包装 C binding，但本 PR 的原上游测试统计涵盖已真实完成的 Python/Shell 535项，不能以包作用域缩小正文测试分母。两个组件分别具有完整独立终态，541是非重复覆盖总数，不追认任何单个 W3 事务的测试结果。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

原 c/tests/test_child.c、c/lib/child.c、c/include/subunit/child.h 与 Check 二进制字节不改。配方构建原 test_child 入口；包装器仅设置任务私有 TEMP/TMPDIR/TMPPREFIX、清除继承 CK_* 选择/fork 覆盖并设置本次 XML 路径，不削减测试、不关闭 fork、不弱化断言。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/main.c 消费者和 harmony_tests/hmdfs_loader.c 专项，均调用真实包 API。原 void API 冒烟只调用不比较输出、错误声称 ok: 的问题已修复为真实 success: 字节核对；新增两例不替代原六例。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：541/541（100%）
- 新增测试用例通过率：2/2（100%）

- 原生 r005：subunit-20261005-r005，源码归档105136 bytes，SHA-256 c55b39d0802ca15c18fbf267faf3a1cf67b4fe2482abbb00755c31b53c833bf7。
- config SHA-256 8be88593ee9cac284a1ee9831a2968d35b3497a90fcab060fd7f986eb722b7e4；终态 snapshot SHA-256 b85db511fe27e80bd19cbb2f3efc7de18ec52d5c5c4ca1b15fc6ff003f47be59。完整 WAL/receipt、唯一launch=1、AFTER、release/postrelease PASS，自有进程0。
- Check 0.15.2 已真实通过 OHOS/armv8 --build=never：RREV6d41c3078e77093b6b9dfe97b95e0f9c / PID21b17f8b2bc0e9511e276e3d57a23893067cefe5 / PREV30d62eb1e36c4d31e934b687d33d3943。无产品依赖，测试依赖不私有重建。
- reports/r005-* 保留原始日志、注册清单、XML、结果和输入哈希；旧 r001 真失败、r002/r003/r004 先前输入验证独立保留，不拼接为 r005。
- 宿主合成正/负控制2/2，验证环境隔离及空套件 RC0 拒绝，只作为包装器定向诊断，不计入上面产品测试分母。
- formal-r001 是真实失败：HarmonyOS CMake 输出 libsubunit.so，签名却查找版本名。formal-r002 因 SONAME .so.0 与实际 .so 名不符、缺运行搜索路径而加载失败；formal-r003 原六例通过，但 test_package 仅判断 OHOS，实际 CMake 平台 HarmonyOS 未生成专项目标。当前修复实际产物定位、SONAME、上游构建入口 $ORIGIN RPATH，以及 OHOS/HarmonyOS CMake 条件；不混淆 Conan os=OHOS 与 CMake 平台名。
- formal-r004 的真实 conan create、原六例、消费者及专项通过，本地 CI 的 KC/JC/L0/L1/L4/L5 通过；原日志 ci-build.log SHA-256 a6cade02708499b65db6964462fcac126b05498f9721e41089340f66d84f3d39。终态 snapshot-002.json SHA-256 c2035a733ef2f88e84f6f981365709a38bdd514f7cfe56604d0c464ac0ff6f3b。后续仅修正文档、配方说明字符串及 MANIFEST 的三个 evidence 字段；实际构建表达式、测试命令和产品输入未改变，原运行保留原哈希，不追认新运行。
- 整体 finish RC1、PARTIAL_POST_W3：step5b/step7/step8 仍报告稀疏目录比较、旧知识字段及手工包标记问题。保留真实失败，不创建假标记、不修改 .ci-result.json、不将本地 CI 或 Conan PASS 冒充平台 CI PASS。
- 旧 HEAD 平台 CI #66541 仅历史结果；当前修复提交的 CI/Review 已申请，必须取得本轮完整 HEAD 的真实终态，不提前提审。
- AtomCode 原始静态检视已公开于评论 192510748。TMPPREFIX 与 static 分支两项误报以官方 Check 实现和实际条件分支说明；构建包装描述、success: 协议文本及 r005 证据字段的真实文档问题已修正。该静态检视不冒充平台 CI 或真机执行。

---

### 人工评审补充：原 Python 与 Shell check-local 已真实执行

对应 gcw 原 Python/iso8601/testtools 覆盖意见（192450456）与主表漏计意见（193180121），本次将完整覆盖同步到两张主表和验证结果。测试时完整 HEAD `e48a5a5ea8aa9596a98d423a14539e3ea3713c72` 的官方源码，原 `all_tests.test_suite` 已在 HarmonyOS PC/aarch64、Python 3.12.9 真实执行：**535/535 success，failure/error/skip/xfail/xpass 均为 0**。后续本次仅修正报告统计，不改变产品、测试或运行闭包。

- 实际事务 `subunit-python-original-20261010-r010`，唯一 launch=1，真实命令 RC0；完整 WAL/receipt 与原 release/postrelease 已核验，自有进程0。
- 原加载清单526项含三个协议执行包装器。运行时这三个包装器产生12个真实子协议案例，因此实际结果为 `526-3+12=535`；不是以加载526或两个 Shell 包装器作为真实运行分母。每个运行 ID 都有且仅有 start→success→stop。
- 保留原 Python 测试、源脚本和全部断言。两份 Shell 脚本通过真实签名 ELF execv 调用任务私有 Bash 5.3，原脚本字节不变；不模拟协议、不改系统解释器或共享环境。
- 原测试引用 `testtools.tests.test_testresult.TestStreamResultContract`。真实 testtools 2.9.1 已将测试移动到顶层 `tests/`，不能编造辅助模块；采用原 pyproject 明确允许的 `testtools>=2.7` 中真实 2.7.0 wheel（含原测试契约），SHA-256 `068a20348482301bcee8ad6366021301469fc1c81ac3c80e8c038d711befa2c6`，配合真实 iso8601 2.1.0、fixtures 4.3.2、testscenarios 0.7.0、hypothesis 6.155.7、sortedcontainers 2.4.0。六输入逐项冻结、任务私有展开，无 shared pip install。
- r008 是真实缺辅助模块 FAIL；r009 原默认入口 RC0/535，但默认 TextTestResult 不显示 skips，未将摘要当零跳过证明。r010 只增加透传结果观察器，沿用原 TestProgram 与 TextTestResult 语义；独立核对所有535个结果后才给出以上零跳过结论。
- 原始结果 stdout SHA-256 `8ec8a20fc3a7954a0a321a27f524c646f4023f1d3423408d70489dece2d7470a`；独立事务核验 JSON SHA-256 `a98b26dc227996e15a20c08e1dbb98b717950a642453dbc24d691c211ba659a9`。逐项核验保存在本任务 `subunit-original-cases-oct10-r010.json`。

覆盖总数541由两个不同原上游组件的完整证据构成：C/Check 6/6（原 r005及formal-r004）和Python/Shell 535/535（原r010）。这是逐ID不重叠的覆盖清单汇总，不将不同事务的阶段或局部结果拼成同一次W3 PASS，不修改原回执或仅包装C binding的产品范围。`reports/original-upstream-coverage-oct11-r689.json`及对应清单保留两组件的实际run、原日志SHA、真实结果与范围边界。修正文档后的当前HEAD仍须获得自己的平台CI成功，旧提交的CI不迁移。

## 补充说明

- 关联 Issue：#3566
- 队伍名称：2301_80739235（个人）
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/subunit-1.4.5
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 知识补充对象仅 [PR 9499](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/9499)；本软件 PR 为13626。四域 main 查重及2244 OPEN PR编号占用已完成；新 E2026100501 同 stem KV/MD，draft:true。
- 高难候选申请见唯一 Issue3566：HD4=true，原535项测试的跨语言依赖闭包、真实私有测试契约兼容与协议运行身份核验已完成；HD1/HD2/HD3=false。申请路径A+B+C候选，不宣称官方高难认定或分值。
- 人工意见已落实到六章完整模板、两表两勾选区、原C全量执行和独立鸿蒙专项；已有 resolve 状态不代表这次修复自动被评审接受。
- 不上传制品、不合并、不 force push，不改共享工具和其它软件工作树。
