- **三方库名称**：reptyr（把正在运行的进程重挂到新终端的工具；基于 ptrace 夺取进程控制终端）
- **上游版本**：0.10.0
- **上游仓库地址**：https://github.com/nelhage/reptyr（官方 tarball 端点 `https://codeload.github.com/nelhage/reptyr/tar.gz/refs/tags/reptyr-0.10.0`，与 `archive/refs/tags` 端点字节一致；sha256 `c6ffbc34a511ac00d072219bda30699e51f2f4eb483cbae9e32e981d49e8b380` 已实测校验）
- **适配路径**：路径 A（基础适配，2 个可移植性补丁）+ 路径 B（贡献创新，见下方「路径 B 知识贡献说明」）
- **使用知识库**：E007（系统识别不认 HarmonyOS，手写 Makefile 变体）、E091（linux/socket.h 与 sys/socket.h 的 sockaddr_storage 重定义）、E188（OHOS 无 GNU install）；本 PR 新增路径 B 草稿 `knowledge/drafts/DRAFT-10103-reptyr-ptrace-capability-boundary`（见下）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试/回归 | 2 | 来源：`test/`（`basic.py`、`tty-steal.py`，pexpect 驱动；`Makefile test` 目标注册） |
| 集成测试 | 0 | 上游未区分集成层 |
| 其他测试 | 0 | `matrix.sh` 为 32/64 位构建矩阵脚本，仍以 make test 为入口，不计独立用例 |
| **合计** | **2** | 上游 0.10.0 共 2 个 E2E 用例 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 上游测试（全量执行） | 2 | 不变（0 通过：OHOS ptrace 平台边界，逐项原因见下） | 真机实际执行，日志 `reports/upstream-basic.log`、`reports/upstream-tty-steal.log` |
| 鸿蒙特有测试（消费者视角） | 18 | **新增** | `test_package/test_reptyr.sh` 真实执行已安装二进制，18/18 通过 |
| **合计** | **20** | **+18** | 覆盖 pty 分配/子进程 stdio/参数校验/错误报告/CLI 合约 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 2 个用例原样在真机执行（未改一行）；失败发生在被测工具调用 `PTRACE_ATTACH` 的
> 首个系统调用处，是 OHOS 内核策略边界（见下），与测试代码无关。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游测试在 OHOS 上无法产生有效覆盖（平台 ptrace 边界），适配后补全了消费者测试（请在下方说明）

> - **上游测试清点证据（R51）**：`test/` 目录含 `basic.py`、`tty-steal.py`、`util.py`、
>   `victim.c`、`matrix.sh`、`requirements.txt`；`Makefile` 的 `test` 目标运行前两者（共 2 用例，
>   `PYTHON_CMD ?= python2`，basic.py 兼容 py3）；无 `make check` 目标。完整申报表见
>   `0.10.0/test_package/MANIFEST.yml` 与 `0.10.0/notes.md`。
> - **上游测试真机执行结果（如实申报）**：2 用例全部执行、**0 通过、2 失败**——
>   两例均在 preflight `PTRACE_ATTACH` 处 EPERM，`reptyr` 报
>   `Unable to attach to pid N: Permission denied`；victim 的
>   `PR_SET_PTRACER: Invalid argument`（EINVAL）证据见 `reports/upstream-basic.log`
>   与 `reports/ptrace-capability-probe.txt`（tty-steal 用例使用同一 victim 程序）。根因是 **OHOS 内核对非特权进程禁用 ptrace**：
>   最小探针（同一会话/UID）实测父→子、兄弟间、祖父→孙的 ATTACH/SEIZE 全部 EPERM，
>   `PTRACE_TRACEME`、`process_vm_readv` 同样 EPERM（进程 Seccomp=2 + 1 filter、
>   CapEff 无 CAP_SYS_PTRACE、`yama/pdebug_scope` 读取 ENOSYS）。探针源码与原始输出见
>   `0.10.0/reports/ptrace-capability-probe.txt`。**该边界为系统策略，用户态适配无法消除，
>   未做任何桩化或断言弱化。**
> - **补全的测试范围**：18 条 TAP 断言——安装可见性；`-v`/`-h` 输出与退出码；缺 pid/非数字
>   pid/未知选项的参数校验；不存在 pid 的附加错误报告（No such process）；`-l` 新建 pty 对
>   并播报 slave；`-L` 在新建 pty slave 上运行命令、导出 `REPTYR_PTY`（与播报路径一致）、
>   转发子进程 stdout、子进程确认 slave 为字符设备。
> - **补全原因**：上游 E2E 用例在 OHOS 上被平台策略阻断，需以消费者视角覆盖平台可用行为面，
>   防止包损坏/安装错误流入 CI（含 L1e 破坏性反向验证）。
> - **新增测试文件清单**：
>   1. `archives/r/reptyr/0.10.0/test_package/test_reptyr.sh` — 18 条 TAP 断言，真实执行已安装二进制
>   2. `archives/r/reptyr/0.10.0/test_package/conanfile.py` — `test()` 通过 `sh test_reptyr.sh` 执行
>   3. `archives/r/reptyr/0.10.0/test_package/MANIFEST.yml` — 上游清点证据 + 断言计数声明（18）

