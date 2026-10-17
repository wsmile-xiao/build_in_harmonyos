# ninja 1.13.2 知识候选台账（Knowledge Candidate Ledger）

> 生成时间: 2026-09-22　生成环境: pc3-15 (OHOS PC, aarch64, clang 15)
> 查重范围（四范围）: `knowledge/graph/index.tsv`（540 正式条目）· `knowledge/doc/` · `knowledge/graph/E*.kv` · `knowledge/drafts/`（897 草稿）
> 查重方法: 对每个非噪声候选记录真实错误、根因、修复、验证、适用范围，并按七轴与关系字段完成正式知识/图谱/草稿三处比对（index/doc/kv/drafts 四范围）
> 路径决定依据: knowledge-reuse-governance —— 完整重复→复用走路径 A；候选已验证、可跨库复用且查重未命中或部分覆盖并有新增差异→路径 B 建立同 stem 草稿

## 候选总览与路径决定

| 候选 | 标题 | 查重结果 | 既有条目覆盖 | 新增差异 | 路径决定 | 草稿 |
|---|---|---|---|---|---|---|
| C1 (E430) | OHOS 内核 ppoll() 运行时 ENOMEM：需强制 pselect 路径 | **全库未命中**（index/doc/kv 0 命中） | 无 | 全新 | **B / new_draft** | knowledge/drafts/E430-draft-B8F9.{kv,md} |
| C2 (E431) | OHOS HMDFS 不支持 mknod/FIFO：FIFO 类测试平台阻塞 | **部分覆盖** | E074（make jobserver FIFO/SELinux）、E292（error_signature 含 jobserver mkfifo） | mknod EPERM 为 HMDFS 文件系统语义（非仅 SELinux）；覆盖 /dev/shm EACCES、/tmp erofs 全候选验证；适用范围从 make 扩至 ninja/任意 mknod FIFO | **B / new_draft** | knowledge/drafts/E431-draft-E86D.{kv,md} |
| C3 (E432) | 上游测试文件未被任何目标接入且缺 include：最小补丁纳入 | **未命中**（E269=Python2 runner、E301=ctest helper、E302=memstream 均不同） | 无 | 全新（测试纳入关系恢复模式） | **B / new_draft** | knowledge/drafts/E432-draft-16F2.{kv,md} |
| C4 (E433) | 上游 find_package(GTest) 大写 vs CMakeDeps 小写 gtest：GTest_DIR 指向包内配置 | **部分覆盖** | E216（CMakeDeps 组件头文件传播）、E221（CMakeDeps target libs 空） | 目标名大小写差异 + GTest_DIR 注入方案；conan create 实测日志验证 | **B / new_draft** | knowledge/drafts/E433-draft-2C1D.{kv,md} |

## 逐项七轴查重与关系

### C1 — E430 ppoll ENOMEM → NINJA_FORCE_PSELECT=ON
- **exact_duplicate**: false（全库 ppoll/pselect 0 命中）
- **causal_duplicate**: false（无既有条目同根因）
- **trigger_overlap**: 低（E055 posix_spawn subprocess compat 是 fork/spawn 语义，非 poll 系统调用）
- **solution_overlap**: 低（E074/E076 是 FIFO/fstat syscall 域，非 poll 域）
- **combination_novelty**: true —— "OHOS 内核 poll 族系统调用运行时失败 → 构建工具强制 pselect 开关" 为组合新知识
- **boundary_novelty**: true —— 适用范围=使用 ppoll() 的 C/C++ 构建工具/守护进程（OHOS aarch64）；反例=纯 Linux 环境 ppoll 正常
- **test_migration_novelty**: false（不涉及测试迁移）
- **关系**: similar_to=E055(子进程系统调用 compat)；caused_by=OHOS 内核 ppoll 实现；prerequisite_of=ninja 上游测试子进程套件可运行；conflicts_with=无
- **验证证据**: 未强制 pselect 时 `./ninja_test` 刷 "ninja: ppoll: Out of memory" 无限循环（run1 日志）；`-DNINJA_FORCE_PSELECT=ON` 后 411 用例 1.4s 跑完（ninja_test_run4.log）

