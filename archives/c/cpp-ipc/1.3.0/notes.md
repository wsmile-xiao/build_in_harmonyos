# cpp-ipc 1.3.0 适配笔记

## 编译环境
- 构建系统: CMake（上游 `CMakeLists.txt`，`cmake_minimum_required(3.10)`，`set(CMAKE_CXX_STANDARD 17)`）
- 编译日期: 2026-10-06
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，libc++ 15.0.4，musl），HarmonyOS aarch64
- 状态: built

## 编译步骤

1. **源码**：`init-build cpp-ipc 1.3.0 --url=https://github.com/mutouyun/cpp-ipc/archive/refs/tags/v1.3.0.tar.gz`
   （官方 tag 归档，实测 GET 200 / 643531 B / `sha256=a5ffb67ff451aa28726ab7801509c5c67feb737db49d2be4f7c70a4e9fad2fee`，
   解包根 `cpp-ipc-1.3.0/`，269 个文件；自动 URL 搜索只会给出 savannah 假候选，必须显式给 URL）。
2. **探索构建**（模式 B）：`cmake -DCMAKE_BUILD_TYPE=Release .. && make -j2`
   → 产出 `build/lib/libipc.a`（271164 B）；`make install` 装出 `include/libipc/*.h` + `lib/libipc.a`（staging: bin=0 lib=1）。
3. **配方生成**：`conan-init`（默认给的是 Autotools 模板，本包是 CMake ⇒ 手写 `conanfile.py`）：
   `cmake_layout` + `CMakeToolchain`，`LIBIPC_BUILD_TESTS/OFF`、`LIBIPC_BUILD_DEMOS=OFF`、
   `LIBIPC_BUILD_SHARED_LIBS` 由 `shared` option 映射，`CMAKE_SYSTEM_NAME=Linux`（E092：CMake 无 HarmonyOS platform module）。
4. **验证**：`conan-verify`（G1 配方完整性 → G0 风险预评 → G2 `conan create` 干净源码重建 → G3/G4/L2/L4/L5）。
5. **收尾**：`finish built` → `submit`（W4 前置）→ `graph validate`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/libipc/platform/detail.h:77/79: error: deduction guide must be declared in the same scope as template 'std::unique_ptr'` | 上游把 `std::unique_ptr` 的推导指引直接写进 `namespace std`（往 `namespace std` 注入声明本就是 UB）；libc++ 把 `unique_ptr` 放在 **inline ABI namespace**（`std::__n1`/`__n1` 见 `__config_site` 的 `_LIBCPP_ABI_NAMESPACE`），两者不是同一作用域 ⇒ clang 拒绝；libstdc++ 宽容所以上游没发现 | 补丁 `0001-src-libipc-platform-detail.h.patch`：用 `#if !defined(_LIBCPP_VERSION)` 包住该段。**指引未被本库使用**（全库唯一 `unique_ptr` 用点 `src/libipc/ipc.cpp:229` 显式传模板参数，`grep` 实证），跳过无语义损失 |
| 2 | `test/test_sync.cpp:21/35: use of undeclared identifier 'pthread_mutexattr_setrobust' / 'pthread_mutex_consistent'` | musl（OHOS SDK `pthread.h`）只定义 `PTHREAD_MUTEX_ROBUST` 常量、**不声明** robust mutex 函数族 —— 既有条目 **E192** 已记录（`source-patch`） | 补丁 `0002-test-test_sync.cpp.patch`：守卫改成 `#if defined(IPC_OS_LINUX_) && defined(__GLIBC__)`（按"被禁的具体操作"写、不用 `__OHOS__` 平台宏 ⇒ PF5/R8 合规）；语义 = robust mutex 是 Linux+glibc 扩展，musl 目标一律跳过 |
| 3 | 构建驱动 Step7 `make check` 报 `No rule to make target 'check'` | 上游 CMake **没有注册 ctest**，测试要 `LIBIPC_BUILD_TESTS=ON` 单独编 `./bin/test-ipc`；另需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（自带 3rdparty/gtest 的 `cmake_minimum_required` 低于 3.5，CMake 4.1 直接拒） | 不阻塞编译；按 `test_package/MANIFEST.yml` 逐例实测（见"验证结果"），如实回填 |
| 4 | 上游 27 例测试 **13 过 / 6 失败 / 4 崩溃 / 4 超时**，stderr 大量 `fail condition broadcast[38]`、`fail condition wait[38]`、`fail mutex unlock[1]` | **HongMeng 内核未实现 3 个 futex 操作**：`FUTEX_CMP_REQUEUE_PI` / `FUTEX_WAIT_REQUEUE_PI` / `FUTEX_TRYLOCK_PI` → `ENOSYS(38)`；而上游 a0 层的条件变量 wait/wake 全部走这三种操作（`src/libipc/platform/linux/a0/ftx.h`、`mtx.c` 的 `a0_cnd_wake`/`a0_cnd_timedwait_impl`） | 本机探针实测定性（见"验证结果"）。**本包不做 a0 并发层降级改造**（改并发语义超出本次适配范围、且会让 CI 引入挂死风险），如实记录为已知限制；机制沉淀为 `B判定=create` 的知识草稿（见"注意事项"） |
| 5 | `refresh-patch --auto` 生成 `detail.h` 补丁时 `dry-run 失败` | 上游 `detail.h` 是 **CRLF** 行尾，工具用**系统 patch**（toybox）试打，而它读文件时统一换行、生成的补丁上下文是 LF ⇒ 上下文匹配不上 | 把**本地 `.orig` 基线**里该文件行尾归一化为 LF 后重新生成（补丁内容不受影响，工具按文本读取）。**补丁能否打在真实上游文件上，已用 conan 实际使用的 `patch_ng` 对原始 CRLF 文件直接验证 = True**（否则 G2 `conan create` 必失败，见验证结果） |

