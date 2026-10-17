# lambda-align2 2.0.1 适配笔记（HarmonyOS PC / OHOS 6.0 aarch64）

## 1. 上游与产物

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/seqan/lambda |
| 版本 / tag | 2.0.1 / `lambda-v2.0.1` |
| 许可证 | AGPL-3.0-or-later（`LICENSE.rst`/`LICENSE-AGPL3.rst`，部分组件 BSD：`LICENSE-BSD.rst`） |
| 构建系统 | CMake（顶层 `CMakeLists.txt` + `src/CMakeLists.txt`） |
| 产物 | 单二进制 `bin/lambda2`，子命令 `mkindexp` `mkindexn` `searchp` `searchn`（蛋白/核苷酸建索引与检索） |
| 依赖 | SeqAn 2.x（header-only，上游 git 子模块 `include/seqan`）、zlib、BZip2、OpenMP（可选） |

## 2. 构建环境与配置

- 编译器：OHOS SDK `aarch64-unknown-linux-ohos-clang` / `clang++`（15.x）
- sysroot：`/root/ohpc/sdk/ohos-6.0/native/sysroot`；工具链：`native/build/cmake/ohos.toolchain.cmake`
- CMake 构建类型：Release；`-DOHOS_ARCH=arm64-v8a`
- 关键开关：
  - `-DLAMBDA_LEGACY_PATHS=1`：2.x 默认只保留 FM 索引（`--db-index-type fm|bifm`），打开后额外支持 1.x 的后缀数组索引（`sa`），便于兼容旧索引并使上游 tests 的 `sa` 用例可执行。
  - `-DSeqAn_DIR=<src>/include/seqan/share/cmake/seqan`
  - 依赖：`zlib/1.3.1`、`bzip2/1.0.8`（conan），并预设 `ZLIB_*`/`BZIP2_*` 缓存变量指向依赖真实路径
- 与 x86_64 参考构建对齐的默认值：`LAMBDA_NATIVE_BUILD=OFF`、`LAMBDA_FASTBUILD=OFF`、`LAMBDA_MMAPPED_DB=OFF`、`LAMBDA_MULTIOPT_BUILD=OFF`、`LAMBDA_STATIC_BUILD=OFF`、`LAMBDA_LINGAPS_OPT=OFF`、`LAMBDA_LONG_PROTEIN_SUBJ_SEQS=OFF`、`LAMBDA_COMPILE_THREADS=1`（不加 `-flto`）。
- **OpenMP 关闭**（`-DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE`）：
  - OHOS SDK 自带 `libomp.so`（`native/llvm/lib/aarch64-linux-ohos/`），CMake 会自动启用 `-fopenmp=libomp`；但该运行库**不在目标设备镜像与本地 musl 运行根中**，实测运行产物时报 `Error relocating ../bin/lambda2: __kmpc_for_static_fini: symbol not found` 等 20 余条重定位错误，连 man 页生成都无法完成；
  - x86_64 参考构建（`expected.md5` 来源）本身未检测到 OpenMP（`OpenMP_CXX_FLAGS=NOTFOUND`），关闭后目标构建与参考构建在并行维度上一致，期望值逐字节可比、结果确定性更好；
  - 代价：产物为单线程（上游会打印 "Lambda will be built without multi-threading!" 警告），`-t` 参数不影响并行度。需要多线程时可在有 `libomp.so` 的环境中把该开关改为 `FALSE` 重新构建。
- `LAMBDA_LEGACY_PATHS=1` 作为**编译宏**注入（上游 CMake 无对应 option，`src/mkindex_options.hpp`/`search_options.hpp`/`search.hpp` 用 `#ifdef` 判断），打开后 `--db-index-type` 才接受 1.x 的 `sa` 类型。

构建命令（配方内为裸 cmake + 自发现 ohos.toolchain，绕开 `os=OHOS` 下 conan_toolchain 的 `CMAKE_SYSTEM_NAME` 映射问题）：

```bash
cmake -B build-ohos -S <src> \
  -DCMAKE_TOOLCHAIN_FILE=<sdk>/native/build/cmake/ohos.toolchain.cmake -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_BUILD_TYPE=Release -DLAMBDA_LEGACY_PATHS=1 \
  -DSeqAn_DIR=<src>/include/seqan/share/cmake/seqan \
  -DZLIB_INCLUDE_DIR=... -DZLIB_LIBRARY=... -DBZIP2_INCLUDE_DIR=... -DBZIP2_LIBRARIES=... \
  -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=<build>/ohos-find-deps.cmake \
  -DCMAKE_CROSSCOMPILING_EMULATOR=<qemu wrapper>
cmake --build build-ohos --parallel
```

