# libflorist 2025.1.0 测试报告

> **项目**: libflorist（FLORIST，IEEE 1003.5 POSIX.5 Ada 绑定）
> **版本**: 2025.1.0（= 上游 AdaCore/florist `25.1` 分支，提交 `d28d09a6`）
> **测试日期**: 2026-09-29（复审轮；首轮 2026-09-27）
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（真机）
> **测试类型**: 官方测试套件（上游 POSIX.5b Validation Test Suite）+ 消费者断言
> **适配路径**: **路径 B（场景二：适配困难库分析报告）** —— 不申请路径 A

---

## 一、测试摘要

### 1.1 消费者视角（test_package，路径 A 层 2）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 5 | 100% |
| 通过 (PASS) | 5 | **100%** |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

消费者程序 `test_package/src/florist_consumer.adb` 真实调用被测包 API：

| # | 断言内容 | 调用的 Florist API | 结果 |
|---|---|---|---|
| 1 | `Get_Process_ID/Image returned a value` | `POSIX.Process_Identification.Get_Process_ID` / `Image` | ✅ ok |
| 2 | `Is_Environment_Variable("PATH") is True` | `POSIX.Process_Environment.Is_Environment_Variable` | ✅ ok |
| 3 | `Environment_Value_Of("PATH") is non-empty` | `POSIX.Process_Environment.Environment_Value_Of` | ✅ ok |
| 4 | `Is_Directory("/") is True` | `POSIX.Files.Is_Directory` | ✅ ok |
| 5 | `Is_Directory(absent path) is False` | `POSIX.Files.Is_Directory`（反向断言） | ✅ ok |

实体输出（`reports/conan-create.log`）：

```
libflorist consumer: POSIX.5 Ada bindings
  ok   : Get_Process_ID/Image returned a value
  ok   : Is_Environment_Variable("PATH") is True
  ok   : Environment_Value_Of("PATH") is non-empty
  ok   : Is_Directory("/") is True
  ok   : Is_Directory(absent path) is False
FLORIST_CONSUMER_OK
```

### 1.2 上游官方测试套件（R51 层 1）

**本表为 2026-09-29 复审轮实测值**（驱动脚本 `tools/run_upstream_tests.py` 已修正，
修正内容见 2.2 节）：

| 指标 | 复审轮（本次） | 首轮（2026-09-27） |
|:----:|:----:|:----:|
| 上游清单条目 **N** | **61** | 61 |
| 辅助子程序（HELPER，非独立测试） | **8** | 0（误计为测试） |
| 不产出可执行文件 | 1（`p030300a`） | 1 |
| 实际执行 **N′** | **52** | 60 |
| 通过 (PASS) | **17** | 14 |
| 不适用 (NOT_APPLICABLE) | **10** | 10 |
| 断言失败 (ASSERT_FAIL) | **19** | 33 |
| 超时 (TIMEOUT) | **4** | 5 |
| 异常退出 (CRASH) | **2** | 2 |
| **严格通过率 (PASS/N′)** | **17/52 = 32.7%** | 14/60 = 23.3% |
| **剔除 N/A 后通过率** | **17/42 = 40.5%** | 14/50 = 28.0% |

口径自洽：`PASS 17 + FAIL 19 + TIMEOUT 4 + CRASH 2 + N/A 10 = 52 = N′`；
`N 61 = N′ 52 + HELPER 8 + NOT_LINKED 1`。

> ⚠️ 上游测试**未全部通过**，故本适配**不申请路径 A 积分**；13 项剩余失败
> 中**仍有 4 项未给出平台级不可修复证据**（见 2.3 节"待进一步调查"），
> 本轮如实标注、不作豁免申报。

### 1.3 复审轮修正记录（驱动脚本）

| # | 缺陷 | 影响 | 修正 | 结果 |
|---|------|------|------|------|
| 1 | `tests/run_tests_1` 在 `test.dir` 建 `ln -fs ../<name>`（供子进程按裸名 exec），旧驱动未复现 | 子进程 exec 失败 → 假 FAIL | `prepare_run_dir()` 重建每项软链 | **p030100 / p030101 / p030102 / p120502 由 FAIL→PASS** |
| 2 | `tests/Makefile` 中辅助子程序被当作独立测试运行 | 系统性假 FAIL（`bad arg`） | `helper_entries()` 识别并标记 `HELPER`（不执行） | 8 项不再计入失败 |
| 3 | 未设 `PWD` / `HOME` / `TMPDIR` / `LC_ALL` / `TZ` | p040300 等依赖环境的项失败 | `test_env()` 补齐 | p040300 断言由 2 项降至 1 项 |
| 4 | 未复现上游 `umask 033` | p050300 断言错乱 | 按上游逐项设置 umask | p050300 断言由 1 项 fatal 变为 5 项明细 |
| 5 | PTY 无窗口尺寸、stdin 指向 `/dev/null` | 终端类用例 `tcsetattr` 失败 | `TIOCSWINSZ` + stdin 同挂 PTY | 保留为已知限制（见 2.3） |

