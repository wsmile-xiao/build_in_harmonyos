# sexpect 2.4.0 测试报告

> **项目**: sexpect 2.4.0（Expect for shells，PTY 交互自动化 CLI）
> **测试日期**: 2026-09-26
> **测试环境**: HarmonyOS / HongMeng Kernel 1.12.0，aarch64（HAD-W32），OHOS SDK clang 15.0.4
> **测试类型**: 官方测试套件（CTest）+ 消费者测试（test_package）+ 负向对照

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游 CTest 总数（OHOS 注册） | 25 | 100% |
| 上游 CTest 通过 (PASS) | 25 | 100% |
| 上游 CTest 失败 (FAIL) | 0 | 0% |
| 上游 Linux 守卫用例（OHOS 不注册，上游设计） | 2 | — |
| 消费者测试断言 | 10 | 100% |
| 消费者测试通过 | 10 | 100% |

**核心功能通过率**: ✅ **100%（上游 25/25 + 消费者 10/10）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游测试套件在打上抽象命名空间回退补丁后于设备端全量通过；
消费者测试覆盖打包后的二进制端到端流程与平台能力路径。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| HarmonyOS 拒绝 AF_UNIX 路径名 socket（bind EPERM） | 所有 spawn/expect 用例（22/25 基线失败） | 🔴（已修复） |
| `/tmp` 只读 | `send-null`、`send-128k` 临时文件 | 🟡（已修复） |
| 沙箱拒绝 `ls -l /`（EACCES） | `chdir-after-logfile` 的 wait 退出码 | 🟡（已修复） |
| 上游 Linux 守卫用例在 OHOS 不注册 | `spawn-nowait`、`still-open-after-exit` | 🟢（上游设计） |

### 2.3 可用功能清单

```
✅ spawn / send / expect（-exact/-glob/-re/-eof）/ interact / wait / get / close / kill / set / expect_out
✅ sockfile 会合（路径 socket 平台原生；OHOS 经抽象命名空间回退）
✅ 子进程退出码透传（wait）、超时分类（chkerr -is timeout）
✅ 僵尸回收（-zombie-idle）、TTL（-ttl）、非阻塞（-nonblock）、日志（-logfile）
```

### 2.4 已知限制

1. HarmonyOS 上 `SEXPECT_SOCKFILE` 不产生文件系统节点（抽象命名空间），依赖「sockfile 文件存在性」
   的外部脚本需改用 `sexpect get` 判活；sexpect 自身的判活/回收逻辑不受影响。
2. `interact` 的交互路径在无 tty 环境（CI/ctest）由上游脚本主动空跑（`[[ -t 0 ]] || exit 0`），
   本报告不宣称其已覆盖。

---

## 三、测试详情

### 3.1 通过的测试（上游 CTest，设备实测 25/25）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| glob2re | glob→ERE 转换单元级比对（可执行直跑） | ✅ PASS |
| version | `sexpect version` | ✅ PASS |
| spawn-ttl | server TTL 到期退出 | ✅ PASS |
| chkerr | 错误码分类（eof/timeout） | ✅ PASS |
| cstring | `-cstring` 转义 | ✅ PASS |
| chdir-after-exec | daemon chdir 不影响子进程 cwd | ✅ PASS |
| chdir-after-logfile | logfile 在 chdir 前打开 | ✅ PASS |
| cloexit | `-close-on-exit` | ✅ PASS |
| close | `close` 子命令 | ✅ PASS |
| eof-before-exit | 子进程退出前关闭 fd 的 EOF 语义 | ✅ PASS |
| expbuf-overflow | 期望缓冲溢出边界 | ✅ PASS |
| expect_out | 匹配输出（`$expect_out`） | ✅ PASS |
| expect-eof | `expect -eof` | ✅ PASS |
| expect-nocase | `-nocase` | ✅ PASS |
| expect-pattern | 模式匹配 | ✅ PASS |
| get-expbuf | `get -expect-buf` | ✅ PASS |
| interact-re-helper | 无 tty 环境按上游设计空跑 | ✅ PASS（upstream skip path） |
| kill | 信号与退出码（143） | ✅ PASS |
| send-128k | 128KiB 分块发送 | ✅ PASS |
| send-null | NUL 字节收发 | ✅ PASS |
| spawn-nohup | `-nohup` | ✅ PASS |
| spawn-nonblock | `-nonblock` 丢旧数据语义 | ✅ PASS |
| spawn-zombie-idle | 僵尸空闲回收 | ✅ PASS |
| spawn-zombie-idle_02 | 僵尸存活窗口 | ✅ PASS |
| still-data-after-exit | 子进程退出后残留数据可读 | ✅ PASS |

逐项执行证据：W3 本地 CI 的 `conan create` 内全量执行，逐项 25 条 `Passed` 与汇总见平台 CI 构建 #62096 日志（https://ohpcd.atomgit.com/ci?id=62096）；按仓库评审规则 19，原始 `*.log` 不随 PR 提交，本报告引用其汇总行（见第六节）。

### 3.2 失败的测试

无。

### 3.3 未在 OHOS 注册的上游用例（上游设计）

| 测试项 | 原因 |
|--------|------|
| spawn-nowait | `tests/CMakeLists.txt` 的 `if (CMAKE_SYSTEM MATCHES "Linux.*")` 守卫 |
| still-open-after-exit | 同上 |

