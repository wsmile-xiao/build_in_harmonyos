# 原生构建与测试记录 — wuffs 0.4.0-alpha.10

> 设备：OpenHarmony / HarmonyOS PC（aarch64）
> 工具链：`/data/service/hnp/bin/clang` 15.0.4（`aarch64-unknown-linux-ohos`）、
> `conan 2.29.1`、`GNU Make 4.4.1`
> 记录时间：2026-09-10

本文件记录**探索期**在任务私有源码副本上做的原生验证。配方内的同一批检查已在
`conan create` 中重跑（见 `reports/conan-create-log.md`）。

## 1. 上游形态确认

wuffs 对库本体没有构建系统（`BUILD.md`: `There's no build step`）。仓库提供了
`build-all.sh` 作为一致性检查脚本，但它需要 Go 工具链（`go install` / `go test` /
`wuffs gen`），而本设备与 CI 镜像均无 Go：

```
$ command -v go
(空)
```

因此原生验证取 `build-all.sh` 中不依赖 Go 的部分，并逐项保留上游原始命令与
flag。上游全量入口的缺口已在 `test_package/MANIFEST.yml` 的 `not_run` 段与
`notes.md` 第 3.4 节明确记录。

## 2. 单文件产物的编译一致性检查

上游 `build-all.sh` 的 4 条命令，warning 集原样照抄（`WARNING_FLAGS` +
C 附加项），对象换成本包安装的 `release/c/wuffs-v0.4.c`：

| # | 模式 | 编译器 / 标准 | 结果 |
| --- | --- | --- | --- |
| 1 | 头模式（无 `WUFFS_IMPLEMENTATION`） | clang `-std=c99 -Wc++-compat` | ✅ 0 warning |
| 2 | 实现模式（`-DWUFFS_IMPLEMENTATION`） | clang `-std=c99 -Wc++-compat` | ✅ 0 warning |
| 3 | 头模式 | clang++ `-std=c++11 -x c++` | ✅ 0 warning |
| 4 | 实现模式 | clang++ `-std=c++11 -x c++` | ✅ 0 warning（见下） |

**第 4 项的设备实测细节**：按上游原样 warning 集会报 8 条 `-Wc99-extensions`
错误，全部落在 aarch64/NEON 代码路径的 C99 复合字面量上：

```
release/c/wuffs-v0.4.c:35246:51: error: compound literals are a C99-specific
  feature [-Werror,-Wc99-extensions]
    v_v2 = vmlal_u16(v_v1, vget_low_u16(v_col2), ((uint16x4_t){16u, 15u, 14u, 13u}));
```

该路径由 `__ARM_NEON` 守卫（`release/c/wuffs-v0.4.c:154`），x86_64 上不会命中。
配方在 C++ 检查中**只**追加 `-Wno-c99-extensions` 一个开关，其余 `-Werror`
保持有效；随后 0 warning 通过。这是设备实测才能发现的一类差异，已在
`manifest.yaml`/`README.md`/PR 正文说明。

目标文件大小（`ls -la`）：`wuffs-v0.4.c` 3 625 906 B
（同目录 `wuffs-v0.3.c` 1 825 612 B、`wuffs-unsupported-snapshot.c` 3 625 807 B）。

## 3. 上游 C 测试套件（探索期基线）

30 个程序，按 `cmd/wuffs-c/test.go` 的方式编译运行：

```sh
for f in test/c/std/*.c; do
  clang -std=c99 -Wall -Werror "$f" -o <bin>/$(basename "$f" .c)
  (cd <wuffs-root> && <bin>/$(basename "$f" .c))
done
```

结果（设备实测，程序自报）：

