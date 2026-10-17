# DRAFT-ohos-sysv-shmget-sigsys：OHOS 沙箱拦截 SysV 共享内存（shmget 家族）

## 现象

编译全部通过，运行即被 SIGSYS 终止。shell 表现：

```text
Signal 31 (core dumped)
Bad system call (core dumped)
```

独立探针（仅调用 `shmget(IPC_PRIVATE,...)` + `shmctl(IPC_RMID)` 的 C 程序）：

```text
$ ./shmget_probe; echo exit=$?
Signal 31 / Bad system call
exit=159        # = 128 + 31 (SIGSYS)
```

## 根因

OHOS 沙箱/内核拦截 **SysV IPC 共享内存** syscall（`shmget`/`shmat`/`shmctl`）。
进程运行时收到 SIGSYS（signal 31）被终止（exit = 128+31 = 159）。
这是**运行时 syscall 拦截**而非编译问题——编译全部通过、运行即崩。

SysV 共享内存没有内建替代路径，但 **POSIX 共享内存**（`shm_open` +
`ftruncate` + `mmap(MAP_SHARED)` + `shm_unlink`）**不受拦截**，是功能等价的
替代通道。注意区分：E051 覆盖的是"未实现 syscall → 只能排除功能"
（setreuid/setregid/chroot 等无替代）；本模式是"SysV IPC 有 POSIX 等价通道
→ 应替换而非排除"，修复路径本质不同。

## 可复用修复模式

任何在 OHOS 上调用 SysV 共享内存的 C/C++ 工具/库（fuzzer、IPC 库、数据库等）：

1. **首选**：若上游自带 mmap 共享内存编译开关（如 AFL++ 的 `TEST_MMAP=1` →
   `-DUSEMMAP=1`），直接启用编译期开关（`fallback_approach:
   compile-time-mmap-switch`）。
2. **否则**：手工重写 `setup_shm()` / `remove_shm()`（`rec_approach:
   replace-sysv-shm-with-posix-shm`）：
   - `shm_open(名称, O_RDWR|O_CREAT|O_EXCL, 0600)`（名称形如 `/__afl_<pid>`）；
   - `ftruncate(fd, size)` 定长；
   - `mmap(NULL, size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0)` 得到共享指针；
   - 跨进程标识：**环境变量内容由 "shm ID 整数" 改为 "shm 名称字符串"**；
   - atexit 清理：`close(fd)` + `shm_unlink(名称)`。
3. **禁止**：试图用 signal handler 捕获被拦 syscall 的 SIGSYS（同 E051 教训，
   OHOS 对部分被拦 syscall 的 SIGSYS 不可捕获，方案无效）。
4. 验证：`nm -u <bin> | grep shmget` 应为空、`shm_open` 应存在（落盘验证，
   注意 make 按时间戳不重编的坑——需 `make -B` 或删除目标后重编）。

## 验证证据

**主证据（afl 1.35b，本团队 2026-09-02 鸿蒙 PC 实机）**：经典 afl 1.35b
（`shmget`/`shmat`/`shmctl` 硬编码于 afl-fuzz.c / afl-showmap.c / afl-tmin.c，
无 USEMMAP 选项）打补丁 0002-0004 改为 `shm_open+ftruncate+mmap+shm_unlink`
后，`conan create`（OHOS aarch64 / clang 15.0.4）通过，test_package 3/3：
afl-gotcpu / afl-showmap fork-exec / afl-fuzz -n dumb 模式均正常运行。

**交叉佐证（aflplusplus 4.33c 适配实机证据，经对方授权引用）**：

- 片段 A —— 运行时 SIGSYS（4.33c test-basic.sh 实机日志，USEMMAP 落盘前）：
  ```text
  [*] Testing: afl-clang-fast, afl-showmap, afl-fuzz, afl-cmin and afl-tmin
  [+] afl-clang-fast compilation succeeded
  Signal 31 (core dumped)            ← afl-showmap 执行插桩目标
  [!] afl-clang-fast instrumentation failed
  Signal 31 (core dumped)            ← 再次触发
  [!] afl-cmin did not correctly minimize the number of testcases (0)
  ../afl-cmin.bash: line 381: 16830 Bad system call (core dumped)
  ```
  出处：4.33c 适配留痕（`md汇总/留痕工作/aflplusplus/aflplusplus适配留痕.md` 坑 2）
  + test-basic.sh 实机日志。

- 片段 B —— 独立 shmget 探针（根因确认）：仅调用 `shmget`+`shmctl` 的独立
  测试程序运行报 `Signal 31 / Bad system call`，`exit=159`（128+31）。
  出处：4.33c 适配中隔离根因单独编译的 shmget 测试程序。

- 片段 C —— 修复后验证（USEMMAP 落盘）：`nm -u afl-showmap | grep -E 'shmget|shm_open'`
  → `U shm_open`（shmget 消失）。出处：4.33c manifest.yaml（TEST_MMAP=1 → USEMMAP）。

**结论**：同一根因（OHOS 拦截 SysV shmget 家族）在两个不同代码族上独立验证：
AFL++ 走编译期 `USEMMAP` 开关（内建 mmap 路径），经典 afl 1.35b 无该开关故
手工重写 `setup_shm`——两条修复路径共同指向同一 POSIX 通道（shm_open+mmap）。
跨库通用性由"fuzzer 家族双代码族 + 独立探针"三重证据支撑。

## 查重结论

- **E051**（SIGSYS/signal 31 家族）：根因为"未实现 syscall → 排除功能"
  （setreuid/setregid/chroot/clock_settime，无替代只能跳过）；本条目为
  "SysV IPC 被拦但有 POSIX 等价通道 → 替换而非排除"。修复路径本质不同，
  E051 未覆盖 SysV IPC 共享内存成员（已读 E051.kv 全文对比）。
- **E022**（POSIX 信号量 sem_unlink /dev/shm，python 警告）：POSIX 信号量
  与 SysV 共享内存不同通道，根因不同。
- **E220**（perl Configure 探测 IPC/SysV）：配置期探测，非运行时拦截。
- index.tsv 全量 grep（shm/shared/ipc/sysv）+ knowledge/drafts/ 目录：
  无 SysV 共享内存运行拦截相关条目。
- 盲区声明：以上基于本地已合并知识（本地 main + 本分支），无法保证全宇宙
  无人提交过同主题草稿；已与 aflplusplus-4.33c 会话交叉确认边界
  （对方 DRAFT-aflplusplus-ohos-posix-types 为编译期 musl 传递包含问题，
  与本条 runtime 拦截问题不重复）。
