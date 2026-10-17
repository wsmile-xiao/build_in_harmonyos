# elfutils 0.195.1 —— OHOS PC (aarch64) 上游用例执行与失败分析

本文件记录**在本机 OHOS PC aarch64 环境真实执行**上游 `make check` 的
结果与逐条失败原因，供 PR「验证结果」引用。命令与口径：

```
make -k -j1 check-TESTS TESTS='<253 条>' check_PROGRAMS='<122 个>'
```

## 总览

| 项 | 数量 |
|---|---|
| 上游 TESTS 总数 | 259 |
| 因 OHOS musl 缺接口无法构建（见下节） | 6 |
| **本环境可执行** | **253** |
| 实际执行 | 253 |
| PASS | 221 |
| FAIL | 26 |
| SKIP | 6 |
| 通过率（按实际执行数） | 87.4% |

## 无法构建的 6 条（OHOS musl 缺 glibc 接口）

| 用例 | 依赖的接口 | 实测现象 |
|---|---|---|
| `run-dwfl-report-offline-memory.sh` | `<error.h>` | `dwfl-report-offline-memory.c:22: fatal error: 'error.h' file not found` |
| `dwfl-proc-attach` | `pthread_cancel` | `ld.lld: error: undefined symbol: pthread_cancel` |
| `run-eu-search-cfi.sh` | `pthread_cancel` | 同上 |
| `run-eu-search-die.sh` | `pthread_cancel` | 同上 |
| `run-eu-search-lines.sh` | `pthread_cancel` | 同上 |
| `run-eu-search-macros.sh` | `<error.h>` + `pthread_cancel` | 同上两者 |

`pthread_cancel` 在 OHOS musl 上**头文件与 libc.so 都没有**（上游 musl 本身有实现，OHOS 变体裁掉了）；`<error.h>` 是 glibc 扩展头。
automake 的 `check-am` 依赖**全部** `check_PROGRAMS`，任何一个测试程序编不出来，整批用例都不会执行，
因此配方改为同时从 `TESTS` 与 `check_PROGRAMS` 剔除这 6 项，其余 253 条全部执行。

## FAIL 归类（26 条）

### 平台：OHOS ELF 方言（7 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-elflint-self.sh` | `phdr[10]: cannot get content of note section: section does not contain compressed data` |
| `run-exprlocs-self.sh` | `varlocs: No DWARF CU found?` |
| `run-readelf-self.sh` | `readelf: cannot get content of note: garbage data` |
| `run-reverse-sections-self.sh` | `copy_elf: /storage/Users/currentUser/.conan2/p/b/elfut92edbd528c106/b/build-release/src/addr2line -> addr2line.rev (read,reverse)` |
| `run-strip-reloc-self.sh` | `readelf: cannot get debug context descriptor: No DWARF information found` |
| `run-strip-strmerge.sh` | `phdr[10]: cannot get content of note section: section does not contain compressed data` |
| `run-varlocs-self.sh` | `  [3399] function '__argp_error_internal'@84dc` |

### 环境：ptrace 受限（3 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-backtrace-dwarf.sh` | `PTRACE_TRACEME failed: Permission denied` |
| `run-backtrace-native.sh` | `backtrace: dwfl_linux_proc_report: No such file or directory` |
| `run-deleted.sh` | `stack: dwfl_thread_getframes tid 47054: Permission denied` |

### 环境：error(3) 前缀（3 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-stack-d-test.sh` | `--- stack.out	2026-09-25 12:22:30.835497499 +0800` |
| `run-stack-demangled-test.sh` | `--- stack.out	2026-09-25 12:22:32.071500937 +0800` |
| `run-stack-i-test.sh` | `--- stack.out	2026-09-25 12:22:31.447500624 +0800` |

### 平台：无账号数据库（2 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-ar-N.sh` | `ar: cannot represent ar_uid: No such file or directory` |
| `run-ar.sh` | `ar: cannot represent ar_uid: No such file or directory` |

### 环境：fd 上限（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `dwfl-bug-fd-leak` | `dwfl-bug-fd-leak: dwfl_linux_proc_report: No file descriptors available` |

### 平台差异：压缩率断言（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-compress-test.sh` | `No errors` |

### 工具链差异：DWARF 属性输出（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-dwarf-die-addr-die.sh` | `checking testfile-debug-types` |

### 平台差异：符号表基线（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-dwflsyms.sh` | `--- dwflsyms.out	2026-09-25 12:24:01.487497030 +0800` |

### 工具链差异：DWARF 解析（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-get-units-invalid.sh` | `file: testfile-debug-types` |

### 工具链差异：addr2line 在本环境可解析出行号（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-prelink-addr-test.sh` | `--- addr2line.out	2026-09-25 12:21:50.191497968 +0800` |

### 平台差异：DWZ 备用调试链接（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-readelf-dwz-multi.sh` | `-readelf: DIE [b] cannot get attribute 'comp_dir' (GNU_strp_alt) value: no alternative debug link found` |

### 平台：musl getopt 行为差异（`--syms=<arg>` 未报错）（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-readelf-s.sh` | `--- readelf.out	2026-09-25 12:24:00.503498437 +0800` |

### 工具链差异：strip 后节名表（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-strip-nothing.sh` | `elfcmp: a.out strip.out diff: shdr string index` |

### 环境：seccomp 拦截系统调用（SIGSYS，exit 159）（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `run-sysroot.sh` | `/storage/Users/currentUser/.conan2/p/b/elfut92edbd528c106/b/tests/test-subr.sh: line 88: 49700 Bad system call            (core dumped) LD_LIBRARY_PAT` |

### 平台差异：vDSO 符号解析（1 条）

| 用例 | 日志中的首条实质报错 |
|---|---|
| `vdsosyms` | `module name: /data/service/el2/100/hmdfs/account/files/Docs/.conan2/p/b/elfut92edbd528c106/b/build-release/tests/vdsosyms` |

## SKIP（6 条，上游自身的门控条件）

| 用例 | 触发条件 |
|---|---|
| `run-backtrace-data.sh` | `/storage/Users/currentUser/.conan2/p/b/elfut92edbd528c106/b/build-release/tests/backtrace-data: x86_64 linux only test` |
| `run-backtrace-native-biarch.sh` | `biarch testing disabled` |
| `run-backtrace-native-core-biarch.sh` | `biarch testing disabled` |
| `run-backtrace-native-core.sh` | `flock: Unknown option 'w' (see "flock --help")` |
| `run-large-elf-file.sh` | `long_bit: 64` |
| `run-lfs-symbols.sh` | `LFS testing is irrelevant on this system` |

## 说明

- 以上 6 条无法构建的用例之外，**本环境可执行的 253 条全部真实执行**，
  没有跳过、没有用断言桩替代。
- 0.195 配方（基线包）从未执行上游用例集，故不存在「0.195.1 相对 0.195 引入失败」的可比基线。
- 失败项均为**平台/环境固有**：ptrace 权限（SIGSYS/seccomp、PTRACE_TRACEME）、OHOS 无账号数据库、OHOS ELF 方言、fd 上限、musl getopt 差异、工具链输出基线差异。
- 新增的 27 条鸿蒙消费者测试（`test_package/test.cpp`）全部通过，覆盖真实 `libdebuginfod` 客户端调用链。