| 程序 | 用例 | 程序 | 用例 | 程序 | 用例 |
| --- | --- | --- | --- | --- | --- |
| adler32 | 3 | gif | 45 | sha256 | 3 |
| bmp | 4 | gzip | 9 | targa | 2 |
| bzip2 | 7 | handsum | 6 | thumbhash | 4 |
| cbor | 4 | jpeg | 7 | vp8 | 5 |
| crc32 | 3 | json | 33 | wbmp | 8 |
| crc64 | 3 | lzip | 1 | webp | 3 |
| deflate | 19 | lzma | 4 | xxhash32 | 3 |
| etc2 | 3 | lzw | 11 | xxhash64 | 3 |
| | | netpbm | 4 | xz | 5 |
| | | nie | 5 | zlib | 10 |
| | | png | 12 | qoi | 3 |

- **TOTAL = 232，PASS = 232，FAIL = 0，SKIP = 0，NOT_RUN = 0**
- 30/30 程序 `FAILED_FILES=0`，退出码 0。
- 统计单位：上游 `testlib` 的测试过程（`g_tests[]` 元素），与上游打印
  `PASS (N tests)` 的口径相同。
- 源码静态计数（用 `clang -E` 真实预处理后解析 `g_tests[]`）：
  - `-DWUFFS_MIMIC` 定义时元素总数 **295**；
  - 其中位于 `#ifdef WUFFS_MIMIC` 内 —— **63** 个；
  - 未定义该宏（上游默认，即本包）时 **232** 个，逐文件与上表实测数字 30/30
    完全吻合。这不是跳过（见 `test_package/MANIFEST.yml`）。
  - 复算注意（两条陷阱，实测都踩过）：必须先按花括号配平把 `proc g_tests[] = { ... }`
    块文本取出来再预处理——整文件带 `-DWUFFS_MIMIC` 预处理在本仓这种无第三方库的
    树上有 10/30 个文件因缺 `bzlib.h`/`gif_lib.h`/`jpeglib.h`/`lzma.h`/`png.h`/
    `openssl/evp.h`/`webp/decode.h`/`xxhash.h` 直接失败；取出块后还要滤掉
    `# <line> "<file>"` linemarker，否则在实际触发该合并的 10 个文件上（`g_tests[]`
    内含 `#ifdef WUFFS_MIMIC` 分支的文件共 28 个，其中 10 个因此多计 1），
    `#endif` 回填的 linemarker 会与末尾 `NULL` 哨兵落进同一个逗号片段，使哨兵被
    计入（默认口径 232 → 242；带宏时 295 恒等）。
  - **勘误**：本文件早期版本把上述两个数字写成「242 个元素 / 10 个在 mimic 内」。
    已按真实预处理口径订正；W4 独立审计（`reports/audit-result.json`）以 P0
    记录该错误计数。

探索期用 `$TASK_DIR/run-c-tests.sh` 驱动，日志
`$TASK_DIR/c-tests-v0.4.log`（31 行：30 条 PASS 行 + 1 条汇总行）。

## 4. 上游端到端检查（build-all.sh 的第 3 组）

`build-all.sh` 会构建示例程序并与仓库内冻结的回归数据比对。示例程序自身
include 的是未版本化快照，因此先在其副本中把 include 改指 `wuffs-v0.4.c`
（与 30 个测试补丁同一改动），再按上游 `build-example.sh` 的 flag 构建：

```
Building (C++) gen/bin/example-crc32        Building (C)   gen/bin/example-mzcat
Building (C++) gen/bin/example-jsonptr      Building (C)   gen/bin/example-zcat
Building (C)   gen/bin/example-convert-to-nia
... （共 11 个示例程序，构建 rc=0）
```

实测结果：

| 检查 | 实测值 | 期望 | 结果 |
| --- | --- | --- | --- |
| `example-crc32 < test/data/json-things.formatted.json` | `cdcc7e35` | `cdcc7e35` | ✅ |
| `example-jsonptr < json-things.unformatted.json \| example-crc32` | `cdcc7e35` | `cdcc7e35` | ✅ |
| `print-nia-checksums.sh` vs `test/nia-checksums-of-data.txt` | 203 行 | 203 行 | ✅ diff 空（202 条数据 + 1 条表头） |
| `print-mzcat-checksums.sh` vs `test/mzcat-checksums-of-data.txt` | 35 行 | 35 行 | ✅ diff 空（34 条数据 + 1 条表头） |