## 验证结果

- 编译状态：**通过**（`make` rc=0；`conan-verify` G0–G4 与 L2/L4/L5 PASS；`finish` W3 本地 CI 阻塞门禁：`conan create` EXIT=0，profile `ohos-aarch64-device`）
- 上游测试用例通过率：**0/2（0%）** —— 2 例全部执行，均在 `PTRACE_ATTACH` 处 EPERM（OHOS 非特权进程 ptrace 平台边界，探针证据齐全；见上）
- 新增测试用例通过率：**18/18（100%）**
- 本地 CI 等价门禁（与平台 CI 同脚本 `ci/conan/build_and_test.sh`，profile `ohos-aarch64-device`）：L0 pass / L1 pass（含 L1a/L1b/L1c 与 L1e 破坏性反向验证，18/18）/ L4 pass（补丁安全扫描无危险函数）/ L5 pass；L2 因 reptyr 上游接口为 `-v`/`-h`（无 `--version`/`--help`）跳过，非阻断（日志 `reports/w3-local-ci.log`）

## 补充说明

### 适配要点

1. **构建链**：上游为普通 Makefile（`-MD -Wall -Werror -D_GNU_SOURCE`），配方以
   `make CC=<conan conf clang> -j1` 直调（R9/R33）；`install` 目标依赖 `install(1)`
   （OHOS 无此命令），由 `package()` 显式 `copy()` 安装。
2. **补丁 0001（Makefile 平台识别）**：`UNAME_S := $(shell uname -s)` 在 OHOS 返回
   `HarmonyOS`，不匹配 `Linux` 分支 → linux 后端目标未编译、链接失败；改为
   `ifneq ($(filter $(UNAME_S),Linux HarmonyOS),)`（纯平台识别，无平台宏；E007 家族）。
3. **补丁 0002（sockaddr_storage 重定义）**：`<linux/net.h>` → `<linux/socket.h>`（kernel 侧）
   与 `<sys/socket.h>`（musl）重复定义该结构，`-Werror` 下直接失败；在包含 linux 头文件期间
   以 `#if defined(__linux__) && !defined(__GLIBC__)` 守卫改名（E091 同类处置，accel-ppp 先例形态）。
4. **零平台宏**：2 个补丁均为可移植性修复，不注入 `__OHOS__`/`-D__OHOS__`（R8/PF5）。
5. **零依赖**：`requires` 为空（W0 检查；源码仅链接系统 libc）。
6. **CLI 声明**：软件级 `commands.json`（R38，`type=tool`，`ref=reptyr/0.10.0`）。

### 已知限制（重要）

| 项 | 技术原因 |
|----|----------|
| `reptyr PID` / `-T` / `-s` 在本平台不可用 | OHOS 内核对非特权进程禁用 ptrace：ATTACH/SEIZE/TRACEME 全 EPERM、`process_vm_readv` EPERM、`PR_SET_PTRACER` EINVAL（进程 Seccomp 过滤，见探针证据）。系统策略，用户态无法绕过；这正是上游 2 用例失败的原因 |
| 上游零通过 | 上游 2 用例依赖上述被禁能力；回归保护由本 PR 新增的 18 条消费者断言承担 |
| `reptyr -l` stdin 为 EOF 时忙等 | 上游未处理 `read()==0`；自动化中需带看护超时（test_package 已用 kill 收尾） |

### 验证证据

| 证据 | 位置 |
|------|------|
| ptrace 能力边界探针（源码 + 原始输出） | `0.10.0/reports/ptrace-capability-probe.txt` |
| 上游 2 用例真机日志（EPERM 原文） | `0.10.0/reports/upstream-basic.log`、`0.10.0/reports/upstream-tty-steal.log` |
| 测试摘要 + 18 条断言明细 | `0.10.0/reports/test-report.md` |
| 本地 CI 门禁日志 | `0.10.0/reports/w3-local-ci.log` |
| conan-verify 报告（G0–G4/L2/L4/L5） | `0.10.0/reports/conan-verify-report.md` |
| 适配笔记（问题、补丁、R51 申报表） | `0.10.0/notes.md` |