> 二者在 Linux CI 环境（本项目的远端 CI worker）会注册并运行；HarmonyOS 构建不注册是上游
> 的设计选择（非本次适配裁剪），此处如实列出。

### 3.4 消费者测试（`test_package/test.sh`，10/10）

| 断言 | 内容 | 结果 |
|------|------|------|
| 1 | `sexpect version` = `sexpect 2.4.0` | ✅ PASS |
| 2 | `spawn`（scratch sockfile）成功 | ✅ PASS |
| 3 | `send -cr hello` + `expect -exact got:hello` 匹配 | ✅ PASS |
| 4 | `wait` 透传子进程退出码 3 | ✅ PASS |
| 5 | `spawn`（`/tmp` sockfile —— OHOS 抽象回退平台能力路径）成功 | ✅ PASS |
| 6 | `expect -exact abs:world` 匹配 | ✅ PASS |
| 7 | `wait` 透传子进程退出码 5 | ✅ PASS |
| 8 | `expect -t 1` 无匹配返回非零 | ✅ PASS |
| 9 | `chkerr -is timeout` 分类正确 | ✅ PASS |
| 10 | 无守护进程时 `get` 失败（负向对照） | ✅ PASS |

---

## 四、关键问题分析

### 问题1: HarmonyOS 拒绝 AF_UNIX 路径名 socket（22/25 基线失败）

**现象**：
```
[ERROR] bind: Operation not permitted (1)
!! ASSERT: sexpect sp -t 10 -ttl 20 bash --norc
12% tests passed, 22 tests failed out of 25
```

**根因**：设备探针确认所有可写位置（HMDFS/EACCES 变体、`/tmp` EROFS、`/dev/shm` EACCES、
`/data/local/tmp` EACCES）都无法创建路径名 AF_UNIX socket，仅抽象命名空间可 bind/connect。

**解决方案**：补丁 0001–0003 —— 路径 `bind()` 被拒（EPERM/EACCES/EROFS）时回退到
按 sockfile 路径 FNV-1a 哈希派生的抽象名；client 先试路径、再试抽象。无平台宏、
Linux 行为不变，修复后 25/25 通过。

### 问题2: `/tmp` 只读（send-null / send-128k）

**现象**：`touch /tmp/x` → `Read-only file system`，两用例的 `cat > /tmp/...` 失败。

**解决方案**：补丁 0005/0006 改用 `${TMPDIR:-/tmp}`；配方在 `build()` 内把 `TMPDIR`
指向构建目录（CI Linux 环境仍走 /tmp，行为不变）。

### 问题3: `chdir-after-logfile` 的 `ls -l /` 被沙箱拒绝

**现象**：`sexpect ex -eof` 通过后 `sexpect w` 断言失败，输出 `ls: /: Permission denied`。

**根因**：`sexpect wait` 退出码 = 子进程退出码；`ls -l /` 在 OHOS 沙箱 EACCES 退出非零。

**解决方案**：补丁 0004 将子命令改为 `ls -l $tmpfile`（同 cwd 刚创建的日志文件）；
被测的「logfile 在 chdir 前打开」语义仍被最终 `ls -l $tmpfile` 断言覆盖，回归保护不变。

---

## 五、测试环境

```
OS:        HarmonyOS / HongMeng Kernel 1.12.0 #1 SMP aarch64 (HAD-W32/W24)
Toolchain: OHOS SDK clang 15.0.4 (ohos-sdk@26.0.0.18/native/llvm)
CMake:     4.4.3（设备）；构建经 Conan 2.29.1（OHOS 适配版）
Profile:   ohos-aarch64-device（W3 本地验证）/ ohos-aarch64（CI worker）
bash:      GNU bash 5.3.9 (aarch64-unknown-linux-musl)
宿主机:    /storage/Users/currentUser/work/kasumizawa-miyuu/sexpect-wt
```

---

## 六、W3 `conan create` 证据（设备实测，2026-09-26）

- **全量复现**：W3 本地 CI 的干净 `conan create`（profile `ohos-aarch64-device`，
  rrev `#f826ce580fc2974758497fcf09b224de`）内全量执行上游套件，实测汇总：
  ```
  100% tests passed out of 25
  Total Test time (real) = 126.89 sec
  ...
  assertions: 10  passed: 10  failed: 0
  ALL TESTS PASSED
  ```
  逐项 25 条 `Passed` 明细见平台 CI 构建 #62096 日志（https://ohpcd.atomgit.com/ci?id=62096）；
  按仓库评审规则 19，原始 `*.log` 不随 PR 提交。
- 安装产物：`bin/sexpect`、`share/man/man1/sexpect.1`、`licenses/LICENSE`（`cmake --install` 输出）。
- `conan-verify`/`finish` 阶段的 `conan create`：此时配方与二进制均已入缓存（`Already installed!`），
  因此仅复跑 `test_package`（同样 10/10、`ALL TESTS PASSED`），不重复构建/执行 ctest——
  与 W3 全量运行结论一致。
- `conan-verify`（设备本地）：G0 / G1 / G2 / G3 / G4 / L2 / L4 / L5 全部 PASS
  （按仓库评审规则 19，验证报告原始副本不随 PR 提交，结论以本节汇总为准）。

---

*报告生成时间: 2026-09-26*