### C2 — E431 HMDFS 不支持 mknod/FIFO（平台阻塞）
- **exact_duplicate**: false
- **causal_duplicate**: false（E074 根因写 SELinux 策略禁 FIFO；本轮实测 EPERM 来自 HMDFS 文件系统 mknod 语义，且 /dev/shm 为 EACCES、/tmp 为只读 erofs——根因面更广）
- **trigger_overlap**: **true**（E074 的 `FIFO.*Permission denied|jobserver.*fifo` 正则可命中 ninja Jobserver.PosixFifoClient；E292 error_signature 含 jobserver mkfifo）
- **solution_overlap**: **true**（E074 rec_approach=env-var-override 单线程绕过 jobserver；对本轮无解，记录为平台阻塞+恢复条件）
- **combination_novelty**: true —— 全候选挂载点验证流程（HMDFS EPERM + /dev/shm EACCES + /tmp erofs）与"设备上不存在任何可写且支持 POSIX FIFO 的挂载点"结论
- **boundary_novelty**: true —— 适用范围从 make jobserver 扩至 ninja/任意 mknod FIFO 测试；反例=提供 ext4/tmpfs 可写挂载点后 FIFO 可建
- **test_migration_novelty**: false
- **关系**: similar_to=E074、E292；caused_by=HMDFS 文件系统 mknod 语义 + 平台挂载限制；conflicts_with=无
- **验证证据**: `os.mkfifo` 全候选挂载点逐一失败（/storage/* EPERM、/dev/shm EACCES、/tmp erofs），见台账 3.1 与 ledger 五、四节

### C3 — E432 上游测试文件未接线 + 缺 include（最小补丁恢复）
- **exact_duplicate**: false
- **causal_duplicate**: false（E269/E301/E302 均为不同测试执行面问题）
- **trigger_overlap**: 低
- **solution_overlap**: 低
- **combination_novelty**: true —— "枚举到但未被 CMake/configure.py 任何目标接线的独立测试文件 + 文件自身缺 include 无法编译 → 最小补丁纳入目标并补 include" 完整闭环
- **boundary_novelty**: true —— 适用范围=上游仓库存在但未接线测试文件的 C/C++ 项目；反例=上游有显式排除条件（WIN32-only 的 includes_normalize_test/msvc_helper_test 保持未实例化）
- **test_migration_novelty**: true —— 双口径台账中"未实例化→最小补丁纳入→注册数 409→411"的可复现迁移路径
- **关系**: similar_to=E269/E301/E302（测试执行面条目族）；caused_by=上游遗漏接线；prerequisite_of=双口径台账可执行口径准确；conflicts_with=无
- **验证证据**: status_test.cc 未接线时 409 注册；最小补丁（CMakeLists 目标+补 include）后 411 注册、StatusTest 2 用例通过（ninja_test_run4.log）

### C4 — E433 find_package(GTest) 大写 vs CMakeDeps 小写
- **exact_duplicate**: false
- **causal_duplicate**: false（E216=组件 INTERFACE_INCLUDE_DIRECTORIES 传播；E221=target libs 空——均非目标名大小写）
- **trigger_overlap**: **true**（同属 CMakeDeps/Conan CMake 配置域）
- **solution_overlap**: **true**（均涉及以配置注入修复 CMake 目标解析）
- **combination_novelty**: true —— "上游 find_package(GTest) 大写目标 GTest::gtest vs CMakeDeps 生成小写 gtest → GTest_DIR 指向依赖包自带 GTestConfig.cmake" 具体方案
- **boundary_novelty**: true —— 适用范围=上游用 find_package(GTest) 大小写目标的 Conan 项目；反例=上游 find_package(gtest) 小写时无需注入
- **test_migration_novelty**: false
- **关系**: similar_to=E216、E221；caused_by=CMakeDeps 配置名与上游 find_package 名大小写不一致；conflicts_with=无
- **验证证据**: 注入 GTest_DIR 前 conan create CMake configure 报 `GTest::gtest ... target was not found`；注入后 configure/build/package 全通过（conan-create.log）

## 结论
- **reuse_existing**: 0（无完整重复候选）
- **new_draft**: 4（E430/E431/E432/E433，均经本轮真实日志验证、可跨库复用、查重未命中或部分覆盖且存在新增差异）→ **路径 B**
- **path_a_no_knowledge**: false
- 说明: 本任务 task_type 为【高难度挑战】，即使 new_draft 且 .md/.kv 配对通过，PR 前缀仍保留【高难度挑战】（任务规则 7）；草稿与三方库归档进入同一 PR（路径 B 规则）。

---

## R02 复核（2026-09-22，task ninja-1.13.2-r02）

R02 返工后重新复核候选台账与七轴查重：**无新增候选**，R01 判定的 new_draft ×4（E430/E431/E432/E433）全部保留，并补充 R02 新证据：

| 候选 | R02 补充证据 | 判定维持 |
|---|---|---|
| E430 ppoll/pselect | R02 确认 ninja 子进程 shell 硬编码 `/bin/sh -c`（subprocess-posix.cc:132，无 $SHELL/NINJA_SHELL 覆盖），pselect 强制开关是唯一不改变库行为的规避路径 | new_draft 维持 |
| E431 HMDFS FIFO | R02 新增候选挂载点扫描（/mnt/hmdfs/100、/data/storage/el2、sharefs、fuse、cloud）全部 mkfifo 失败；唯一可写 HMDFS 目录 stat 模式 0o2771 非真实 0700 且 chmod 被忽略——平台阻塞证据更完整 | new_draft 维持 |
| E432 status_test 纳入 | R02 复核 22 个未实例化项均存在明确上游排除条件（WIN32 守卫 12 + WIN32-only 文件 9 + USE_PPOLL 1），status_test 是唯一无排除条件者——验证恢复规则应用边界 | new_draft 维持 |
| E433 GTest_DIR 大小写 | R02 复验 conan create 仍通过（配方未改），GTest_DIR 注入方案稳定 | new_draft 维持 |

- **reuse_existing**: 0；**new_draft**: 4（E430/E431/E432/E433）；**path_a_no_knowledge**: false —— 维持路径 B。
- R02 新增观察（不构成新候选，仅边界反例补充）：toybox `id` 无法解析 uid 20020101（`id: bad uid`）属该设备工具链行为，已在 E431 平台工具类范畴内记录；不单独建条目。

---

## R03 复核（2026-09-23，task ninja-1.13.2-r03）

R03 返工后重新复核候选台账、七轴查重与 .md/.kv 配对：

| 候选 | R03 复核结论 | 判定维持 |
|---|---|---|
| E430 ppoll/pselect | R03 独立复跑确认强制 pselect 后 411 用例 1.4s 跑完（ninja_test_run_r03.log）；无新候选合并 | new_draft 维持 |
| E431 HMDFS FIFO | R03 独立全候选挂载点 mkfifo 复测（含 /storage/userExternal、/storage/External、/mnt/hmdfs/100/non_account、/sys/fs/cgroup）仍全部 FAIL；chmod 700 后 stat 0o2771 非真实 0700 证据重申 | new_draft 维持 |
| E432 status_test 纳入 | R03 复核 22 个未实例化项维持明确上游排除条件判定（WIN32 守卫 12 + WIN32-only 文件 9 + USE_PPOLL 1），无无排除条件项漏网 | new_draft 维持 |
| E433 GTest_DIR 大小写 | R03 复验 conan 包内 ninja --version=1.13.2 正常、配方未改，方案稳定 | new_draft 维持 |

- **.md/.kv 配对补全（R03）**：4 份草稿 .md 此前为模板占位（453 字节），本轮补全真实内容
  （错误特征/触发条件/根因/方案/禁止做法/验证/适用边界/查重差异/关系字段），
  与 .kv 关键字段（error_signature/root_cause/rec_approach）逐项核对非空；W5 完整性满足。
- **reuse_existing**: 0；**new_draft**: 4（E430/E431/E432/E433）；**path_a_no_knowledge**: false —— 维持路径 B。
- R03 无新增候选（平台条件复验产生的均为既有候选的补充证据，不构成独立知识模式），不预造条目。

---

## R04 复核（2026-09-23，task ninja-1.13.2-r04）

### 新增候选：C5 (E434) — OHOS /bin/sh 缺 POSIX 信号语义：编译期子进程 shell 覆盖

本轮实施 subprocess shell 适配补丁（`NINJA_SUBPROCESS_SHELL` 编译期宏）并实测通过
`SubprocessTest.InterruptChildWithSigHup`（130==ExitInterrupted），形成可跨库复用的新知识模式，
按 knowledge-reuse-governance 完成查重后新建草稿。

| 七轴 | E434 判定 | 说明 |
|---|---|---|
| exact_duplicate | false | index/doc/kv/drafts 四范围均无 SIGHUP-WIFSIGNALED 错误模式条目 |
| causal_duplicate | false | E051=SIGSYS 未实现 syscall 信号；E043=toybox ash bashism/BASH_SOURCE，根因均不同 |
| trigger_overlap | 低 | E043/E051 同属 OHOS shell/信号域，但错误面不同（非信号死亡 vs 非法 syscall 信号） |
| solution_overlap | 低 | E043=source-patch bashism 修正；E051=source-patch syscall 规避；均非编译期子进程 shell 覆盖 |
| combination_novelty | true | "OHOS /bin/sh SIGHUP 信号语义缺失 + 编译期子进程 shell 覆盖（默认 /bin/sh 保持平台中立）" 为组合新知识 |
| boundary_novelty | true | 适用=依赖子进程 WIFSIGNALED 中断检测的构建工具；反例=纯 Linux /bin/sh 语义正常无需覆盖 |
| test_migration_novelty | true | 407/411 → 408/411（InterruptChildWithSigHup 由补丁恢复）的可复现迁移路径 |

- **关系字段**: similar_to=E043、E051；caused_by=E043（toybox 系 shell 行为差异）；conflicts_with=无；prerequisite_of=ninja 上游测试套件在 OHOS 全量通过
- **验证证据**: 补丁后 `./ninja_test --gtest_filter=SubprocessTest.InterruptChildWithSigHup` PASSED；
  全量 411 ran / 408 passed / 3 failed（ninja_test_run_r04.log）；C probe 对照 /bin/sh WIFEXITED vs bash WIFSIGNALED(SIGHUP=1)
- **草稿**: knowledge/drafts/E434-draft-4F2C.{kv,md}（.kv/.md 配对，关键字段非空）

### R04 结论
- 既有 new_draft x4（E430/E431/E432/E433）维持；新增 **E434** → **new_draft x5**，路径 B 维持。
- **reuse_existing**: 0；**new_draft**: 5（E430/E431/E432/E433/E434）；**path_a_no_knowledge**: false。
- 无预造条目：E434 全部结论来自本轮真实补丁、编译与测试日志。

---

## R06 复核（2026-09-25，task ninja-1.13.2-r06-pc3-15-20260924T214107Z）

### 本轮知识动作：补丁格式修复不产生新知识候选
- 本轮修复为 0003/0004 补丁 hunk 头格式（行数/偏移声明错误 → 按序应用失败）与配方传参方式
  （NINJA_FORCE_PSELECT / NINJA_SUBPROCESS_SHELL 改为 configure 命令行变量），均属既有知识
  E434（OHOS 子进程 shell 覆盖）的实施修复，非新的错误模式。
- 七轴查重（本轮候选）：exact_duplicate=false；causal_duplicate=false；trigger_overlap=低（同属补丁/配方实施域）；
  solution_overlap=高（E434 同一方案的格式修复）；combination_novelty=false（无新组合）；boundary_novelty=false；
  test_migration_novelty=false（测试数字未新增通过项）。
- 决定：**reuse_existing=0；new_draft=0（本轮无新候选）；维持既有 new_draft x5（E430/E431/E432/E433/E434）→ path B 维持。**
- 验证证据：R06 全新 conan create EXIT=0（conan-create-r06.log SHA-256 92cb49bc...）；
  InterruptChildWithSigHup PASSED（adaptation-validation-r06.log）；全量 411 ran / 408 passed / 3 failed（ninja_test_run_r06.log）。