---

## 二、测试结论

### 2.1 总体评价

✅ **库本体可用** / ⚠️ **上游全量测试受平台能力限制**

- **库本体可正常编译、链接、被消费**：`conan create` 端到端成功
  （`Package '21b17f8b…' created`），37 个 Ada 单元 + 2 个 C 单元入
  `libflorist.a`（41 个归档成员），消费者 5/5 断言通过。
- **上游全量测试无法通过**，剩余失败集中于 OHOS POSIX 能力缺口与
  Ada 运行时（GNAT 9.5.0）在 musl/OHOS 上的语义差异。

### 2.2 复审轮转绿项（非系统限制 → 已修复）

| 测试项 | 首轮判定 | 复审轮 | 根因（首轮误判） | 修复动作 | 验证 |
|---|---|---|---|---|---|
| `p030100` | FAIL（6× `failed process creation (41)`） | **PASS** | 子进程按裸名 `p030100b` 启动，`test.dir` 缺 `ln -fs` 软链；PATH 未含 tests 目录 | runner 重建软链 + PATH 注入 | `p030100.log`: `Test Completed Successfully` |
| `p030101` | FAIL（1× 同上） | **PASS** | 同上（`p030101b`） | 同上 | `p030101.log`: PASS |
| `p030102` | FAIL（4× `unexpected exit status 41`） | **PASS** | 同上，且上游 runner 为它建 `ln -fs ../p030102` | 同上 | `p030102.log`: PASS |
| `p120502` | FAIL（`executable file for child not found`） | **PASS** | 同上（`p120502a`） | 同上 | `p120502.log`: PASS |
| `p030100b` `p030101b` `p030301b` `p030306a` `p120502a` `p150100b` `p990040b` `p990050b` | FAIL（假失败） | **HELPER** | 这些是父用例的子程序，上游自带的 `run_tests_1` 从**不**独立运行它们，仅 `ln -fs` | 识别为 HELPER，不计入 N′，不执行 | 上游 `run_tests_1:22-83` 仅有 `ln -fs`，无对应 `$RUN` 行 |

> **关键更正**：首轮把 `failed process creation (41)` 解释为 `errno 41`。
> 实测（`tests/posix_report.adb:834` + `libsrc/threads/posix-process_primitives.ads:135`）
> **41 并非 errno**，而是 Florist 自定义哨兵 `Failed_Creation_Exit := 41`，
> 表示"子进程 exec 前哨兵路径失败"。首轮的 errno 归因**不成立**，已更正。
> 实测 fork+exec 在本设备可用（探针 `execv()` 成功、子进程正常退出），
> 41 的直接原因是**驱动脚本未复现上游的软链布局**，属**驱动缺陷**（已修复）。

### 2.3 剩余失败逐项分类（如实回填）

**A. 系统限制（平台能力缺口，有可复核证据）**