对同一批数据也验证了 Python 复刻取数与上游 shell 脚本**逐字节一致**
（`diff rc=0`），因此配方内用 Python 实现同一比对是等价替换，不是放宽。
配方内这四项检查同样全绿（见 `reports/conan-create-log.md` 的
`golden regression OK` 两行与两个固定值检查）。

## 5. 补丁等价性验证

30 个补丁只改测试的 include 行。按第 5.3 节要求用 **patch_ng 库调用**（而非
`patch` CLI）复验：

```python
import glob, patch_ng
ok = 0
for f in sorted(glob.glob("patches/*.patch")):
    p = patch_ng.fromfile(f)
    assert p, f
    assert p.apply(strip=1, root="<pristine-tree>"), f
    ok += 1
# applied_ok=30
```

说明：`strip=1` 是本次人工复验使用的参数；**Conan 的
`apply_conandata_patches()` 未传 `strip` 时实际用 `strip=0`**
（`conan/tools/files/patches.py` 的 `patch(..., strip=0)`，且 `patch_ng` 的
`decode_clean` 已去掉 `a/`/`b/` 前缀）。两种 strip 实测都能成功应用，
本条结论不受影响；已在 `manifest.yaml` 的 `patch_generation` 中统一为
「Conan 实走 strip=0」口径。

随后 `diff -rq <pristine+patches> <exploration-tree>`：
**无输出**（逐字节一致）。即「补丁应用结果」与「实际跑出 232/232 的那棵树」
完全相同。

## 6. 鸿蒙/aarch64 平台专项测试（探索期）

外部评审 rule12 要求鸿蒙特有测试 ≥1。探索期先确认 wuffs 的平台相关面：其
`release/c/wuffs-v0.4.c` 在编译期按 CPU 架构选择代码路径，ARM 快速路径以
「小端序 + 可用非对齐访存」为前提。

探索验证（`$TASK_DIR/neon-probe/`）：

```
# 默认构建（aarch64）
$ clang -std=c99 -E ... | grep -cE 'vld1q_u8|vaddq_u32|vpadalq'   →  15   # 预处理输出命中
# 说明：该 15 是「预处理后文本里出现的次数」，其中一部分来自 arm_neon.h 的宏/内建
# 定义行而非 wuffs 自身的调用点，故只作粗判据。硬判据用 nm 的具体实现符号：
# 加 -DWUFFS_CONFIG__AVOID_CPU_ARCH
$ clang -std=c99 -E ... | grep -cE 'vld1q_u8|vaddq_u32|vpadalq'   →  0    # 架构特化已禁用
# 目标文件大小差异也印证代码路径不同：287584 B vs 272208 B
```

硬判据（对同一源文件的两次构建做目标文件符号对比）：

> 口径说明：下面的 `.o` 是**未优化的 `-O0` 目标文件**（本节专门用于符号可见性对照，
> 与上一段 `neon-probe` 的 287584/272208 B 是**另一组**产物，勿混用）。
> `-O1` 及以上编译器会内联/裁剪部分 `*_arm_neon` 实现，计数退化。实测各优化级别
> 的 `nm` 计数（`def_up`/`port_up` = `__(up|hasher__up)` 符号数；`def_neon`/`port_neon`
> = 含 `arm_neon` 的符号数）：

| 优化级别 | def_up | port_up | def_neon | port_neon |
| --- | --- | --- | --- | --- |
| `-O0` | 23 | 22 | 6 | 1 |
| `-O1` / `-O2` / `-O3` / `-Os` | 21 | 20 | 5 | 0 |

> 因此符号计数**只在 `-O0` 口径下**具有本文所述的判别力；运行期的
> `have_arm_neon()` 断言（`test_package` 实际执行、CI 日志可查的判据）不受优化级别影响。

