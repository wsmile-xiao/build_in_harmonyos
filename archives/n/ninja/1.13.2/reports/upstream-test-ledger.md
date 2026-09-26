# ninja 1.13.2 上游测试双口径台账（Upstream Test Ledger）

> 生成时间: 2026-09-22　生成环境: pc3-15（HarmonyOS PC, aarch64, clang 15.0.4, CMake 4.1.2, GTest 1.17.0）
> 源码: 官方 tag v1.13.2（commit 3441b633c2fe2c494e958780ba0f4227b1327634，tarball sha256 974d6b2f... 与官方重新下载比对一致）
> 构建: `cmake -B . -DBUILD_TESTING=ON -DGTest_DIR=<conan gtest 1.17.0 OHOS 包> -DNINJA_FORCE_PSELECT=ON -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++`
> 运行: `./ninja_test`（GTest 注册项 + 实际执行日志见 `reports/ninja_test_run4.log` 摘要与下方台账）

## 一、双口径统计

| 口径 | C++ (src/*_test.cc) | Python (misc/*_test.py) |
|------|---------------------|--------------------------|
| 源码声明总数 source_declared_total | **433**（66 TEST + 367 TEST_F，官方 tag 全量 TEST 宏枚举） | **49**（ninja_syntax 21 + output 19 + jobserver 4 + jobserver_pool 5） |
| 当前配置可执行总数 configured_executable_total | **411**（GTest 实际注册，32 个 suite；上游原配 409，恢复补丁纳入 status_test 2 个后 411） | 49（脚本均可实例化，部分依赖工具 `script`/FIFO） |
| 实际执行总数 executed_total | 411 | 49（4 脚本全部运行） |
| 实际通过 executed_passed_total | **407** | **27**（21 + 4 + 2 + 1，另见逐项） |
| 失败数 | **4**（全部为真实平台/权限/工具条件，见第三节） | 22（12+3 个 output 错误/失败、2 个 jobserver、3+1 个 pool） |
| 未实例化/未运行 | 22（WIN32-only 9 + 守卫编译排除 13，见第二节映射） | 0（均尝试运行；部分受平台工具限制） |
| 全量通过率（通过/发现） | 407/433 = **94.0%** | 27/49 = **55.1%** |

> 高难度挑战硬门禁口径：实际通过数必须等于源码声明总数（433）。当前 4 个 C++ 用例为真实平台/权限/工具链条件硬阻塞，已在第三节逐项记录首错、命令、退出码、日志与恢复条件；未满足门禁时按任务规则禁止 commit/push/PR，最终回报真实阻塞事实。

## 二、C++ 用例逐项映射（声明 → 构建条件 → 目标 → GTest 注册 → 执行）

### 2.1 进入 ninja_test 目标并注册运行的 22 个测试文件（411 个用例）

| 测试文件 | 声明 TEST 宏数 | 预处理/构建条件 | 目标 | GTest 注册（suite 聚合） | 执行结果 |
|---|---|---|---|---|---|
| src/build_test.cc | 118 | 无平台排除 | ninja_test | BuildTest 75 + BuildWithLogTest 13 + BuildWithDepsLogTest 10 + BuildWithQueryDepsLogTest 6 + PlanTest 10 + StatTest 4 + BuildDryRun 2 + CleanDeadTest 2 + StripAnsiEscapeCodes 2 等 | 全过 |
| src/manifest_parser_test.cc | 53 | 无 | ninja_test | ParserTest 51 + 其余 | 全过 |
| src/graph_test.cc | 51 | 无 | ninja_test | GraphTest 50 + 其余 | 全过 |
| src/dyndep_parser_test.cc | 42 | 无 | ninja_test | DyndepParserTest 42 | 全过 |
| src/depfile_parser_test.cc | 29 | 无 | ninja_test | DepfileParserTest 29 | 全过 |
| src/clean_test.cc | 19 | 无 | ninja_test | CleanTest 17 + 其余 | 全过 |
| src/disk_interface_test.cc | 15 | 无 | ninja_test | DiskInterfaceTest 9 + 其余 | 全过 |
| src/util_test.cc | 14 | 无 | ninja_test | 部分 | 全过 |
| src/subprocess_test.cc | 13 | `#if defined(USE_PPOLL)` 下 SetWithLots 未注册（本机构建强制 pselect，USE_PPOLL 未定义） | ninja_test | SubprocessTest 12 | **9 过 3 败**（见 3.2/3.3/3.4） |
| src/build_log_test.cc | 11 | 无 | ninja_test | BuildLogTest 10 + BuildLogRecompactTest 1 | 全过 |
| src/deps_log_test.cc | 9 | 无 | ninja_test | DepsLogTest 9 | 全过 |
| src/clparser_test.cc | 8 | 无 | ninja_test | CLParserTest 8 | 全过 |
| src/missing_deps_test.cc | 7 | 无 | ninja_test | MissingDependencyScannerTest 7 | 全过 |
| src/lexer_test.cc | 7 | 无 | ninja_test | Lexer 7 | 全过 |
| src/jobserver_test.cc | 7 | 无 | ninja_test | Jobserver 6（PosixFifoClient 注册） | **5 过 1 败**（见 3.1） |
| src/string_piece_util_test.cc | 4 | 无 | ninja_test | StringPieceUtilTest 4 | 全过 |
| src/json_test.cc | 4 | 无 | ninja_test | JSONTest 4 | 全过 |
| src/edit_distance_test.cc | 4 | 无 | ninja_test | EditDistanceTest 4 | 全过 |
| src/status_test.cc | 2 | 上游未接入任何目标（CMakeLists/configure.py 均遗漏）→ 本任务恢复补丁纳入 | ninja_test | StatusTest 2 | **全过** |
| src/explanations_test.cc | 3 | 无 | ninja_test | Explanations 3 | 全过 |
| src/elide_middle_test.cc | 3 | 无 | ninja_test | ElideMiddle 3 | 全过 |
| src/state_test.cc | 1 | 无 | ninja_test | State 1 | 全过 |
| src/ninja_test.cc | 0（main） | — | ninja_test | — | — |
| src/test.cc | 0（框架辅助） | — | ninja_test | — | — |

### 2.2 声明但未实例化（22 个，均给出明确条件）

| 用例/文件 | 数量 | 未实例化原因（预处理或构建条件） |
|---|---|---|
| src/includes_normalize_test.cc | 6 | 上游 CMakeLists `if(WIN32)` 显式平台排除（含 `<direct.h>`，非 Windows 不可编译）；configure.py `is_windows()` 同口径 |
| src/msvc_helper_test.cc | 3 | 同上，MSVC 辅助器测试，WIN32-only |
| src/subprocess_test.cc SetWithLots | 1 | `#if defined(USE_PPOLL)`：本机 OHOS 上 ppoll() 运行时返回 ENOMEM（实测 `ninja: ppoll: Out of memory` 循环），按平台适配强制 `NINJA_FORCE_PSELECT=ON`（USE_PPOLL 未定义）→ 该用例按上游守卫排除 |
| 上述 21 文件内 `#if defined(_WIN32)` 分支 | 12 | 各文件内 Windows 专属 TEST 宏（上游守卫），本平台不编译 |

## 三、C++ 失败用例逐项记录（首错/命令/退出码/日志/恢复条件）

### 3.1 Jobserver.PosixFifoClient
- 测试源: src/jobserver_test.cc:312（`mknod(fifo_path, S_IFIFO|0666, 0)`）
- 首错: `Expected equality of these values: 0 / ret Which is: -1` + `Could not create FIFO at: ninja_test_jobserver_fifo-<rand>/fifo`
- 命令: `./ninja_test --gtest_filter=Jobserver.PosixFifoClient`
- 退出码: -1（mknod EPERM）
- 日志: `reports/ninja_test_run4.log`
- 平台证据: 全量候选挂载点 mkfifo/mknod 验证均失败 —— `/dev/shm`(tmpfs) EACCES、`/storage/Users/currentUser`(HMDFS) EPERM(Operation not permitted)、`/storage/External`、`/storage/userExternal`、`/storage/hmdfs` 均 EPERM/EACCES，`/tmp` 为只读 erofs；设备上不存在任何"可写且支持 POSIX FIFO"的挂载点（HMDFS 不保留 FIFO inode 语义）
- 阻塞归属: 真实平台/文件系统限制（非当前库缺陷）
- 恢复条件: 提供支持 mknod/FIFO 的写入挂载点（ext4/tmpfs 且 hmmac 放行）后重跑该用例

### 3.2 SubprocessTest.InterruptChildWithSigHup
- 测试源: src/subprocess_test.cc:126（子进程 `kill -HUP $$`）
- 首错: `Expected equality of these values: ExitInterrupted Which is: 130 / subproc->Finish() Which is: 129`
- 命令: `./ninja_test --gtest_filter=SubprocessTest.InterruptChildWithSigHup`
- 退出码: 129（子 shell WIFEXITED(129)=128+SIGHUP）
- 日志: `reports/ninja_test_run4.log`
- 平台证据: 设备 `/bin/sh`（306288 字节，toybox/OHOS 适配 shell）收到 SIGHUP 时以 `exit(128+1)=129` 正常退出（WIFEXITED），而非被信号杀死（WIFSIGNALED）；对照 `/data/service/hnp/bin/bash` 为 WIFSIGNALED(SIGHUP)。ninja `ParseExitStatus` 仅对 WIFSIGNALED(SIGHUP) 映射 ExitInterrupted，故返回 129 ≠ 130。SIGTERM 对应用例 InterruptChildWithSigTerm 通过，证明非 ninja 缺陷
- 阻塞归属: 真实平台 shell 信号语义差异
- 恢复条件: 在符合 POSIX 信号语义的 shell（如 bash）环境下运行；或平台 /bin/sh 修复 SIGHUP 处理

### 3.3 SubprocessTest.SetWithSingle
- 测试源: src/subprocess_test.cc:166（kSimpleCommand = `ls /`）
- 首错: `Expected equality of these values: ExitSuccess Which is: 0 / subproc->Finish() Which is: 1`；stderr: `ls: /: Permission denied`
- 命令: `./ninja_test --gtest_filter=SubprocessTest.SetWithSingle`
- 退出码: 1（`ls /` 因根目录不可读失败）
- 日志: `reports/ninja_test_run4.log`
- 平台证据: 设备根目录权限 `drwx--x--x 19 root root`（711，others 无 r），当前非 root 用户（uid 20020101）对 `/` 无读权限，`ls /` 必然 exit 1；标准 POSIX 上 `/` 为 755 可读
- 阻塞归属: 真实平台权限条件（沙箱根目录不可读）
- 恢复条件: 以具备根目录读权限的用户运行；或平台放开根目录读权限

### 3.4 SubprocessTest.SetWithMulti
- 测试源: src/subprocess_test.cc:181（kCommands = `ls /`、`id -u`、`pwd`）
- 首错: `Expected equality of these values: ExitSuccess Which is: 0 / processes[i]->Finish() Which is: 1`
- 命令: `./ninja_test --gtest_filter=SubprocessTest.SetWithMulti`
- 退出码: 1（`ls /` 根目录不可读；`id` 亦不在 PATH 中，未安装 coreutils `id`）
- 日志: `reports/ninja_test_run4.log`
- 阻塞归属: 真实平台权限条件（同 3.3）
- 恢复条件: 同 3.3；并补充含 `id` 的可执行路径

## 四、Python 测试逐项结果

### 4.1 misc/ninja_syntax_test.py — 21/21 通过 ✅
命令: `python3 misc/ninja_syntax_test.py`，EXIT 0（日志 `reports/python_tests.log`）

### 4.2 misc/output_test.py — 19 个用例，4 过 / 3 失败 / 12 错误 ❌
- 错误类（12 个）: `subprocess.CalledProcessError` —— 命令 `['script', '-qfec', '<ninja> ...', '/dev/null']` 退出非 0；平台 `/data/service/hnp/bin/script` 为 BusyBox（v1.37.0），不支持 util-linux `script -e` 选项（实测 `unrecognized option: e`），上游测试依赖 util-linux script 捕获 tty 输出
- 失败类（3 个）: test_issue_2621 / test_pr_2540 / test_tool_compdb_targets —— 均在 script 包装路径下输出为空/不一致（同 4.2 错误类根因：BusyBox script 无 -e，stdout 捕获不完整）
- 阻塞归属: 真实平台工具差异（缺 util-linux `script`）
- 恢复条件: 提供 util-linux 版 `script`（或等价 tty 捕获工具）后重跑

### 4.3 misc/jobserver_test.py — 4 个用例，2 过 / 1 失败 / 1 错误 ❌
- test_jobserver_client_with_posix_pipe: 通过；test_no_jobserver_client: 通过
- test_jobserver_client_with_posix_fifo: `PermissionError: [Errno 1] Operation not permitted`（FIFO 创建，同 3.1 平台条件）
- 失败 1: 基于 FIFO 的 jobserver_pool 子进程返回 1（同 FIFO 条件）
- 恢复条件: 同 3.1

### 4.4 misc/jobserver_pool_test.py — 5 个用例，1 过 / 3 错误 / 1 跳过 ❌
- 错误 3: MAKEFLAGS/fifo 相关（`jobserver_pool.py -j10 --fifo` 等，FIFO 创建 EPERM + 缺 `id` 等工具）
- 跳过 1: 上游条件跳过（无 jobserver 环境）
- 恢复条件: 同 3.1 + 补齐平台工具链

## 五、结论
- 独立上游用例共 **482**（C++ 433 + Python 49），C++ 当前配置可执行 **411**，实际运行 411，通过 **407**，失败 **4**（全部真实平台/权限/工具条件，逐项证据见第三节）；Python 运行 49，通过 27。
- 已按源码测试入口恢复规则完成 1 项最小补丁恢复：上游遗漏的 `status_test.cc`（2 用例）纳入 ninja_test 目标并实际通过（补丁随本任务配方归档，见 `patches/`）。
- 未满足高难度挑战"全部上游测试通过"硬门禁（407/433），按任务规则禁止 commit/push/PR，本任务回报真实阻塞事实与恢复条件。

---

## R02 返工更新（2026-09-22，task ninja-1.13.2-r02）

### 双口径统计（R02 复验，口径与 R01 一致）
| 项 | R01 | R02 复验 |
|---|---|---|
| source_declared_total（C++） | 433 | **433**（grep 与严格解析双口径一致） |
| configured_executable_total（C++ 注册） | 411 | **411** |
| executed_passed_total | 407 | **407**（无新增通过） |
| failed | 4 | **4**（R02 逐项重跑确认仍失败） |
| 未实例化 | 22 | **22**（全部有明确上游排除条件，见下） |
| Python 通过 | 27 | **27** |

### R02 恢复尝试与结果（逐项）
1. **R02-A FIFO 全候选挂载点深度扫描（新增候选）**：除 R01 已测的 /dev/shm、/storage/*、/tmp 外，追加验证 /mnt/hmdfs/100、/data/storage/el2、/storage/Users/currentUser/appdata（sharefs）、/data/storage/el2/media（fuse）、/mnt/hmdfs/100/cloud（hmdfs）等；全部 mkfifo 失败——HMDFS/sharefs/hmdfs 挂载点 mkdir 即 EPERM 或 mkfifo EPERM，tmpfs 挂载点（/dev/shm、/data/storage/el2 等）EACCES，唯一可写的 HMDFS 目录（/storage/Users/currentUser/tmp 等）stat 模式为 0o2771（非真实 0700，chmod 被忽略）且 mkfifo EPERM。结论：设备不存在"可写且支持 POSIX FIFO 且保留真实 0700 语义"的挂载点。重跑 `./ninja_test --gtest_filter=Jobserver.PosixFifoClient`（TMPDIR=/storage/Users/currentUser/tmp）首错复现：`Could not create FIFO`（mknod -1, EPERM）。
2. **R02-B PATH/POSIX shell 恢复**：PATH 追加 /system/bin 后重跑 4 个失败用例——`id -u` 返回 `id: bad uid 20020101`（toybox id 无法解析该 uid，exit 1），`ls /` 仍 Permission denied（根目录 drwx--x--x root 711，非 root 无读权限），FIFO 用例复现 EPERM；`SubprocessTest.InterruptChildWithSigHup` 仍 129 vs 130。核 src/subprocess-posix.cc：ninja 子进程 shell 硬编码 `/bin/sh -c`（posix_spawn），无 $SHELL/NINJA_SHELL 环境覆盖项（grep 确认），无法在不改库行为的前提下切换 POSIX 信号语义 shell（bash 实测 WIFSIGNALED 正确，但 ninja 不用它）。
3. **R02-C Python 组恢复**：BusyBox script（v1.37.0，`/data/service/hnp/bin/script -> busybox`）不支持 util-linux 的 `-e` 选项，设备无 apt/dnf/yum 等包管理器可安装替代（确认无）；output_test 19 用例仍 3 失败+12 错误（script -e 相关），jobserver 组 1 失败+1 错误、pool 组 3 错误+1 跳过（FIFO 限制），ninja_syntax_test 21/21 通过。
4. **R02-D 22 个未实例化项复核**：全部有明确上游排除条件——12 个位于 `#if defined(_WIN32)` 守卫（build_test.cc 2、disk_interface_test.cc 2、graph_test.cc 1、jobserver_test.cc 1、manifest_parser_test.cc 2、util_test.cc 4）；9 个为 WIN32-only 文件（includes_normalize_test.cc 6 + msvc_helper_test.cc 3，CMakeLists `if(WIN32)` 与 configure.py `is_windows()` 双重排除）；1 个为 `#if defined(USE_PPOLL)` 守卫（subprocess_test.cc SetWithLots，本平台 ppoll 运行时 ENOMEM 已强制 pselect 故 USE_PPOLL 未定义）。status_test.cc 2 个为唯一无排除条件者，R01 已最小补丁纳入并注册（411 含之）。

### R02 结论
- 全量通过率仍为 **407/433 (94.0%)**，当前配置可执行集合通过率 **407/411 (99.0%)**；4 个失败与 22 个未实例化项均复跑/复核确认，无新增通过项、无伪造。
- 高难度挑战上游测试硬门禁仍未满足：按任务规则禁止 commit/push/PR/rebuild，回报真实阻塞事实与恢复条件。

---

## R03 返工更新（2026-09-23，task ninja-1.13.2-r03-pc3-15-20260922T162056Z）

### 平台条件逐项核验（任务头 4 项，实际命令 + 退出码 + 证据）
| # | 条件 | 核验命令（摘） | 结果 | 证据 |
|---|---|---|---|---|
| 1 | mknod/FIFO + 保留真实 0700 的可写挂载点 | `toybox mkfifo` 于 worktree(/storage/Users/currentUser/junshi_liu/worktrees/pc3-15-ninja-1.13.2)、/dev/shm、/tmp、/storage/hmdfs、/data/local/tmp、/storage/userExternal、/storage/External、/mnt/hmdfs/100/non_account、/sys/fs/cgroup | **FAIL** | 唯一可写目录（HMDFS）chmod 700 后 stat 仍 0o2771（chmod 被忽略）且 mkfifo EPERM；/dev/shm mkdir EACCES；/tmp 只读（Read-only file system）；其余挂载点 EPERM/EACCES。不存在"可写 + 支持 FIFO + 真实 0700"挂载点 |
| 2 | /bin/sh 对 SIGHUP 以 WIFSIGNALED 退出 | C probe（fork + execl /bin/sh -c 'sleep 5' + kill(SIGHUP) + waitpid） | **FAIL** | probe 输出 `WIFEXITED code=0 => NOT WIFSIGNALED`；R03 复跑 SubprocessTest.InterruptChildWithSigHup 仍 `130 vs 129`。OHOS /bin/sh（/system/bin/sh, musl aarch64）收到 SIGHUP 非信号死亡 |
| 3 | 根目录读权限 + 可解析当前 uid 的 id 工具 | `ls /`；`toybox id` / `/system/bin/id` / busybox id | **FAIL** | `/` mode=711 drwx--x--x root，`ls /` Permission denied；`toybox id` → `bad uid 20020101` exit 1，busybox id → `/etc/passwd: bad record` |
| 4 | util-linux 版 script（支持 -e） | `script -e -c 'echo ttytest' /dev/null`；find /data /system 搜 script | **FAIL** | 仅 `/data/service/hnp/bin/script -> busybox_1.37.0`，实测 `unrecognized option: e`；全盘无 util-linux script；设备无包管理器可安装 |

### 双口径统计（R03 独立复跑，口径与 R01/R02 一致）
| 项 | R01 | R02 | R03 复验 |
|---|---|---|---|
| source_declared_total（C++） | 433 | 433 | **433**（官方 tag 全量 TEST 宏枚举，grep+严格解析双口径一致） |
| configured_executable_total（C++ 注册） | 411 | 411 | **411**（GTest 实际注册，32 suite；含恢复补丁 status_test 2） |
| executed_passed_total | 407 | 407 | **407**（`./ninja_test` 实测 411 ran / 407 passed / 4 failed，FULL_EXIT=1） |
| failed | 4 | 4 | **4**（Jobserver.PosixFifoClient / InterruptChildWithSigHup / SetWithSingle / SetWithMulti，R03 独立复跑确认） |
| 未实例化 | 22 | 22 | **22**（全部有明确上游排除条件：WIN32 守卫 12 + WIN32-only 文件 9 + USE_PPOLL 1，不强制纳入） |
| Python 通过 | 27 | 27 | **27**（R03 独立复跑：ninja_syntax 21/21；output_test 19 run 3 fail+12 error；jobserver_test 4 run 1 fail+1 error；jobserver_pool_test 5 run 3 error+1 skip） |

### R03 恢复尝试（逐项，独立执行）
1. **R03-A 全量 ninja_test**：`cd /storage/Users/currentUser/tmp/builds/ninja-1.13.2.build && ./ninja_test` → `[==========] 411 tests from 32 test suites ran` / `[  PASSED  ] 407` / `[  FAILED  ] 4`，EXIT=1（日志 `reports/ninja_test_run_r03.log`）。
2. **R03-B 4 失败用例设 TMPDIR+PATH 复跑**：`TMPDIR=/storage/Users/currentUser/tmp/ohr03_tmpdir PATH=/data/service/hnp/bin:$PATH ./ninja_test --gtest_filter=Jobserver.PosixFifoClient:SubprocessTest.InterruptChildWithSigHup:SubprocessTest.SetWithSingle:SubprocessTest.SetWithMulti` → 4 全部 FAILED（PosixFifoClient mknod -1 EPERM；SigHup 129 vs 130；SetWithSingle/Multi `ls /` exit 1）。TMPDIR 目录 stat 仍 0o2771（非真实 0700），说明 HMDFS 无法满足 0700 语义（日志 `reports/adaptation-validation-r03.log`）。
3. **R03-C Python 组独立复跑**：ninja_syntax_test.py → `Ran 21 tests ... OK` EXIT 0；output_test.py → `Ran 19 tests / FAILED (failures=3, errors=12)`（script -e 平台工具缺失）；jobserver_test.py → `Ran 4 tests / FAILED (failures=1, errors=1)`（FIFO EPERM）；jobserver_pool_test.py → `Ran 5 tests / FAILED (errors=3, skipped=1)`（FIFO + 缺工具）。日志：`reports/python_*_r03.log`。
4. **R03-D 22 未实例化复核**：维持 R02 判定（WIN32 守卫 12 + WIN32-only 文件 9 + USE_PPOLL 1），全部有明确上游排除条件，无无排除条件项漏网；status_test.cc 2 项已由 R01 最小补丁纳入并注册（411 含之，R03 通过）。

### R03 结论
- 全量通过率仍为 **407/433 (94.0%)**，当前配置可执行集合通过率 **407/411 (99.0%)**；4 个失败与 22 个未实例化项复跑/复核确认，无新增通过项、无伪造、无宽泛排除。
- 高难度挑战上游测试硬门禁（全量通过）仍未满足：按任务规则禁止 commit/push/PR/rebuild，回报真实阻塞事实与恢复条件（见 natural-terminal-r03.log）。

---

## R04 返工更新（2026-09-23，task ninja-1.13.2-r04-pc3-15-20260922T172741Z）

### 本轮适配动作：subprocess shell 适配补丁（0003）
- **修改点**：`src/subprocess-posix.cc` 子进程 shell 由硬编码 `/bin/sh` 改为编译期宏 `NINJA_SUBPROCESS_SHELL`（默认 `/bin/sh` 保持其他平台行为不变，OHOS 构建以 `-DNINJA_SUBPROCESS_SHELL=/data/service/hnp/bin/bash` 覆盖）；`CMakeLists.txt` 新增 `NINJA_SUBPROCESS_SHELL` cache 变量并注入 `libninja` 编译定义。
- **根因**：OHOS /bin/sh（toybox 系，musl aarch64）对 SIGHUP 以 `WIFEXITED(128+1)=129` 正常退出而非 `WIFSIGNALED`；bash（/data/service/hnp/bin/bash，POSIX 信号语义）本轮 C probe 实测 `WIFSIGNALED sig=1`。
- **运行时行为说明**：补丁默认值仍为 `/bin/sh`，仅在本库配方构建时显式传入 bash 路径才改变子进程 shell；ninja 子进程命令（rule command / depfile 生成等）将改用 bash 执行，POSIX 语义一致，bash 位于构建 profile 的 CONFIG_SHELL/SHELL 指向路径。
- **编译复验**：`cmake . -DNINJA_SUBPROCESS_SHELL=/data/service/hnp/bin/bash && cmake --build . --target ninja_test -j2` → BUILD_EXIT=0。
- 补丁文件：`patches/0003-src-subprocess-posix.cc.patch`、`patches/0004-CMakeLists.txt.patch`（或合并补丁，见 patches/ 实际文件）。

### 双口径统计（R04 独立复跑）
| 项 | R01/R02/R03 | R04 复验 |
|---|---|---|
| source_declared_total（C++） | 433 | **433** |
| configured_executable_total（C++ 注册） | 411 | **411** |
| executed_passed_total | 407 | **408**（`./ninja_test` 实测 411 ran / 408 passed / 3 failed，FULL_EXIT=1；补丁修复 InterruptChildWithSigHup） |
| failed | 4 | **3**（Jobserver.PosixFifoClient / SetWithSingle / SetWithMulti，见下） |
| 未实例化 | 22 | **22**（维持明确上游排除条件） |
| Python 通过 | 27 | **41**（R04 复扫发现 colrm/column 版 util-linux 语义 script 支持 -e：output_test 从 R03 的 3 fail+12 error 降至 1 fail+1 error；ninja_syntax 21/21；jobserver 2 过 1 fail 1 error；pool 1 过 3 error 1 skip） |

- 全量通过率：**408/433 (94.2%)**；当前配置可执行集合通过率：**408/411 (99.3%)**。
- 4 用例复跑（`--gtest_filter` 4 项，TMPDIR=/storage/Users/currentUser/tmp/ohr04_tmpdir + PATH 含 /data/service/hnp/bin）：
  1. **InterruptChildWithSigHup：PASSED**（补丁生效，subproc->Finish()==130==ExitInterrupted，WIFSIGNALED 语义满足）
  2. Jobserver.PosixFifoClient：仍 FAILED（mknod FIFO EPERM，HMDFS 平台条件未变）
  3. SubprocessTest.SetWithSingle：仍 FAILED（`ls /` exit 1，根目录 711 不可读）
  4. SubprocessTest.SetWithMulti：仍 FAILED（同上 + `id -u` bad uid）
- 日志：`reports/ninja_test_run_r04.log`（sha256 b09006bb...）、`reports/adaptation-validation-r04.log`（sha256 f06bb040...）。

### R04 结论
- 通过数较 R03 +1（408/411=99.3%，408/433=94.2%），为补丁真实收益；剩余 3 个失败仍为真实平台/权限条件（FIFO、根目录读权限+id），22 个未实例化项维持上游排除判定。
- 高难度挑战硬门禁（全量通过）仍未满足；按任务规则在平台条件全部落实前不得伪交付，commit/push/PR/rebuild 判定见自然终态。

---

## R06 返工更新（2026-09-25，task ninja-1.13.2-r06-pc3-15-20260924T214107Z）

### 本轮适配动作（两处，均为当前库真实交付/门禁修复）
1. **补丁修复（0003/0004）**：原 0003/0004 hunk 头行数/偏移声明错误（0004 hunk1 声明 `-4,6` 但官方源第 4 行为
   `include(CheckIPOSupported)` 而非空行、hunk2 前导空行上下文与 `else()` 不符；0003 hunk1 计数 6 vs 实际 7），
   对官方 v1.13.2 源按序应用必然失败（CI `invalid hunk no.1 at 11`）。重新生成方式：在官方源 git 仓库中
   `git apply` 0001/0002 后，用 `edit_file` 实施 0003/0004 语义修改，再 `git diff` 提取精确 hunk 生成新补丁
   （生成命令见 natural-terminal-r06.log / 结果回报）。验证：全新官方源上 `git apply --check` 与 `patch -p1`
   按序 0001→0004 全部 rc=0，最终文件含 `NINJA_SUBPROCESS_SHELL` 宏与 `target_compile_definitions`。
2. **配方修复（conanfile.py generate/build）**：R06 全新 conan create 日志发现原配方声明的适配未生效——
   `tc.variables["NINJA_FORCE_PSELECT"]="ON"` 被上游 `option()` 覆盖（CMakeCache 实测 `NINJA_FORCE_PSELECT:BOOL=OFF`，
   编译标志 `-DUSE_PPOLL=1`，运行时 `ninja: ppoll: Out of memory` 死循环），且 `NINJA_SUBPROCESS_SHELL` 从未传入
   （实测 `/bin/sh`）。修复：改为 `cmake.configure(variables={"NINJA_FORCE_PSELECT":"ON","NINJA_SUBPROCESS_SHELL":"/data/service/hnp/bin/bash"})`
   命令行传参。修复后新构建实测 `NINJA_FORCE_PSELECT:BOOL=ON`、`NINJA_SUBPROCESS_SHELL:STRING=/data/service/hnp/bin/bash`、
   `USE_PPOLL` 消失；`SubprocessTest.InterruptChildWithSigHup` PASSED（130==ExitInterrupted）。

### 双口径统计（R06 独立复跑，全部新日志，见 reports/）
| 项 | R04 | R06 复验 |
|---|---|---|
| source_declared_total（C++） | 433 | **433** |
| configured_executable_total（C++ 注册） | 411 | **411**（无 USE_PPOLL → SetWithLots 未注册，口径一致） |
| executed_passed_total | 408 | **408**（`./ninja_test` 实测 411 ran / 408 passed / 3 failed，ninja_test_run_r06.log） |
| failed | 3 | **3**（Jobserver.PosixFifoClient / SetWithSingle / SetWithMulti，平台条件逐项复现，见下） |
| 未实例化 | 22 | **22**（维持明确上游排除条件：WIN32 守卫 12 + WIN32-only 文件 9 + USE_PPOLL 1） |
| Python 通过 | 41 | **42/49**（ninja_syntax 21/21；output_test 18 过 1 错；jobserver 2 过 1 fail 1 err；pool 1 过 3 err 1 skip；R06 实测日志） |

- 全量通过率：**408/433 (94.2%)**；当前配置可执行集合通过率：**408/411 (99.3%)**。
- 3 失败用例复跑（adaptation-validation-r06.log，TMPDIR=/storage/Users/currentUser/tmp/ohr06_tmpdir + PATH 含 colrm script）：
  1. **InterruptChildWithSigHup：PASSED**（修复补丁 + 配方 bash 覆盖双生效）
  2. Jobserver.PosixFifoClient：FAILED（mknod FIFO EPERM，HMDFS 平台条件，恢复条件=提供支持 POSIX FIFO 的写入挂载点）
  3. SubprocessTest.SetWithSingle：FAILED（`ls /` exit 1，根目录 711 不可读）
  4. SubprocessTest.SetWithMulti：FAILED（同上 + toybox id 无法解析 uid 20020101）
- Python 平台条件：output_test 唯一 error=test_issue_2586（受限 env `{'NINJA_STATUS':''}` 无 PATH → script 不可达）；
  余下 errors/fails 均为 BusyBox script 无 util-linux `-e`、FIFO EPERM、缺工具链（恢复条件同 R03/R04 记录）。
- 消费方验证：conan create 内 test_package 消费者 `ohos-ninja-consumer-ok:3` EXIT 0（conan-create-r06.log）+ 鸿蒙专项
  ohos-spec-test-r06.log（`<conan产物>/bin/ninja -v -f ohos_build.ninja` BUILD_EXIT=0，`./hello_ohos` RUN_EXIT=0，输出 `ohos-ninja-consumer-ok:3`）。
- 新日志 SHA-256：conan-create-r06.log=92cb49bc...、ninja_test_run_r06.log=a8336e4e...、adaptation-validation-r06.log=07b05d93...、
  python_ninja_syntax_test_r06.log=019c2072...、python_output_test_r06.log=59ac0991...、python_jobserver_test_r06.log=dad55f97...、
  python_jobserver_pool_test_r06.log=032177a9...、ohos-spec-test-r06.log=ee348017...、bootstrap/source/atomicity-audit-r06.log 见 reports/。

### R06 结论
- 补丁与配方双修复后 conan create 4 补丁全链路 EXIT=0（新日志，未复用旧日志）；全量测试 408/433 (94.2%)、
  配置可执行 408/411 (99.3%)、Python 42/49；3 个 C++ 失败与 Python 缺项全部为真实平台/权限/工具条件（逐项首错、命令、退出码、日志与恢复条件已记录）。
- 高难度挑战硬门禁（全量通过）仍未满足；按任务规则在平台条件全部落实前不得伪交付；本轮交付判定见 natural-terminal-r06.log。
