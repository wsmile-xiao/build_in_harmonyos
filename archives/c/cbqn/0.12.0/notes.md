# cbqn 0.12.0 适配笔记

## 编译环境

- 构建系统: makefile（上游自带 BQN 驱动的引导式构建 `make for-build` → `build/build` → `build/src/build.bqn`）
- 编译日期: 首次构建 2026-09-07；最终验证与账本 2026-09-08（本文所有数字取 2026-09-08 那一轮 W3 日志）
- 编译器: `/data/service/hnp/bin/clang` 15.0.4（经 profile `tools.build:compiler_executables` 传入），`make` GNU Make 4.4.1
- 状态: built（`conan create` 通过，制品仓发布由合并后的 release 流水线决定）
- 任务: #6226 `feat/cbqn-0.12.0`（活动：开源鸿蒙PC专项积分赛，认领人 wanderlust_0823）

## 编译步骤（配方固化）

```sh
# 0) 子模块补齐（tag 归档里三个 Submodule 目录是空的；配方用
#    get(filename="cbqn-0.12.0-<target>.tar.gz", destination=build/<target>, strip_root=True)，
#    等价于下面两条，实际下载文件名由 Conan 决定）
tar xzf cbqn-0.12.0-bytecodeLocal.tar.gz -C build/bytecodeLocal --strip-components=1
tar xzf cbqn-0.12.0-singeliLocal.tar.gz  -C build/singeliLocal  --strip-components=1

# 1) 引导解释器：纯 C，不需要 libffi / C++，并且 makefile-only 路径会拒绝 singeli=1
#    —— 所以这一步的参数集是刻意最小的（配方 _bootstrap_flags）
make for-build CC=<绝对 clang> REPLXX=0

# 2) 解释器 + 共享库（配方 _make_flags 的完整参数集；shared-o3 额外带 lf= 补 DT_SONAME）
make o3        CC=<绝对 clang> CXX=<绝对 clang++> REPLXX=0 FFI=1 singeli=1 \
               target_arch=aarch64 target_os=linux version=0.12.0 nogit=1 j=4
make shared-o3 <同上参数> lf=-Wl,-soname,libcbqn.so

# 3) 只为执行"上游按构建配置注册"的那批用例（不进入交付产物，配方 build() 内自动跑）
make debug        <同上参数> OUTPUT=cbqn-debug       # -DDEBUG ⇒ TEST_UTILS，含 mode 201/202/203/298
make o3 usz=32    <同上参数> OUTPUT=cbqn-usz32       # -DUSZ_32，usz32.bqn 才有意义
```

