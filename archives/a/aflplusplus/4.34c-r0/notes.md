# AFLplusplus 4.34c-r0 鸿蒙 PC 适配笔记

> 基于 4.33c（PR !5711，已合入 main）同代码族升级适配。
> 详细差异分析见 `md汇总/留痕工作/aflplusplus/aflplusplus-4.34c差异分析.md`。

## 与 4.33c 的差异（本次适配核心）

| 差异点 | 4.33c | 4.34c | 对配方的影响 |
|--------|-------|-------|-------------|
| `include/forkserver.h` 头部 | stdio/stdbool → types.h | 新增 `<string.h>`/`<unistd.h>` | 补丁 0001 **重打**（sys/types.h 插入点不变，上下文更新） |
| `include/sharedmem.h` 头部 | types.h | 新增 `<unistd.h>` | 补丁 0002 **重打** |
| `afl-cmin.py` | — | Worker 前新增 JobDispatcher 类；其余结构不变 | 补丁 0003/0004/0005 **原样复用**（git apply --check 通过） |
| LLVM 支持范围 | 21- | 22-（`LLVM_UNSUPPORTED` 改 `^2[3-9]\.`） | OHOS LLVM 15.0.4 仍在支持范围，无影响 |
| 新增文件 | — | IJON 插桩（afl-llvm-ijon-pass.so）、ZMQ mutator、src/Makefile | 不纳入配方（保持与 4.33c 的 10-pass 体系一致） |
| unicorn 构建 | build_unicorn_support.sh | build_unicorn_support.py | 配方不编 unicorn，无影响 |
| 核心工具 PROGS | 5 个 | 5 个（逐字符一致） | 无 |
| test_package 断言 | VERSION/MAP_SIZE/u8/u32/u64 | 兼容（VERSION="++4.34c"、MAP_SIZE=1<<16） | test_afl.c 原样 |
| cmocka 测试源 | 5 文件 | 5 文件（未变） | 测试指令原样 |

## 构建策略（与 4.33c 相同）

- **Makefile-based**: GNUmakefile + GNUmakefile.llvm，无 autotools/cmake
- **核心工具**: afl-fuzz, afl-showmap, afl-tmin, afl-gotcpu, afl-analyze
- **LLVM 插桩**: afl-cc + 10 个 .so pass + afl-compiler-rt.o（OHOS 自带 LLVM 15.0.4）
- **跳过 GCC plugin / LTO / IJON**: 与 4.33c 决策一致
- **NO_PYTHON=1 / SYS=Linux / TEST_MMAP=1**: 沿用 4.33c

## 平台适配问题（与 4.33c 相同的 5 类，补丁已按 4.34c 重打/复用）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | `unknown type name 'uid_t'/'pid_t'/'mode_t'` | OHOS musl 不传递包含 `<sys/types.h>` | 补丁 0001/0002（重打） |
| 2 | 运行时 `Signal 31`(SIGSYS) | OHOS 沙箱拦 SysV 共享内存(shmget) | TEST_MMAP=1 强制 USEMMAP（core tools 与 LLVM runtime 两者都要验证落盘） |
| 3 | afl-cmin.py `file_index_type_code=None` | multiprocessing spawn 重导重置全局 | 补丁 0003（原样） |
| 4 | afl-cmin.py `afl_showmap_bin=None` | 同上 | 补丁 0004（原样） |
| 5 | afl-cmin.py Pool 永久死锁 | OHOS Python 3.12 默认 spawn，worker 重 import 失败 | 补丁 0005 强制 fork（原样） |

## 版本号说明（R37）

- `4.34c-r0`：首次适配 4.34c，与分支名 `feat/aflplusplus-4.34c-r0` 一致
- 上游 tag 为 `v4.34c`（带 v 前缀）

## 验证状态

- [ ] 鸿蒙 PC conan create（塞源码 → 编译 → test_package）
- [ ] cmocka 单元测试（make -f GNUmakefile unit）
- [ ] test-basic.sh / test-llvm.sh
- [ ] USEMMAP 落盘（nm -u 验证 shm_open）
- [ ] manifest.yaml test_results 回填

## 运行环境要求

- 用户运行时需 `export AFL_TMPDIR=$HOME/tmp`（/tmp 只读，E002）
- AFL_PATH 已通过 runenv_info 指向 package 的 lib/afl