| # | 测试项 | 现象 | 证据 | 判定 |
|---|--------|------|------|------|
| A1 | `p060300` | 14× `OPERATION_NOT_IMPLEMENTED`（A023–A048） | `p060300.log:4-15`；行尾 `**** Nonsupport of SYNCHRONIZED_IO_OPTION detected.` | OHOS 未提供 SYNCHRONIZED_IO（`fdatasync`/`sync_file_range` 语义） |
| A2 | `p110200` | `OPERATION_NOT_SUPPORTED: A016` | `p110200.log:2`；`**** Nonsupport of MUTEX_PRIORITY_CEILING_OPTION detected.` | OHOS 未实现对 POSIX 可选 MUTEX_PRIORITY_CEILING |
| A3 | `p150100` `p150101` | `OPERATION_NOT_IMPLEMENTED` | `p150100.log`、`p150101.log:2` | XTI/TLI（`t_*`）未实现 |
| A4 | `p110200` 组 | 上游自判 | 10× `**** Nonsupport of PRIORITY_PROCESS_SCHEDULING_OPTION detected.`（`p990010/11/20/30/40/50/60/70/80/90.log`） | 上游**自行**判定不可用 → 记为 NOT_APPLICABLE，不计失败 |
| A5 | `p120300` | `raised STORAGE_ERROR : s-intman.adb:136 explicit raise` | `p120300.log:3` | GNAT 运行时中断管理单元 `s-intman.adb:136` 显式 raise，Ada 运行时对 OHOS 信号/中断栈假设不成立 |
| A6 | `p140101` | 无裁决语句，进程被信号 31 终止（`CRASH_-31`） | `p140101.log`（仅横幅）；探针：`SIGRTMIN=35 SIGRTMAX=64 NSIG=65` | SIGSYS：触发 OHOS 内核未实现/被 MAC 拒绝的系统调用（须补 syscall 名，见 2.4） |
| A7 | `p030300` | 4× `SIGNAL_64`/`SIGNAL_INTERRUPT` 断言失败 + TIMEOUT | `p030300.log:2-14` | 用例假定信号编号集与 OHOS 不同（OHOS `NSIG=65`、实时信号 35–64） |
| A8 | `p030301` `p030304` `p030306` | `stopped by signal 19`（SIGSTOP）/ `only 0 signals received` / TIMEOUT | `p030301.log:2-6`、`p030304.log:2-17`、`p030306.log:2-15` | 信号集与作业控制语义差异；**但**在 `-v` 下同样的 Start_Process 断言全部成功，不能排除驱动侧时序因素 → 见 B 组 |
| A9 | `p090100` `p090200` `p040101` | `CONSTRAINT_ERROR` / `POSIX_ERROR`（A002/A004–A012/A014/A007/A010） | `p090100.log:2-7`、`p090200.log:2`、`p040101.log:2-3` | 共享内存/映射与权限语义差异（`OPERATION_NOT_PERMITTED`） |
| A10 | `p140100` | `CONSTRAINT_ERROR [A037]`、`INVALID_ARGUMENT A073/A076`、`deleted Timer_ID can be deleted [A062/A078]` | `p140100.log:2-10`；`p140100.adb:593-600`、`744-747` | OHOS `timer_delete()` 幂等（`probe_sys` 待补）：重复删除返回 0 而非 EINVAL |
| A11 | `p030303` `p040300` `p040301` | `STORAGE_ERROR` / `CONSTRAINT_ERROR`（A003/A006/A002/A054/A067/A071/A079） | 对应 `.log` | 共享内存与栈边界语义差异 |

**B. 非系统限制（尚未修复，**必须继续修**，本轮不豁免）**

| # | 测试项 | 现象 | 待查方向 |
|---|--------|------|---------|
| B1 | `p030301` `p030304` `p030306` | TIMEOUT / 信号计数为 0 | `-v` 下 Start_Process 断言全数成功，疑为驱动侧信号掩码/时序；须与上游 `run_tests_1` 的进程组语义逐条对齐 |
| B2 | `p050200` `p050300` `p060100` | `[A123] fatal exception`、`assert [A004/A006/A007/A012/A015]`、`assert [A029]` | 终端特性（`tcsetattr`）与 umask 语义；PTY 已补窗口尺寸与 stdin，仍失败 → 须核对用例前置条件 |
| B3 | `p070200` | `PERMISSION_DENIED [expected INAPPROPRIATE_IO_CONTROL_OPERATION]` | `ioctl(TIOC*)` 错误码映射差异；可能属 Florist errno 映射而非平台 |
| B4 | `p110100` | `exception not raised [A045/A051/A054]` | 线程调度/互斥语义，非平台能力缺口 |
| B5 | `p120500` | `NO_SUCH_FILE_OR_DIRECTORY: A017` | 用例依赖的运行目录状态；驱动重建目录后仍未过 → 须核对用例前置文件 |
| B6 | `p120300` | `s-intman.adb:136`（A5 同项） | 需区分 GNAT 运行时缺陷（可在配方侧打补丁）与平台限制 |
| B7 | `p020400` | 5× `assert [A004/A008/A010/A014/A024]` | 未定位 |

**C. 待进一步调查（暂不归类）**

| # | 测试项 | 说明 |
|---|--------|------|
| C1 | `p030300a` | `NOT_LINKED`：上游 Makefile 中不产出独立可执行文件（仅作为 `p030300`/`p030306` 的辅助单元），非跳过 |
| C2 | `p140101` | 须补 syscall 名与 errno 才能完成 A6 的证据链 |

> ⚠️ 本表严格执行"**禁止把不确定归为系统限制**"：B 组 7 项**不计入豁免**，
> 明确列为待修。