产物：`bin/bqn`（上游 `BQN` 在包内按 install 约定以小写名落盘，见问题 13）、`lib/libcbqn.so`、`include/bqnffi.h`、`licenses/LICENSE-*`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make o3` 首跑即 `failed to build bootstrap CBQN` | 上游 `build/build` 内部以 `i_CC=cc` 硬调子 make，OHOS 无裸 `cc`（只有 hnp `clang`） | 先显式 `make for-build CC=<绝对 clang> REPLXX=0`；`build/makefile` 的 `ifeq ($(origin CC),command line) override i_CC := $(CC)` 会覆盖，之后 `build/obj2/for_build5` 被复用 |
| 2 | `src/builtins/ffi/ffiCore.c:14: error: "<ffi.h> not found..."` | 该文件用 `#if !__has_include(<ffi.h>)` 预判；libffi 头/库路径没进编译命令行 | 用 `PkgConfigDeps` 生成 `libffi.pc` 并把 `PKG_CONFIG_PATH` 指向 generators 目录（`build.bqn` 的 `pkgconfig=1` 分支自己 `pkg-config --cflags/--libs libffi`）。**不要**用 `LD_LIBS=`：它在 makefile 里是整体替换 `i_LIBS_LD`，且在 `-rdynamic` 追加之后，会同时丢掉 `-lm`/`-ldl`/`-rdynamic`（`•ffi` 加载宿主符号需要 `-rdynamic`） |
| 3 | `test/cases/perf.bqn` 13/14（`wasn't fast enough`），且重复稳定复现 | `singeli=0` 时上游 Singeli 生成的 `si_*` 快速路径不存在；实测 3742 次调用恒定 ~1.28ms/次、累计 5.00s 触发上游 `_fastone` 的 `t<5` 断言 | 采用上游默认 `singeli=1`（额外固定引入 Singeli 子模块源码），该文件 14/14 通过 |
| 4 | `fuzz/bitarr-fill.bqn`、`fuzz/bitcpy.bqn`、`build-specific/test_range.bqn`、`build-specific/test_group_stat.bqn` 整文件 `Unknown/unsupported •internal.Temp mode: 201/202/203/298` | `src/builtins/internal.c` 把这四个模式包在 `#if TEST_UTILS`（`TEST_UTILS` 默认取 `DEBUG`）与 `#if TEST_UTILS && SINGELI` 里，release 构建根本不注册 | 按上游自身设计在**单个** `make debug` 变体（参数集仍含 `singeli=1`，因为 mode 298 需要 `TEST_UTILS && SINGELI`）里执行：24/24 全过；配方在 `build()` 内自动跑该变体 |
| 5 | `test/cases/usz32.bqn` 在发布配置下实跑 `1/6` | 该文件 6 条断言逐条都期望抛错（1/3/4/5/6 行期望 `Out of memory`，2 行期望 `𝕨⥊𝕩: 𝕨 too large`；5、6 行标 `%SLOW`）。usz64 地址空间下这些形状合法：只有第 1 行仍抛 Out of memory 而通过，第 2 行是 `Wrong error message`（实际抛 `Out of memory`），第 3-6 行是 `Expected error, but didn't get one` | 用 `make o3 usz=32`（`-DUSZ_32`）变体执行：6/6 全过（逐行明细见 `test_package/MANIFEST.yml` 的 `evidence`） |
| 6 | `test/cases/proper-fills.bqn:20,21` 稳定 `Expected error, but didn't get one` | 见下节"上游用例与实现错配"：期望错误串在本 tag 不存在，实现又对空数组提前返回 | 保留执行但把结果钉死为 `13/15` 且失败行号必须是 20/21（任何偏差即构建失败），notes/MANIFEST/PR 三处同口径申报 |
| 7 | 开启 replxx 的上游默认构建会把 `libc++_shared.so` 变成 `NEEDED`（`find` 在 `/data/service/hnp`、`/system`、`/usr/lib` 内均搜不到该文件），纯 C 路径的 `libcbqn.so`/`BQN` 只 `NEEDED libc.so` | replxx 是可选 C++ 行编辑库 | 采用 `REPLXX=0`（也是上游 `shared-o3`/`static-lib`/`wasi` 目标自身的取值），交互式行编辑记入已知限制 |
| 8 | 测试入口形态导致假失败 | `test/run.bqn` 用 argv 里的 `testname` 同时做临时用例文件名；传 `test/cases/system.bqn` 时 `•state`/`•name` 两条断言拿到完整路径（352/354） | 统一按上游 `"cases"•file.At` 语义传**相对 test/cases 的裸文件名**；`cli/*.bqn` 必须额外带 `bin=./BQN`，否则 66 例整文件 `0/N` |
| 9 | CI 预下载后 `source()` 抛 `NotADirectoryError: .../predl_cache/<hash>_cbqnBytecode/archive/<sha>.tar.gz` | `ci/conan/build_and_test.sh` 的预下载步骤会抽取 conandata.yml 中**任意位置**的 `http(s)` 字面量，下载到 `predl_cache/<md5[:8]>_<URL最后一段>`，然后用**整串文本替换**把原 URL 换成该本地路径。真正的触发条件是**URL 互为前缀**：当时额外写了仓库主页形式（`owner/repo` 那种短 URL），它恰好是同一条 archive URL 的前缀，于是长的那条被短的那条连带改写，拼出带多余 `/` 的畸形路径。我把这三条 URL 单独喂给框架那段抽取+替换代码复现过：只留互不为前缀的 archive URL 时改写结果干净可打开，把主页 URL 加回去立刻重现畸形路径。作用域也已按框架源码核实为**只读 conandata.yml 一个文件**（`python3 - "$CONANDATA" "$PREDL_DIR"`），所以 `MANIFEST.yml`、`commands.json`、软件级 `manifest.yaml` 里的仓库主页 URL 不在改写范围内 | 不是"conandata 只能放一条 URL"，而是**conandata 内 URL 必须互不为前缀**：主页/仓库归属形态一律不写，只保留三条下载用 archive URL（主源 + 两个子模块），这样 CI 预下载会连子模块一起预热、R39 源扫描也覆盖它们；该不变量由配方 `_sources_block()` 在 `source()` 前机器校验（命中即抛可读错误），注释与文档里也不写第二种 URL 形态的字面量 |
| 10 | `make for-build` 直接拒绝 `singeli=1`（`makefile-only builds don't support Singeli`） | `build/makefile` 的 `run_incremental_0` 对 `singeli=1` 显式 `false` | bootstrap 目标只传最小参数集 `CC=<clang> REPLXX=0`；`singeli=1` 只用于 `o3`/`shared-o3`/`static-lib`/`debug` |
| 11 | 归档目录出现 `conandata.yml.ghfast-bak`、`test_package/build/`、`CMakeUserPresets.json`、`__pycache__` | conan-verify 的镜像注入与 cmake_layout 的本地构建产物 | finish/打包前统一移出或删除（`~/tmp/cbqn/residue/`），提交前用 `git status --short` + `find` 复核五类残留（经验文档 §12.8） |
| 12 | CI L5a 报 `libcbqn.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址` | 上游 `shared-o3` 只用裸 `-shared` 链接，不写 `-Wl,-soname` | 追加 `lf=-Wl,-soname,libcbqn.so`（`ALL_LD_FLAGS = $(LDFLAGS) $(lf) $(i_lf) $(i_PIE) $(i_LIBS_LD)`，`lf` 是上游自身的"额外链接参数"，加法不影响 `-lm/-ldl/-rdynamic`）；实测 `readelf -d` 出现 `SONAME [libcbqn.so]`，且 `make -C test/ffi` 三项黄金比对仍全部 identical |
| 13 | 包内可执行文件停在 `bin/BQN`，与上游 install 约定的 `bin/bqn` 不符；补 SONAME 后消费者测试还一度报 `Error loading shared library libcbqn.so` | HMDFS 上同一目录内 `BQN` 与 `bqn` 是**同一个目录项**：`os.rename(BQN→bqn)` 静默 no-op（实测 `after rename: ['BQN']`），同目录 `shutil.copy2` 直接 `SameFileError`；只有在新目录里以目标名落盘才得到小写名。而补了 SONAME 之后 `DT_NEEDED` 由绝对路径变裸名，必须靠 runenv 解析 | `package()` 用 `os.makedirs(<pkg>/bin)` + `shutil.copy2(<src>/BQN, <pkg>/bin/bqn)` + `chmod 0755`，并断言 `bin/bqn`/`include/bqnffi.h`/`lib/libcbqn.so` 三件套存在；`test_package/conanfile.py` 的 `VirtualRunEnv` 用默认 run 作用域（产出 `conanrun.sh`）配 `env="conanrun"`。实测包内 `bin/bqn --version` → `CBQN 0.12.0 / built with FFI, singeli AARCH64`，`conan test` rc=0、`21 checks, 0 failures` |
| 14 | 想把库目录固化进 CTest 属性，使消费者不依赖 runenv | 两条 CMake 路径都不通：`$<TARGET_FILE_DIR:cbqn::cbqn>` 在 generate 期报 `Target "cbqn::cbqn" is not an executable or library`；改读 `IMPORTED_LOCATION_RELEASE` 取不到值，写出的 `set_tests_properties(ENVIRONMENT …)` **静默不生效**（设备实测属性没进 `CTestTestfile.cmake`，去掉 `LD_LIBRARY_PATH` 后 ctest 仍失败） | 不留无效代码：`test_package/CMakeLists.txt` 只保留机制说明与这两种失败尝试的记录；运行路径由 `env="conanrun"` 提供。真依赖有三重独立证据：去掉 `LD_LIBRARY_PATH` 裸跑消费者 → rc=127（`Error loading shared library libcbqn.so`）、CI L1e 破坏性反向验证（移走 `bin/`、`lib/`、`include/` 后测试必须失败）、`conan test` rc=0 |