## 3. 依赖处理

1. **SeqAn 2.x 内嵌**：上游 `.gitmodules` 把 `include/seqan` 作为子模块挂载，但 GitHub tag 归档不含子模块内容（官方 Debian/Ubuntu 用 `libseqan2-dev` 顶替）。配方内嵌官方 `seqan-library-2.4.0.tar.xz`（sha256 见 `conandata.yml`），按上游预期布局展开到 `<src>/include/seqan/`（`include/seqan/**` + `share/cmake/seqan/seqan-config.cmake`），并以 `-DSeqAn_DIR` 指定。
2. **zlib / bzip2**：上游对 `*.gz`/`*.bz2` 的库/查询/输出以及 SAM/BAM(BGZF) 输出都依赖二者。交叉链下 `ohos.toolchain.cmake` 用普通 `set()` 把 `CMAKE_FIND_ROOT_PATH_MODE_*` 设为 `ONLY`（命令行 `-D` 压不住），因此在 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 前置脚本里放开为 `BOTH` 并把依赖 package 目录加入 `CMAKE_FIND_ROOT_PATH`/`CMAKE_PREFIX_PATH`，同时预设 `ZLIB_INCLUDE_DIR`/`ZLIB_LIBRARY`/`BZIP2_INCLUDE_DIR`/`BZIP2_LIBRARIES` 等缓存变量。SeqAn 的 `seqan-config.cmake` 内部也会 `find_package(ZLIB)`/`find_package(BZip2)`（`SEQAN_HAS_ZLIB`/`SEQAN_HAS_BZIP2`），复用同一套变量。
3. **OHOS 交叉链兜底**：`llvm-ranlib` 兜底（SDK 只提供 `llvm-ar`）、产物代码签名（OHOS 上被 exec 的 ELF 未签名会 E077/E083）。