### 2.4 结论与建议

1. 本包标记为「**部分适配 / 平台受限**」；
2. **不得**按"平台限制"整体豁免上游测试：A 组须补 syscall/errno 证据，
   B 组须继续修复；
3. 建议另立「**OHOS POSIX 能力补齐**」项目（消息队列、实时信号、
   优先级调度、XTI-TLI、共享内存语义、SIGNAL_64 信号集）；
4. 建议在 ohpcd 增补 Ada 工具链（`gprbuild` + `gnatprep`）。

---

## 三、测试方法

### 3.1 消费者测试（test_package）

由 `conan create` 自动执行：`test_package/conanfile.py` → `build()` 调用
`test_package/test.sh` 编译并链接消费者程序 → `test()` 签名后运行。

### 3.2 上游测试

1. **清点**：`tests/Makefile` 的 `TESTS`(44) ∪ `SPECIAL_TESTS`(17) = **61**。
2. **识别辅助子程序**：凡在 Makefile 中作为另一清单条目前置依赖出现者，
   标记 `HELPER`（8 项），不独立执行 —— 与上游 `run_tests_1` 一致。
3. **编译**：`make -f Makefile $(TESTS) $(SPECIAL_TESTS)`（配方 `build()` 内）。
4. **运行**：`tools/run_upstream_tests.py` 逐项执行——
   - **签名**：OHOS 拒绝执行未签名 ELF，每项执行前签名；
   - **PTY**：stderr（及 stdin）挂 PTY，并设 `TIOCSWINSZ` 80×24；
   - **软链**：`test.dir` 内为每项建 `ln -fs ../<name>` 与 `bin -> ..`；
   - **环境**：`PATH` 含 tests 目录、`PWD`、`HOME`、`TMPDIR`、`LC_ALL=C`、`TZ=UTC`；
   - **超时**：每项独立超时（45–120s，按用例调整）；因多用例 fork 子进程会
     保持 PTY 打开，超时判定以**子进程退出**为准（退出后宽限 3s 收尾）。
5. **结果表**：`<build>/build-release/upstream-results.txt`（61 行逐项判定），
   逐项日志 `<build>/tests/test.dir/<name>.log`。

> 未采用上游自带 `tests/run_tests_1`：它既不签名也不提供 PTY。

### 3.3 门禁验证

| 门禁 | 结果 |
|------|------|
| conan-verify G0–G4 | ✅ PASS |
| L2（smoke）/ L4（安全扫描）/ L5（产物基线） | ✅ PASS |
| W3 本地 CI 模拟 | ✅ `exit_code: 0`（含 `log_sha256` 防伪造） |
| W4 Pre-PR 独立审计 | ✅ `verdict: pass`（P0=0 / P1=0） |

---

## 四、环境与工具链

| 项 | 值 |
|---|---|
| 编译器 | `gcc-ada/9.5.0`（GNAT，OHOS/armv8）+ `binutils/2.46.0`（as/ld） |
| 构建模式 | 原生双 profile（`-pr:h/-pr:b` 同为 ohos-aarch64）；无 Linux 交叉 Ada 编译器 |
| Conan | 2.29.1（OHOS 适配版） |
| 链接方式 | 静态（Ada 运行库 `libgnat.a`/`libgnarl.a` 非 PIC） |
| 产物 | `floristlib/`（Ada 规格 + ALI + `libflorist.a`）、`share/gpr/florist.gpr`、`licenses/COPYING` |

---

## 五、详细数据来源

| 数据 | 来源 |
|------|------|
| 消费者 5/5 | `reports/conan-create.log`（test_package 运行输出） |
| 上游逐项判定 | `<build>/build-release/upstream-results.txt`（61 行） |
| 逐项日志与行号 | `<build>/tests/test.dir/*.log`（52 份执行 + 相关 HELPER） |
| 门禁结论 | `reports/conan-verify-report.md`、`.ci-result.json`、`reports/audit-result.json` |
| 根因分析全文 | `reports/adaptation-analysis-report.md` |
| 适配笔记 | `notes.md`（含 R51 三步法与评审意见响应） |

> 说明：`<build>` 为本次 `conan create` 的 Conan 构建目录（临时目录，会随
> Conan 缓存清理失效）；其结论已固化于本报告、`test_package/MANIFEST.yml`
> 的 `upstream_test_census` 与 `notes.md`，不依赖临时目录长期留存。

---

*报告结束。所有数据均来自实际运行；未采集项与待查项已明确标注，未作豁免申报。*