## 上游用例与实现错配（proper-fills.bqn:20,21）——平台无关证据

1. 期望错误串 `">𝕩: Fill element of empty 𝕩 not known"` 在 v0.12.0 全仓 C 源码与
   预编译运行时字节码 blob 中 grep 命中 0（`build/bytecodeLocal/gen/*` 亦 0）。
2. `src/builtins/sfns.c` 的 `shift_powm()` 先 `if (ia==0) return x;` 才 `getFillE(...)`，
   对空数组根本不查 fill element，所以断言期望的错误不可能抛出。
3. 表达式直接求值确认无错：`./BQN -p '•Repr >0⥊{⇐}'` 正常返回。
4. 四种构建配置（`o3`、`o3+singeli=1`、`make debug`、`make o3 f=-DEACH_FILLS=1`）结果均为 `13/15`。
5. 上游 master 的 `test/cases/proper-fills.bqn` 第 20/21 行与 `src/builtins/sfns.c` 的
   `shift_powm` 早退分支与 tag 完全一致（至今未修），且 master 也没有该错误串。

结论：这两例属上游断言与实现不一致，与 OHOS/工具链无关；不做静默删除、不改判为"平台不兼容"，
而是保留执行 + 精确钉死观测结果 + 在 PR 与 MANIFEST 中申报。