## 4. 问题与解决（全部有实测证据）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 交叉构建时 man 页生成失败/无产物 | `src/CMakeLists.txt` 的 5 条 `add_custom_command` 直接执行 `lambda2 --export-help=man`，交叉构建无法运行目标二进制 | 补丁 `0001-cmake-manpages-use-cross-emulator.patch`：改为 `${CMAKE_CROSSCOMPILING_EMULATOR} $<TARGET_FILE:lambda2>`（原生构建行为不变，已实测生成 `lambda2.1` + 4 个子命令 man 页） |
| 2 | 上游 `tests/` 无法直接使用 | `tests/` 与 v1.9.5 **逐字节相同**（1.x 遗留）：调用 1.x 的 `bin/lambda`/`bin/lambda_indexer` 与 `-d/-di/-p` 选项；用 `openssl md5 *` 对 1.x 平铺索引（`db.fasta.<alph>.sa.sa`、`binseg_*`）和 `db_*.md5sums.gz` 比对，2.x 索引是 `*.lambda` 目录（`index.lf.*`/`index.sa.*`/`option:*`/`seq_ids.*`/`translated_seqs.*`），结构上不可能命中。上游因此已在顶层注释掉 `add_subdirectory(tests)`，Debian 打包同样禁用 | `tests_adapt/`：保持上游 6 参签名、测试数据与用例矩阵不变，仅把调用行改成 2.x CLI，并将期望值改为参考构建钉死的 `expected.md5`（见第 5 节） |
| 3 | `tblastn`/`tblastx`（`mkindexp` 翻译路径）建索引报 `illegal characters in the first sequence` | 上游 `tests/db_nucl.fasta` 的**序列行内嵌空格**（1.x 容忍）。2.x `detectSeqFileAlphabet()`（`shared_misc.hpp`）用 `CharString` 读入并做严格回环比较，空白被保留导致三种字母表都不匹配；而真正建索引的强类型读入会跳过空白 | 驱动解压时仅对**序列行**做空白归一（`sed '/^>/!s/[ \t]//g'`）。**已证明对 2.x 无副作用**：带空白与去空白数据建出的索引逐文件 md5 完全一致，检索输出逐字节一致（`tests_adapt/whitespace_noop_proof.txt`） |
| 4 | `test_search_blastn_sa_*`（BLASTN + legacy 后缀数组索引）**段错误** | 上游 2.x legacy SA 检索路径缺陷：`_searchSingleIndex<GlobalDataHolder<Dna5, IndexSa<void>, BlastTabular, (BlastProgram)0>>` SIGSEGV（gdb 栈见下）。x86_64 参考构建同样复现，与 OHOS 适配无关 | 矩阵内显式列为 skip 并附原因（7 例）；其余 4 个 PROG 的 `sa` 检索（blastp/blastx/tblastn/tblastx）全部通过 |
| 5 | `test_search_blastn_fm_m9` 偶发不一致（约 1%） | 上游 2.x **BLASTN FM 检索非确定性**：同一二进制、同一索引、`-t 1` 下偶尔输出更多命中（16188 → 51943 行；正常结果是异常结果的子集）。100 次重复中复现 1 次，且异常输出自身也可复现（同一 md5），说明是上游逻辑里的偶发分支/竞态而非随机数据 | 作为上游缺陷记录（见第 6 节），期望值取多数值；矩阵连续 5 轮 73/73 无抖动 |
| 6 | `find_package(ZLIB/BZip2)` 在交叉链下失效 | `ohos.toolchain.cmake` 的 `CMAKE_FIND_ROOT_PATH_MODE_*` 为 `ONLY` | `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 前置脚本 + 预设缓存变量（见第 3 节） |
| 7 | 交叉构建报 `-march=native`：`clang++: error: unsupported argument 'native' to option '-march='` | 上游 `LAMBDA_NATIVE_BUILD` 默认 `ON`，会追加 `-march=native` | 显式 `-DLAMBDA_NATIVE_BUILD=OFF`（与参考构建一致） |
| 8 | `-DLAMBDA_LEGACY_PATHS=1` 被 CMake 报 "Manually-specified variables were not used" | 该名字是源码里的**预处理宏**，上游 CMake 没有对应 option | 经 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 前置脚本追加到 `CMAKE_CXX_FLAGS`（`-DLAMBDA_LEGACY_PATHS=1`） |
| 9 | SeqAn 编译失败：`use of undeclared identifier 'aio_read'/'aio_write'/'aio_suspend'/'aio_error'/'aio_return'/'aio_cancel'`（`seqan/system/file_async.h`） | OHOS musl 的 `<aio.h>` 只有 `aiocb`/`AIO_*` 常量，不提供 POSIX AIO 入口函数，而 SeqAn 2.4.0 无条件调用 | 补丁 `0002-seqan-musl-posix-aio-shims.patch`：编译期提供 shim（返回 `ENOSYS`），不使用异步文件 IO 的路径不受影响 |
| 10 | SeqAn 编译失败：`use of undeclared identifier 'pthread_setaffinity_np'`（`seqan/parallel/parallel_thread_pool.h`） | 该函数是 glibc 专有扩展，musl 无 | 补丁 `0003-seqan-glibc-only-thread-affinity.patch`：把 `#if defined(__linux__)` 收窄为 `#if defined(__linux__) && defined(__GLIBC__)`，非 glibc 平台沿用原有的 `return false` 分支 |
| 11 | 若开启 OpenMP：`expected identifier specifying the name of the 'omp critical' directive`（`src/shared_misc.hpp:296`） | OHOS musl 的 `stdio.h` 里 `#define stdout (stdout)`；`SEQAN_OMP_PRAGMA(x)` 先把参数展开再交给 `SEQAN_DO_PRAGMA`，于是 `critical(stdout)` 变成 `omp critical((stdout))`，不再是合法标识符 | 本配方关闭 OpenMP 后该问题不触发（已核实：上游其余 `SEQAN_OMP_PRAGMA` 用的都是非宏标识符）；如将来启用 OpenMP，把 `critical(stdout)` 改成任意非宏标识符（如 `critical(lambda2Stdout)`）即可，语义不变 |
| 12 | 运行产物报 `__kmpc_*: symbol not found`（man 页生成阶段即失败） | OHOS SDK 的 `libomp.so` 不在设备镜像/本地 musl 运行根中 | 关闭 OpenMP（`-DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE`，见第 2 节） |
| 13 | OHOS aarch64 与 x86_64 参考构建结果不一致：`test_mkindex_blastn_sa` 索引 digest 不同（OHOS 多出 `translated_seqs.concat`/`.limits` 两个文件）、`test_search_blastn_fm_m0` 命中行数为参考构建的 3 倍（826775 vs 269584） | **上游未定义行为**：`LambdaIndexerOptions::alphReduction`（`src/mkindex_options.hpp:52`）是裸 `int` 且无初值，构造函数 `{}` 不赋值；该值只由 **mkindexp** 的 `--alphabet-reduction` 选项赋值（`mkindexn` 根本没有这个选项，其 `addOption` 位于蛋白质分支内）。`mkindexn` 路径读到的是**未定义栈残留值**，于是 `src/mkindex.hpp:236` 的 `if ((options.alphReduction != 0) \|\| (dbIndexType != SUFFIX_ARRAY))` 分支随平台/编译器而变：x86_64 上恰好为 0（不转储），OHOS aarch64 上非 0（转储）。**已用同一台 x86_64 机器复现**：仅给该成员加 `= 0` 显式初值重编参考二进制，`m0` 输出即从 `ed26…`(269584 行) 变为 `3cb5…`(826775 行)，与 OHOS 完全一致；反之旧参考二进制始终得到 `ed26…` | 补丁 `0004-mkindex-alphreduction-uninitialized.patch`：显式 `int alphReduction = 0;`，行为确定（与核苷酸 BLASTN 索引路径语义一致）；期望值同步用**带该修复的参考构建**重新生成（见第 5 节） |

