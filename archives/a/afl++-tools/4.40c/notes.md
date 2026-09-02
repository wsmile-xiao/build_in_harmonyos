# afl-tools 4.40c 鸿蒙 PC 适配笔记

> 软件级包名 `afl-tools`（目录 `afl++-tools`，Conan 包名禁止 `++`）。
> 基于 aflplusplus 4.33c（PR !5711 已合入 main）/ 4.34c-r0 适配经验，跨 2 个 minor 升级。
> 详细差异分析见 `md汇总/留痕工作/afl-tools/aflplusplus-4.40c差异分析.md`。

## 与 4.33c 的差异（本次适配核心）

| 差异点 | 4.33c | 4.40c | 对配方的影响 |
|--------|-------|-------|-------------|
| **PROGS** | 5 个（无 afl-cmin） | **6 个：新增 afl-cmin**（make 目标 = `cp -f afl-cmin.py afl-cmin`，仍是 Python 实现） | 配方 PROGS 加 `afl-cmin` |
| **SH_PROGS** | 含 afl-cmin | `afl-cmin` → **`afl-cmin.awk`**（根目录不再有 afl-cmin 文件） | 配方 SH_PROGS 换 `afl-cmin.awk` |
| afl-cmin C 重写 | 无 | `src/afl-cmin.c`（60KB）存在但 **make 规则被注释封印**（未启用） | 不纳入配方；若上游后续启用需重评估 |
| `include/forkserver.h` 头部 | stdio/stdbool → types.h | 新增 `<fcntl.h>`（provides mode_t）/stdio/string/unistd | 补丁 0001 **重打**（仍无 sys/types.h） |
| `include/sharedmem.h` 头部 | types.h | 新增 `<unistd.h>` | 补丁 0002 **重打** |
| `afl-cmin.py` | Worker 仅 5 参 | **重构**：Worker.__init__ 参数化传入 file_index_type_code/tuple_index_type_code/afl_showmap_bin；logger=logging.getLogger(__name__) 模块级；`if __name__ == "__main__"` guard 已加 | **补丁 0003/0004 已过时删除**（上游已修） |
| `afl-cmin.py` fork | 无 | 仍无 `set_start_method("fork")` | 补丁 0005 **重打**（import 块插 random，上下文微调） |
| shmget 检测 | 无 | **新增编译期自动检测**（SHMAT_OK，L308） | 编译期测不出 OHOS 运行时 SIGSYS → **TEST_MMAP=1 必须保留** |
| LLVM 支持范围 | 21- | 22-（`LLVM_TOO_NEW_DEFAULT=22`） | OHOS LLVM 15.0.4 仍在支持范围，12 个配方目标全部存在 |
| 新增文件 | — | afl-llvm-ijon-pass.so、src/afl-fuzz-coverage.c、src/afl-fuzz-frameshift.c、custom_mutators 大量新增 | IJON 不纳入（与 4.33c 的 10-pass 体系一致）；fuzz 新模块被 wildcard 自动纳入 |
| 根目录 config.h/types.h | 无 | 新增（复制 include/） | 无影响（配方用 include/ 路径） |
| cmocka 测试源 | 5 文件 | 5 文件（test/unittests/unit_*.c 未变，14 断言） | 测试指令原样 |
| test_package 断言 | VERSION/MAP_SIZE/u8/u32/u64 | 兼容（VERSION="++4.40c"、MAP_SIZE=1<<16） | test_afl.c 原样 |

## 构建策略（与 4.33c 相同）

- **Makefile-based**: GNUmakefile + GNUmakefile.llvm，无 autotools/cmake
- **核心工具**: afl-fuzz, afl-showmap, afl-tmin, afl-gotcpu, afl-analyze, afl-cmin（6 个）
- **LLVM 插桩**: afl-cc + 10 个 .so pass + afl-compiler-rt.o（OHOS 自带 LLVM 15.0.4）
- **跳过 GCC plugin / LTO / IJON**: 与 4.33c 决策一致
- **NO_PYTHON=1 / SYS=Linux / TEST_MMAP=1**: 沿用 4.33c

## 平台适配问题（补丁已按 4.40c 重打/删除）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | `unknown type name 'uid_t'/'pid_t'/'mode_t'` | OHOS musl 不传递包含 `<sys/types.h>` | 补丁 0001/0002（重打） |
| 2 | 运行时 `Signal 31`(SIGSYS) | OHOS 沙箱拦 SysV 共享内存(shmget) | TEST_MMAP=1 强制 USEMMAP（4.40c 编译期自动检测测不出运行时拦截） |
| 3 | afl-cmin.py Pool 永久死锁 | OHOS Python 3.12 默认 spawn，worker 重 import 失败 | 补丁 0005 强制 fork（重打） |
| — | afl-cmin.py 全局变量/logger | — | **上游已修**（0003/0004 删除，见差异分析 §四） |

## 版本号说明（R37）

- `4.40c`：首次适配（与分支名 `feat/afl-tools-4.40c` 一致，用户确认）
- 上游 tag 为 `v4.40c`（带 v 前缀）；SHA256 `3343796f0b69b0bec07e44033608280c360e0e90b4ddb6bdda263d598fc3e472`

## 验证状态

- [ ] 鸿蒙 PC conan create（塞源码 → 编译 → test_package）
- [ ] cmocka 单元测试（make -f GNUmakefile unit）
- [ ] test-basic.sh / test-llvm.sh
- [ ] afl-cmin（PROGS 新成员，cp 产物）可执行
- [ ] USEMMAP 落盘（nm -u 验证 shm_open）
- [ ] manifest.yaml test_results 回填

## 运行环境要求

- 用户运行时需 `export AFL_TMPDIR=$HOME/tmp`（/tmp 只读，E002）
- AFL_PATH 已通过 runenv_info 指向 package 的 lib/afl