## 依赖版本

- 运行/链接依赖：`libffi/3.5.2`（制品仓已发布，OHOS clang15/armv8 有预编译包；配方里
  `visible=False`——它只被 `•ffi` 内部使用，不出现在 `bqnffi.h` 公共接口中）
- 构建输入（上游 `.gitmodules` 在 v0.12.0 固定的 commit，逐字取自 tag tree；官方 URL 与
  双端核对过的 SHA256 都在 `conandata.yml` 的 `submodules` 段，写法约束见问题 9）：
  - `build/bytecodeLocal` ← `dzaima/cbqnBytecode@156b47caf895f6706811c5c34bbbbaf192b8018b`
  - `build/singeliLocal` ← `mlochbaum/Singeli@5187ed3aa22a2257b63c04a5498ec756fa6263cb`（ISC）
- 有意不引入：`build/replxxSubmodule`（`dzaima/replxx@5e3bd870699007b9536d29f60e3a2b0a68ce0a7a`，见问题 7）

## 测试账本（同源于 test_package/MANIFEST.yml 与 manifest.yaml）

- 上游静态条目 `N_static`：**2275**（`test/run.bqn` 对 `test/cases/**.bqn` 43 个文件的注册条目，
  含 runner 自身按 `%SLOW/%DEBUG/%HEAPVERIFY/%PROPER_FILLS/%EACH_FILLS/%USZ32` 跳过的 17 条）
- 配方实际执行口径（`conan create` 日志内的 `UPSTREAM LEDGER` 行，本地 W3 与远端 CI 同源）：
  `files=43 entries=2275 executed=2258 passed=2256 failed=2 skipped_by_upstream_flags=17`
  - 发布配置（`o3 + singeli=1 + FFI=1 + usz=64 + REPLXX=0`）跑 38 个文件：2245 条 / 实跑 2228 /
    通过 2226 / 跳过 17 / 失败 2
  - TEST_UTILS 变体（`make debug`，`singeli=1`）跑 4 个文件：24 条 / 24 通过
  - `usz=32` 变体（`make o3 usz=32`）跑 1 个文件：6 条 / 6 通过
  - `executed=2258` 是三种配置合并后的执行数；配方同时断言恒等式
    `entries == passed + failed + skipped`，不成立即构建失败
- 探索期对照实验：若强行把 43 个文件全塞进发布配置一次跑完，得到实跑 2258 / 通过 2227 /
  失败 31；这 31 例中 24 例属 `-DTEST_UTILS`、5 例属 `-DUSZ_32`（该文件另 1 例两种配置都通过）、
  2 例为上游错配。这正是配方按上游设计分配置执行的原因，而不是把 29 例记成"平台不兼容"。
- 上游 FFI 子套件 `make -C test/ffi`：test-lib / test-shared / test-extended **3/3 黄金输出一致**
- 消费者测试（test_package，另列）：1 个程序、21 条 FFI 行为断言，21/21 通过

## 源码修改

无。`patches/` 为空，`patches: []`；所有适配都通过上游自身的 make 变量表达
（`REPLXX`/`FFI`/`singeli`/`usz`/`target_arch`/`target_os`/`version`/`nogit`/`CC`/`CXX`/`j`）
加上游 README 指定的 `build/*Local` 子模块回退目录。

## 验证结果