## 源码修改

- `patches/0001-src-libipc-platform-detail.h.patch`（+8/-0，`patch_type: portability`）
  —— `namespace std` 里的 `unique_ptr` 推导指引在 libc++ 下跳过。
- `patches/0002-test-test_sync.cpp.patch`（+5/-1，`patch_type: test-portability`）
  —— robust mutex 单测限定 glibc Linux。

两处补丁**均未引入 `__OHOS__` 等平台宏**（PF5 合规）：判据分别是 libc++ 的 `_LIBCPP_VERSION` 与 glibc 的 `__GLIBC__`。

## 依赖版本

- 无第三方依赖（`requirements()` 为空）。
- 系统库：`pthread`、`rt`（OHOS sysroot 提供；musl 下 librt 是空实现桩，`-lpthread -lrt` 实测链接通过）。

## 验证结果

```bash
# 1) 能力面探针（本机 B，2026-10-06 逐项实测）
shm_open POSIX            OK read=b'x'
/dev/shm isdir / W_OK /rw True / True / OK 'x'
memfd_create (libc)       fd=5 read=b'y'
eventfd / mmap ANON / sem_open   OK / OK b'ab' / OK
shmget (SysV)             rc=159 = Signal 31 SIGSYS 被杀   ❌
mq_open                   Symbol not found（musl 无 POSIX 消息队列） ❌

# 2) futex 能力探针（syscall(SYS_futex)=98）
FUTEX_WAKE            ret=0            ✅
FUTEX_WAIT            ret=-1 errno=11  ✅（值不匹配，符合预期）
FUTEX_LOCK_PI         ret=0            ✅
FUTEX_UNLOCK_PI       ret=0            ✅
FUTEX_CMP_REQUEUE_PI  ret=-1 errno=38 ENOSYS ❌
FUTEX_WAIT_REQUEUE_PI ret=-1 errno=38 ENOSYS ❌
FUTEX_TRYLOCK_PI      ret=-1 errno=38 ENOSYS ❌

# 3) 消费者探针（链接探索构建的 libipc.a）
[shm]  valid=1 size=4100 write/read 往返 OK
[mutex] open=1 lock=1 unlock=1
[chan]  connect/send=1 recv 返回 "ping"
PROBE_DONE   （stderr 有 fail condition broadcast[38] 噪声，但收发成功）

# 4) 上游测试套件（LIBIPC_BUILD_TESTS=ON，两个补丁后重编）
注册用例 27（--gtest_list_tests），逐例运行结果（明细：`~/tmp/uc2/cpp-ipc-1.3.0/each-test.log`，第二次独立跑 `~/tmp/uc2/cpp-ipc-1.3.0/each.log` 同读数、两份均为 SUMMARY pass=13 fail=6 crash=4 timeout=4）：
SUMMARY pass=13 fail=6 crash=4 timeout=4
  逐 suite（过/失败/崩溃/超时）：
  - IPC    7 例 = 2/4/1/0（过 basic_ssu、basic_mmb）
  - Queue  9 例 = 5/0/0/4（过 check_size、el_connection、connection、prod_cons_1v1_unicast、prod_cons_1vN_unicast）
  - SHM    5 例 = 5/0/0/0（POSIX shm 完全可用，与探针一致）
  - Sync   4 例 = 1/1/2/0（过 Semaphore；Mutex 断言失败；Condition、ConditionRobust 崩溃 abort）
  - Waiter 2 例 = 0/1/1/0（quit_waiting 断言失败；broadcast 崩溃 fail condition wait[38]）
  ⚠ Queue 的 4 个超时逐名：prod_cons_1v1_broadcast、prod_cons_1vN_broadcast、
    **prod_cons_NvN_unicast**、prod_cons_NvN_broadcast
    ⇒ 单播 3 例只过 2（prod_cons_NvN_unicast 也超时）、broadcast 3 例全超时；
      **不存在"单播路径全绿"**（本行前一版写成「单播 4 过 / 4 个 broadcast 超时」为归因失实，已按日志改回）
```