## 路径 B 知识贡献说明

- **新增草稿（与归档适配同一原子 PR 交付）**：
  - `knowledge/drafts/DRAFT-10103-reptyr-ptrace-capability-boundary.kv` + `.md` — 「OHOS 非特权进程 ptrace/进程内存访问被系统策略整体禁用：ptrace 类工具的适配前能力判定与可用子集」
    （采用任务号命名 `DRAFT-<任务号>-*`，避免与号段式草稿名冲突）
- **触发实例（第一手，本 PR）**：reptyr 0.10.0 上游 2 个 E2E 用例真机全量执行 **0/2**——
  `Unable to attach to pid N: Permission denied`（EPERM）、victim `PR_SET_PTRACER: Invalid argument`；
  最小探针覆盖 attach（父→子 / 兄弟 / 祖父→孙）、SEIZE、TRACEME、`process_vm_readv`、`PR_SET_PTRACER`，
  并附 `Seccomp: 2 / Seccomp_filters: 1`、`CapEff` 无 `CAP_SYS_PTRACE`、`pdebug_scope` ENOSYS 佐证。
  证据：`0.10.0/reports/ptrace-capability-probe.txt`、`reports/upstream-*.log`、`reports/test-report.md`。
- **问题类（可跨库复用）**：以 ptrace/process_vm 为能力前提的**进程控制类工具**（进程重挂载、调试器 attach、跟踪器、
  ptrace 型沙箱/模拟器、调试库 attach 模式）在 OHOS 上的**适配前判定与止损口径**：
  探针 → 按 errno 三态判定（EPERM=策略拒绝 / SIGSYS=未实现 / ENOSYS·EACCES=可降级）→
  盘点“非 ptrace 子集”（如 reptyr `-l/-L` 的 pty 管理）→ attach 类上游 E2E 如实申报平台边界 →
  禁止桩化/弱化断言（R34/R51）。**不是单个库的临时补丁**：判定树与口径可直接复用于同类工具。
- **查重结论与增量（2026-09-27 实查：index 541 条 + drafts 2094 kv/2089 md；`draft-review` 预审）**：
  - **`draft-review`（收紧签名后）= `verdict: create`，最高相似 E222=0.23**（`signature_overlap` 0.26、`keyword_jaccard` 0.05），
    低于仓库先例使用的灰区阈值 0.30；其后为 E179=0.21（ELF 签名类，仅签名正则/阶段弱重叠）与 E462=0.19（ptrace 平台限制的最接近条目，边界见下）（首版签名含泛化片段时为 review-similar 0.32，已按预审建议收紧为与现象精确对应的片段）。
  - 与 **E462**：E462 给出“ptrace system-wide blocked”结论并转向崩溃定位（SIGSEGV handler + FP-chain）；
    本条目补其**能力面/适配面**——权限模型全矩阵、适配前判定树、可用子集分类、测试台账口径，均为既有条目未覆盖；
  - 与 **E222**：E222 为 ptrace 不可用后的**崩溃证据链**；本条不涉崩溃诊断；
  - 与 `DRAFT-debugbreak-1.0-ohos-ptrace-gdb-test-equivalence`：其为断点/陷阱类库的**测试等价执行**（进程内信号）；
    本条为 attach 类工具的**功能可用性判定**（并明确“核心功能不可用、无进程内替代”），互补不重叠；
  - 与 `DRAFT-10686-skypat-perf-events-runtime-capability-probe`（perf，EACCES）、
    `DRAFT-ohos-syscall-capability-matrix-fork-probe`（未实现 syscall，SIGSYS）：方法论近邻（运行期能力探测），
    对象/errno 语义/结论均不同；
  - 与 **E246/E051**（seccomp-SIGSYS / 未实现 syscall）：本条 syscall 存在但被策略拒绝（EPERM，进程不崩）。
- **验证证据**：探针源码 + 原始输出、上游 2 用例日志、消费者 18/18（可用子集）、`notes.md` 边界说明。
- **关联 Issue**：按当前口径处理——#9670 已标注「Issue 机制已废弃，按任务说明执行」，最新合并的【知识库扩展】先例
  （turnstile 0.1.11，2026-09-26）亦未单独开 issue；如平台/评审委员会要求正式申请，可按模板补开并双向关联（`Closes #N`）。
- **预审留档**：`draft-review` 完整输出 JSON 存档于 `0.10.0/reports/draft-review.json`（三态建议与相似度证据，可由 `python3 scripts/ohc-run.py draft-review <草稿名> --json` 复现）；纳入正式库的决策权在主编审核（promote 由人工执行）。