### 证据：BLASTN + legacy SA 段错误（gdb 栈）

```
Program received signal SIGSEGV, Segmentation fault.
0x0000555555d8ecca in void _searchSingleIndex<GlobalDataHolder<seqan::SimpleType<unsigned char, seqan::Dna5_>,
    seqan::IndexSa<void>, seqan::Tag<seqan::BlastTabular_>, (seqan::BlastProgram)0,
    (seqan::BlastTabularSpec)0>, seqan::Tag<seqan::AffineGaps_> >(...) ()
#1 realMain<seqan::IndexSa<void>, seqan::SimpleType<unsigned char, seqan::Dna5_>, ...>(...)
#2 argConv3<seqan::Tag<seqan::BlastTabular_>, seqan::SimpleType<unsigned char, seqan::Dna5_>, ...>(...)
#3 argConv1<seqan::Tag<seqan::BlastTabular_>, (seqan::BlastTabularSpec)0>(...)
#4 argConv0(LambdaOptions&)
#5 searchMain(int, char const**)
#6 main
```
复现：`lambda2 mkindexn -d db.fasta -i db.fasta.lambda --db-index-type sa -t 1` 后
`lambda2 searchn -q queries.fasta -i db.fasta.lambda -t 1 -o out.m8` → 退出码 139（x86_64 参考构建同）。

## 5. 上游测试矩阵的适配口径（rule4）

上游 `tests/CMakeLists.txt`（`LAMBDA_FASTBUILD=OFF`）定义 **80 例**：

- `test_mkindex_${PROG}_${DI}`：5 PROG × 2 DI = **10 例**
- `test_search_${PROG}_${DI}_${FF}`：5 PROG × 2 DI × 7 输出格式（`m0 m8 m9 sam bam m9.gz sam.bz2`）= **70 例**

| PROG | 上游语义 | 2.x 调用映射 |
|---|---|---|
| blastn | `db_nucl` / `queries_nucl` | `mkindexn` + `searchn` |
| blastp | `db_prot` / `queries_prot` | `mkindexp -a aminoacid` + `searchp -a aminoacid` |
| blastx | `db_prot` / `queries_nucl` | `mkindexp -a aminoacid` + `searchp -a dna5` |
| tblastn | `db_nucl`（翻译）/ `queries_prot` | `mkindexp -a dna5` + `searchp -a aminoacid` |
| tblastx | `db_nucl`（翻译）/ `queries_nucl` | `mkindexp -a dna5` + `searchp -a dna5` |

执行的用例数 = **73**（80 − 7 例 BLASTN+sa 段错误），通过 **73/73**：

- 索引校验：每次运行都校验索引（与上游一致），摘要 = 索引目录内「相对路径 + md5」排序清单的 md5，与 `expected.md5` 逐字节比对；
- 检索校验：输出内容 md5 与 `expected.md5` 逐字节比对；`m9.gz`/`sam.bz2`/`bam` 先解压为规范内容再比对（避免压缩库版本差异）；另加语义断言（BLAST 程序标签 BLASTN/BLASTP/BLASTX/TBLASTN/TBLASTX、命中数、字段数、BAM 魔数）；
- 期望值来源：x86_64 Linux + clang 15 + Release + `LAMBDA_LEGACY_PATHS=1` 参考构建（与目标构建在关键维度一致：无 OpenMP、Release、`LAMBDA_NATIVE_BUILD=OFF`），且**已应用 0004 补丁**（消除 `alphReduction` 未定义行为，使 x86_64 与 aarch64 得到同一确定结果）；宿主参考构建连续多轮全矩阵 73/73；
- 期望值条数 = 执行用例数 = 73（用例名唯一），且 `m9` 与 `m9.gz`、`sam` 与 `sam.bz2` 的期望值相同（跨格式不变式，脚本内校验）。