```text
$ ./BQN --version
CBQN 0.12.0
built with FFI, singeli AARCH64

$ ./BQN -p '+´↕10'
45
$ ./BQN test/run.bqn slow system.bqn
system.bqn: 355 passed! (3 skipped tests)        # 路径形式入参会退化成 352/354，见问题 8
$ ./BQN test/run.bqn slow perf.bqn
perf.bqn: 14 passed!
$ ./BQN test/run.bqn slow ffi.bqn
ffi.bqn: 328 passed!
$ ./cbqn-debug test/run.bqn slow build-specific/test_group_stat.bqn
build-specific/test_group_stat.bqn: 14 passed!
$ ./cbqn-usz32 test/run.bqn slow usz32.bqn
usz32.bqn: 6 passed!
$ make -C test/ffi CC=clang
Files test.expected and test.got are identical
Files library.expected and shared.got are identical
Files extended.expected and extended.got are identical
$ readelf -d libcbqn.so | grep NEEDED
(libc.so only)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/bqn` | CBQN 解释器（`--version`、`-p`、`-e`、`-f`；上游 install 同名） |
| `lib/libcbqn.so` | 可嵌入求值库，导出 `bqnffi.h` 的 `bqn_*` C ABI |
| `include/bqnffi.h` | 唯一公共头（`bqn_init/bqn_eval*/bqn_call*/bqn_make*bqn_read*/bqn_shape/bqn_type/...`） |
| `licenses/LICENSE-{LGPLv3,GPLv3,MPL2,MIT-sort,Apache2,Boost}` | 上游许可证原文（主代码三选一，另含 timsort/ryu 例外） |
| `commands.json` | 软件级 CLI 声明（R38） |

## 注意事项与已知限制

1. `REPLXX=0`：交互式 REPL 的行编辑/语法着色/名称补全不可用（可选 C++ 组件，见问题 7）。
   需要时应在本包之外单独立项适配 replxx。
2. 上游构建系统在编译期必须**运行**引导解释器，因此本包只能在可执行目标二进制的原生环境
   （OHOS worker / 真机）构建；纯交叉环境下配方**主动抛错拒绝**（`can_run()` 为假时抛 `ConanInvalidConfiguration`，不静默跳过后仍报账本）。确实只需要构建产物的场合，必须显式写 `-o cbqn/*:upstream_tests=False`，此时日志会打印 `upstream_tests=False: upstream suites skipped by option`，账本数字不再适用。
3. `singeli=1` 会在构建期用引导解释器跑 Singeli 生成部分热路径源码；这是上游默认配置，
   也带来第 3 条问题里那个测试差异。
4. `test/mainCfgs.sh`、`test/x86Cfgs.sh`、`test/moreCfgs.sh` 与 `test/{joinReuse,readTests,precompiled}.bqn`
   需要 `mlochbaum/BQN` 参考实现仓库、`dzaima/BQN`(Java) 或 `-DPRINT_JOIN_REUSE` 等本 tag
   不提供的资产/开关，属上游外部测试资产，未执行（不计入通过率分母，也不冒充已跑）。
5. `usz=32`、`-DTEST_UTILS` 变体仅用于测试取证，不进入交付产物。
6. 语言预检：任务声明 `cpp`，`lang-preflight` 判 `c`（源文件 100% C，构建系统为 makefile），
   属 R47 的 c↔cpp 兼容族，正常适配；未触发 `env_unsupported`。
7. `test/cases/perf.bqn` 是上游清单里**唯一带墙钟阈值**的断言（重复 `⍋` 必须摊销到单次 <10µs
   且 10 次累计 <5s）。发布配置（`singeli=1`）下本机与每一轮 W3 都是 `14 passed!`；
   `singeli=0` 时它稳定不通过（3742 次调用恒定 ~1.28ms/次，直到耗尽 5s 预算）——两者不是矛盾：
   前者快速路径存在、循环很快收敛，后者永远收敛不了所以必然吃满预算。**配方对它不放宽**：
   该文件任何非全绿都直接让构建失败，只在失败信息里附一句可区分诊断（命中
   `wasn't fast enough` 签名时提示这是宿主计时预算问题、并给出复现命令），避免把宿主抖动
   误读成代码回归，也绝不把真实回归当宿主抖动放过。若某天 CI worker 慢到触发该预算，
   按 R41 留全量日志透明记录并回报，而不是悄悄加豁免。
8. `test/cases/windows/system.bqn`（62 条）不参与本平台账本：它编码 Windows 盘符/反斜杠路径语义，
   上游自身的默认 glob 也不含该目录。探索期曾误把它收进发布配置跑过一次，日志留下 `22/62` 与
   `Expected: "A:/"`、`Expected: "//server/share\abc\def"` 一类的 40 条失败签名（设备
   `~/tmp/cbqn/create-full2.log` 的 `windows/system.bqn` 段可逐行复核）。配方对此的处理是
   **显式排除目录 + 在此处登记条数**，不是静默删测试。

---

**编译结束**: 2026-09-08 14:50
**最终状态**: built