```
$ nm def.o  | grep -oE 'wuffs_[a-z0-9_]+__(up|hasher__up)[a-z0-9_]*' | sort -u
wuffs_adler32__hasher__up
wuffs_adler32__hasher__up__choosy_default
wuffs_adler32__hasher__up_arm_neon              ← 仅默认构建存在
...
$ nm def.o  | grep -cE '__(up|hasher__up)'   →  23
$ nm port.o | grep -cE '__(up|hasher__up)'   →  22
$ nm def.o  | grep -c arm_neon               →   6    （含 filter_*_arm_neon 等实现）
$ nm port.o | grep -c arm_neon               →   1    （仅 have_arm_neon 探测函数）
```

即默认构建里确实**定义并链接了 `*_arm_neon` 实现**（`wuffs_adler32__hasher__up_arm_neon`、
`wuffs_png__decoder__filter_1_distance_4_arm_neon` 等），`AVOID_CPU_ARCH` 构建里这些
符号不存在、只剩 `*__choosy_default` 可移植实现——这比预处理命中计数硬得多。

另据实测：本构建的 OHOS clang 15 默认目标**未定义** `__ARM_FEATURE_CRC32`
（需 `-march=armv8-a+crc`），故 `have_arm_crc32()=0`、无 `*_arm_crc32` 实现符号，
CRC-32 走可移植实现；而 `__ARM_NEON`、`__ARM_FEATURE_UNALIGNED` 均已定义，
NEON 路径启用。

随后用同一源文件的两次构建做对照（`test_package/ohos_platform_test.c`），
设备实测两个构建各 32 项断言全过，且库自报所选路径分别为 1 / 0：

```
# build: default (aarch64 fast paths enabled)
# wuffs_base__cpu_arch__have_arm_neon()     = 1 (want 1)
OK: 32 checks passed, 0 failed
# build: portable (WUFFS_CONFIG__AVOID_CPU_ARCH): arch-specific code disabled
# wuffs_base__cpu_arch__have_arm_neon()     = 0 (want 0)
OK: 32 checks passed, 0 failed
```

关键断言之一是**非对齐输入**：把内嵌 PNG 放在故意错位的缓冲区里，从 16 个字节
偏移（0..15）各解码一次，每次都要求 `crc32(解码 RGB) == 0x6B64E606`。这正是
NEON 路径赖以成立的那条平台前提，纯可移植 C 测试无法覆盖它。

注：双 TU 方案（两个翻译单元各自定义 `WUFFS_IMPLEMENTATION` 并以
`WUFFS_CONFIG__STATIC_FUNCTIONS` 隔离）在此库上**不可行**——链接期仍有
`wuffs_aux::` 命名空间下的重复符号（"defined at" 冲突），故改用同一源文件的
两次独立构建（每个可执行文件仍是单 TU、单实现），既绕开该问题又保留了
「两条架构路径都真实执行」的证明力。

## 7. test_package 消费者（设备侧独立复现）

见 `reports/conan-verify-supplement.md` 第 3 节：在只含包内 `include/` 的独立目录
中编译三个翻译单元并链接运行，输出 `OK: 15 checks passed, 0 failed`；移除产物
后同名编译以退出码 1 失败，证明测试真实依赖被测包。

## 8. 未运行项

| 项目 | 原因 | 影响 |
| --- | --- | --- |
| `go install` / `go test github.com/google/wuffs/...` / `wuffs gen` | 设备与 CI 镜像均无 Go 工具链 | 属 Wuffs 语言工具链自身测试；本包不修改任何 `.wuffs` 源，转译结果与入库产物相同 |
| `wuffs test -mimic` / `build-fuzz.sh` | `-DWUFFS_MIMIC` 上游默认不编译，且需 giflib/libpng/libjpeg/libwebp/zlib 等未发布的第三方库 | 上游默认口径；该宏下的 **63** 个测试过程既不编译也不执行，非 mimic 的 232 用例全部执行 |

以上均不计入 232，也不写成 PASS。