## 6. 已知限制（上游缺陷，非 OHOS 适配引入）

1. **BLASTN + legacy SA 检索段错误**：7 例（`test_search_blastn_sa_*`）不可执行；`sa` 索引本身可建（`test_mkindex_blastn_sa` 通过），缺陷在检索路径。x86_64 参考构建同样复现（gdb 栈见第 4 节）。
2. **`alphReduction` 未初始化（已在补丁 0004 修复）**：修复前同一源码在不同平台产出不同的 BLASTN 索引与检索结果；修复后 x86_64 与 aarch64 结果一致（第 4 节问题 13）。
3. 上游 `tests/` 已 1.x 化且被上游禁用，本适配的期望值由参考构建钉死，而非上游 `db_*.md5sums.gz`（1.x 平铺索引 md5，结构上无法对应）。
4. OpenMP 关闭（OHOS SDK 的 `libomp.so` 不在目标设备/本地 musl 运行根中，见第 2 节），`lambda2` 为单线程构建；与 x86_64 参考构建一致。

## 7. 验证记录

| 项 | 结果 |
|---|---|
| OHOS 交叉构建（conan create，`ohos-aarch64-run` + qemu/musl 运行根） | `conan create` EXIT=0 |
| 上游测试矩阵（构建期执行） | **73/73 通过**（逐例日志 73 个，PASS 73 / FAIL 0）；80 例中 7 例因上游 legacy SA+BLASTN 段错误不可执行，已列明原因 |
| 跨格式不变式（m9==m9.gz、sam==sam.bz2） | yes |
| 消费者端到端用例（`test_package/test.sh`） | **10/10 断言**：蛋白链路 m8/m9/sam/m9.gz/bam/sam.bz2 + 核苷酸链路 m8 |
| 真机 DAYU200（OpenHarmony 6.0.0.47 aarch64，静态产物 20666760 字节） | **12/12 断言通过，exit_code=0**（`tests_adapt/device_e2e.sh` + `tests_adapt/device_evidence/_device_evidence.json`） |

## 8. CI 门禁相关

| 项 | 说明 |
|---|---|
| `archives/l/lambda-align2/commands.json` | 本包产出 CLI 可执行文件 `lambda2`，CI L0k（R38）要求软件级目录声明命令清单；已按 `templates/commands.json.template` 提供（`type=tool`、`versions.2.0.1.ref=lambda-align2/2.0.1`、`commands=[lambda2]`、`binary=false`，与同仓库 samtools/acedb 等应用一致） |
| 设备本机构建的执行权限 | CI worker 运行在 OpenHarmony aarch64 设备上，man 页生成步骤会 exec `lambda2` 本体；OHOS 要求被 exec 的 ELF 已代码签名（否则 E077/E083）。因此 `build()` 的顺序为：`--target lambda2` → 签名 → 全量构建（man 页）→ 再次签名 |
| 真机 `bam` 断言口径 | 设备 busybox 的 `gunzip` 不支持 BGZF 多成员 gzip 流（实测 `bad symbol`），且 busybox 无 `od`/`tr`；真机脚本用 `printf`+`dd`+`cmp` 断言 BGZF 头部（`1f 8b 08 04` = FEXTRA）。该 BAM 的完整有效性已在 WSL 侧用 zlib 逐成员解压验证：解出 659 字节、魔数 `BAM\1` 正确 |
| CMake 最低版本（补丁 0005） | 上游 `cmake_minimum_required (VERSION 3.0.0)`；CI worker 的 CMake 4.x 已移除对 <3.5 的兼容，配置阶段直接失败（`Compatibility with CMake < 3.5 has been removed from CMake`）。补丁提升到 `3.5`（本地 CMake 3.22 实测仍可配置构建） |
| `run_matrix.sh` 交叉执行前缀（审查意见 id 192246715） | `RUN="$*"` 读取交叉执行前缀，但 `run_case` 调驱动时未透传，导致 `maintests2.sh` 的 `RUN` 恒为空、交叉环境下直接 exec aarch64 产物（Exec format error）。已改为 `sh "$DRIVER" "$SRCDIR" "$BINDIR" "$@" $RUN`（不加引号以按空格拆分「执行器 + 参数」）。**实测验证**：用可观测包装器作为前缀，修复后包装器被调用（mkindexn + searchn 各一次），不传前缀时调用 0 次 |
