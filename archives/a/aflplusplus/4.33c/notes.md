# AFLplusplus 4.33c 鸿蒙 PC 适配笔记

## 构建策略

- **Makefile-based**: 使用 GNUmakefile + GNUmakefile.llvm 直接构建，无 autotools/cmake
- **核心工具**: afl-fuzz, afl-showmap, afl-tmin, afl-gotcpu, afl-analyze
- **LLVM 插桩模式**: afl-cc + 10 个 .so pass + afl-compiler-rt.o（OHOS 自带 LLVM 15.0.4）
- **跳过 GCC plugin**: OHOS 用 clang 无 gcc-plugin-dev
- **跳过 LTO**: 需 LLD，未纳入（可选）
- **NO_PYTHON=1**: CI 无 python3-config，禁用 Python 绑定
- **SYS=Linux**: 覆盖 uname 检测，获得 Linux 链接标志
- **TEST_MMAP=1**: OHOS 沙箱拦截 SysV shmget(SIGSYS)，强制 mmap 共享内存

## 平台适配问题与修复（5 类）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | `unknown type name 'uid_t'/'pid_t'/'mode_t'` | OHOS musl 不传递包含 `<sys/types.h>` | 补丁 0001/0002 加 include |
| 2 | 运行时 `Signal 31`(SIGSYS) | OHOS 沙箱拦 SysV 共享内存(shmget) | TEST_MMAP=1 强制 USEMMAP（必须同时作用于 **core tools 与 LLVM runtime** 两者） |
| 3 | afl-cmin.py `file_index_type_code=None` | multiprocessing spawn 重导重置全局 | 补丁 0003 传参给 Worker |
| 4 | afl-cmin.py `afl_showmap_bin=None` | 同上 spawn 全局变量问题 | 补丁 0004 模块级初始化 |
| 5 | afl-cmin.py Pool **永久死锁**（worker 全崩、主进程 0 CPU 挂起） | OHOS Python 3.12 默认 **spawn** 启动方式，worker 重 import 主模块失败（`__main__` 变 BuiltinImporter），`pool.map()` 永远等不到结果 | 补丁 0005 强制 `set_start_method("fork")`（fork 不重 import，worker 直接继承内存） |

## 关键决策

| 决策 | 原因 |
|------|------|
| 自定义 package() 而非 make install | make install 尝试安装所有产物，未构建组件会导致失败 |
| LLVM 模式用 `-k` + `ignore_errors` | LLVM 缺失时核心工具仍可构建打包，优雅降级 |
| 不补丁 GNUmakefile | 平台差异通过 make 变量覆盖（SYS/TEST_MMAP/NO_PYTHON） |
| AFL_PATH 指向 package lib/afl | afl-cc 运行时定位 pass 插件 + runtime .o |
| 补丁 0003/0004/0005 修 afl-cmin.py | OHOS Python 3.12 默认 spawn：0003/0004 修 worker 重导后全局变量被重置；0005 更彻底——强制 fork 启动方式，直接避免重导 |

## 验证结果（鸿蒙 PC 实机，2026-08-21 复验）

| 验证项 | 结果 |
|--------|------|
| 核心工具编译（5 个）+ LLVM 插桩（10 pass） | ✅ |
| test_package | ✅ 5/5 |
| **cmocka 单元测试** | ✅ **14/14**（unit_maybe_alloc 6 + unit_preallocable 2 + unit_list 3 + unit_rand 2 + unit_hash 1） |
| **test-basic.sh** | ✅ **全部通过**（afl-clang-fast/afl-fuzz/afl-cmin.py/afl-cmin.bash/afl-tmin/afl-showmap） |
| **test-llvm.sh** | ✅ **全部通过**（threadsafe/dlopen/hardened/laf-intel/floating/cmplog/persistent） |
| USEMMAP 落盘验证 | ✅ `nm -u` 确认 afl-showmap/afl-fuzz/afl-compiler-rt.o 均链 `shm_open`（无 shmget） |

**未执行**（依赖缺失，有 `not found` 证据）：
- test-gcc-plugin.sh（需 GCC）
- test-qemu-mode.sh（需 QEMU）
- test-frida-mode.sh（需 Frida）
- test-nyx-mode.sh（需 NYX）
- test-unicorn-mode.sh（需 UniCorn）

## 关键踩坑

1. **afl-cc LLVM 检测**：`find_object()` 只认 `cmplog-routines-pass.so` 判定 `have_llvm=1`，缺它则所有 afl-clang-fast 报 "LLVM mode is not available"。必须构建完整 cmplog 系列 pass。

2. **OHOS 沙箱 SIGSYS**：`shmget`(SysV 共享内存) 在 OHOS 运行时被拦（编译能过、运行报 Signal 31）。AFL++ 有 USEMMAP 模式（mmap 替代），`TEST_MMAP=1` 强制启用后 fuzzing 真正跑起来。**坑中坑**：`-DUSEMMAP` 是编译期宏，而 make 按时间戳判断重编——若某次不带 TEST_MMAP 编过，之后再 `make TEST_MMAP=1` 会因 "up to date" 静默跳过，USEMMAP 始终没进二进制。必须 `make -B` 或删目标后强制重编，并用 `nm -u` 验证（core tools 与 afl-compiler-rt.o 都要看）。

3. **Python 3.12 multiprocessing spawn（根因）**：OHOS Python 默认 **spawn** 而非 Linux 惯例的 fork。spawn worker 需重 import 主模块，OHOS 上失败 → `__main__` 变 `BuiltinImporter` → worker 全崩 → `Pool.map()` 永久挂起（主进程 0 CPU）。afl-cmin.py 三个症状（file_index_type_code/afl_showmap_bin/logger 为 None）是重导重置；补丁 0003/0004 修症状，补丁 0005 强制 `set_start_method("fork")` 从根上避免重导。

## 运行环境要求

- 用户运行时需 `export AFL_TMPDIR=$HOME/tmp`（/tmp 只读，E002）
- AFL_PATH 已通过 runenv_info 指向 package 的 lib/afl