## 五维测试账（手册/04 §10.1，2026-10-06 本机复算）

| 维度 | 数值 | 来源与复现命令 |
|---|---|---|
| `N_static`（上游静态声明，同名去重） | **33** | `grep -c 'TEST(' test/*.cpp` 合计 **38** − 注释掉的 **4**（`test_mem.cpp` 块注释 2 + `// TEST(Memory, tc_alloc)` 1 + `//TEST(Thread, rw_lock)` 1）= 34 − 同名重复 **1**（`test_sync.cpp` 里 `TEST(PThread, Robust)` 在 Linux/Windows 两分支各一份）= **33** |
| `N_registered`（OHOS 实际注册） | **27** | `./bin/test-ipc --gtest_list_tests`（5 个 suite） |
| `N_executed`（实际执行） | **27** | 逐例 `--gtest_filter=<name>`，27/27 全部执行到终态 |
| 通过 | **13**（48.1%） | 同上，13 PASS / 6 FAIL / 4 CRASH / 4 TIMEOUT，13+6+4+4=27 |
| OHOS 未编译 | **6** | `33 − 27`：`Thread.*` 4（上游 `#if 0`）、`Platform.to_tchar` 1（上游 `#if _WIN32`）、`PThread.Robust` 1（补丁 0002 的 `__GLIBC__` 守卫） |
| 注释掉不计入 `N_static` | **4 字面量** | `Memory.static_alloc`、`Memory.pool_alloc`（`/* */`）、`Memory.tc_alloc`、`Thread.rw_lock`（`//`） |
| `N_consumer`（消费者测试） | **1** | `test_package/test.cpp`，**12 个 `CHECK` 断言**（复现 `grep -c '^[[:space:]]*CHECK(' test_package/test.cpp` = 12；另有 1 行 `#define CHECK` 不计），`conan create` 内 `1/1 Test #1: test_cpp_ipc Passed` |
| `N_runner` | **1** | gtest 主程序 `./bin/test-ipc`（runner 数不替代原子用例数） |

- 三处口径此前不一致（notes 写「11 例未编译」、MANIFEST 枚举 7、审计复算 33）——**以上表为唯一口径**，
  未编译=**6**（OHOS 口径），另有 4 个 `TEST(` 字面量在注释里、不属任何分母。
- **PR 正文不得拿 27 当 `N_static`**；两表分母按 手册/04 §10.1 写清「执行项 27/27、静态全量 13/33」。

## 报告时序与陈旧件申报（W4 P3-⑥/⑦ 逐条）

- **`reports/` 与配方 mtime**：`finish` 每轮 **Step1 `refresh-patch` 会无条件把 `manifest.yaml` 的
  `patch_classification` 重置为 `type: auto / guard: pending`**（`scripts/ohc/refresh_patch.py` 527-548 行，
  `re.sub(r'\npatch_classification:.*')` 后整体重写），我随后回填实质分类；
  **Step5 W3 的 mirror-fallback 会把 `conandata.yml` 的 URL 改写成 `gh-proxy.com` 列表**，
  且它的 EXIT 还原恢复的是"改写之后"的备份 ⇒ 运行后仍留 gh-proxy，我按 PF7（`preflight.py:357` 黑名单）手工恢复为官方单 URL。
  ⇒ 这两处**收尾回填必然晚于 `reports/`**，本条为**事前申报**：两处改动**只涉及 URL 形态与分类标注**，
  **不改 `sha256`、不改补丁内容、不改配方逻辑**，与 W3 校验时的源码身份一致
  （`ci/conan/build_and_test.sh` 归一化时剥掉镜像前缀再比对，URL 形态不参与源码身份）。
  **实测回填（finish5，2026-10-06）**：`manifest.yaml` Step1 重写于 `02:57:40`、`notes.md` Step2 于 `02:57:40`、
  `reports/conan-create.log` `02:57:47`、`reports/conan-verify-report.md` `02:57:50`、
  `conandata.yml` 的 W3 还原 `02:59:35.914` 与 `reports/w3-local-ci.log` `02:59:35.958` **同秒、且 reports 晚 44ms**
  ⇒ **finish 运行期间 reports 全部晚于当时的配方文件**；随后我只做上述两处收尾回填
  （恢复官方 URL + 回填 `patch_classification`），这两处即本条申报的对象。
  W3 `junk_check` 本轮口径：`检查模式: prdiff (13 个文件)`（`pr.diff` 重新生成，13/13 全覆盖）。
- **`reports/test-report.md` 是陈旧件、且 `finish` 刷不动它**：它**唯一**的生成点是构建驱动 Step7 `make check`
  （`scripts/ohc/driver.py:1063`），`finish` 只做存在性检查（`finish.py:66-74`、`365-370`）⇒ **重跑 `finish` 不会刷新它**。
  它现在内容 `Status: FAIL / RC: 2 / Log: ~/make-check-27880.log` 是**真实记录**：
  上游 CMake 没有 `check` 目标（`make: *** No rule to make target 'check'`），见"遇到的问题与解决方案"第 3 行。
  实际测试证据以本文件"五维测试账" + `test_package/MANIFEST.yml` + `~/tmp/uc2/cpp-ipc-1.3.0/each-test.log` 为准；
  `reports/` 被 `.gitignore` 忽略、不进 PR。**不手改该文件**（工具产物手写=P0 欺骗风险）。

## 注意事项

- **已知限制（如实申报）**：本包在 OHOS 上 POSIX 共享内存路径可用（`SHM.*` 5/5）；
  队列**单播 3 例只过 2** —— `Queue.prod_cons_NvN_unicast` 25s 超时，**加长到 180s 仍 `rc=124` 超时**，
  累计 **135 处 `test/test_queue.cpp:48` 断言 `n != PushRetry`（push 重试打满 1,000,000）**，
  而该用例日志里 **0 条** `fail condition broadcast/wait[38]` ⇒ **此例归因未取证，不并入 ENOSYS 结论**
  （复跑日志 `~/tmp/uc2/cpp-ipc-1.3.0/nvn_unicast.log`）。
  **依赖 futex PI-requeue 的跨进程条件广播/等待不可用**（内核 ENOSYS，探针 + 崩溃用例 stderr 实证），
  表现为 `fail condition broadcast[38]` / `fail condition wait[38]`，以及 `IPC.1vN`、`Sync.Condition`、
  `Sync.ConditionRobust`、`Waiter.broadcast` 四例 abort。
  这不是本配方引入的问题，也不在本次适配范围内修复（改 a0 并发层会改变语义）。
- **B判定=create**：机制 = 「HongMeng 内核未实现 `FUTEX_CMP_REQUEUE_PI`/`FUTEX_WAIT_REQUEUE_PI`/`FUTEX_TRYLOCK_PI`（ENOSYS），基础 `FUTEX_WAIT/WAKE/LOCK_PI/UNLOCK_PI` 可用 ⇒ 用 PI-requeue 实现的跨进程条件变量在 OHOS 上整体失效」，
  草稿 `knowledge/drafts/DRAFT-cpp-ipc-1.3.0-futex-requeue-pi-trylock-pi-enosys.{kv,md}`。
- **上游测试归因分寸（唯一口径，前一版「失败项全部归因到上述平台限制」失实已撤回）**：
  **13/27 = 48.1%**（逐例实测：13 过 + 6 失败 + 4 崩溃 + 4 超时 = 27）。
  - **有直接证据归因 ENOSYS**：4 例崩溃（stderr 带 `fail condition broadcast[38]`/`fail condition wait[38]`）——
    `IPC.1vN`、`Sync.Condition`、`Sync.ConditionRobust`、`Waiter.broadcast`；
    以及运行中持续打印同类错误串的用例（`fail condition broadcast[38]` 全程 50 次）。
  - **归因未取证、只记现象**：①`Sync.Mutex`（`lock.try_lock()` 未按预期抛 `std::system_error`；
    `a0_mtx_trylock` 只在 owner-died 恢复分支调 `FUTEX_TRYLOCK_PI`，本例是否走到该分支未验证）；
    ②4 例超时（`timeout` 分支无断言输出，其中 `Queue.prod_cons_NvN_unicast` 已用 180s 复跑排除"纯负载"，
    但日志 0 条 ENOSYS 串）。
  - ⛔ 禁止表述：「失败项全部归因到平台限制」「单播路径全绿」——两处均为前版失实，已按日志改回。
- `test_package/test.cpp` 是消费者视角的实质测试（shm 句柄创建/映射/读写 + 命名互斥锁 + 广播通道收发），
  `conan create` 内 **1/1 Test #1: test_cpp_ipc Passed**；它不依赖上面那条受限路径的超时语义。
---

**编译结束**: 2026-10-06 03:26
**最终状态**: built
