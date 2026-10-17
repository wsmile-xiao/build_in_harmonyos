# libfstfar 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-20
- 编译器: clang/clang++（`clang version 15.0.4`，`Target: aarch64-unknown-linux-ohos`）
- 状态: built（真机门禁通过：编译 + `test_package` 消费者 + 上游 10 用例执行）

## 库定位

libfstfar 是 openfst-1.8.4 的 **FAR（FST ARchive）扩展子库**：提供 FST 档案容器
（`STTable` ＝ 单文件可随机访问表，`STList` ＝ 单文件顺序列表）的 C++ 实现与公共头文件。

源码包与同 tarball 兄弟包 `libfst` / `libfstconst` / `libfstngram` / `libfstlookahead`
**同为 `openfst-1.8.4.tar.gz`**（sha256 `a8ebbb6f…8016`）。上游 configure 用 `--enable-far`
单独打开本扩展（`configure.ac:60-64`，默认 `no`；`src/extensions/Makefile.am:14-16` 由
`HAVE_FAR` 决定是否把 `far` 放进 `SUBDIRS`）。

### 交付面（本包只交付 FAR 扩展本身）

| 产物 | 说明 |
|------|------|
| `lib/libfstfar.so.26`（`-version-info 26:0:0`，默认 shared 构建；静态形态为 `libfstfar.a`） | 档案容器实现：`sttable.cc`（`IsSTTable`）、`stlist.cc`（`IsSTList`） |
| `include/fst/extensions/far/*.h`（15 个） | `far.h`（`FarWriter`/`FarReader`/`STTableFarWriter`/`STListFarWriter`）、`sttable.h`、`stlist.h`、`far-class.h`、`farlib.h`、`create.h`、`extract.h`、`info.h`、`equal.h`、`isomorphic.h`、`map-reduce.h`、`compile-strings.h`、`print-strings.h`、`encode.h`、`convert.h` |
| `lib/libfst.so.26` / `lib/libfst.a` | openfst 核心库（`SUBDIRS` 里无条件构建；`libfstfar` 的 `LIBADD` 依赖它，故 `cpp_info.libs = ["fstfar", "fst"]`） |

**不交付**：`libfstfarscript`、`far*` 工具（9 个）、`fst*` 工具（37 个）。这些都由
`openfst/1.8.4`（以及 `libfst` / `libfstconst` 等兄弟包）交付——理由见下面「构建开关」。

## 配方策略

- 源码：复用 openfst-1.8.4.tar.gz（sha256 与 libfst/libfstconst 配方一致）
- 补丁：复用 openfst 1.8.4 已验证的 4 个平台补丁（config.guess / config.sub /
  configure umask / `--help` 退出码），逐条 `patch -p1 --dry-run` 对 .orig 源码树通过
- 构建开关：`--enable-far --disable-bin --disable-static --enable-shared`
- Conan 包名：libfstfar；`cpp_info.libs = ["fstfar", "fst"]`：`libfstfar.la` 的
  `LIBADD` 是 `../../lib/libfst.la`（`src/extensions/far/Makefile.am`），
  `libfstfar` 的未定义符号要靠 `libfst` 解析，而本包确实交付 `lib/libfst.so`，故两条都声明
- 交付的二进制（测试程序与核心库）额外打 `$ORIGIN/../lib` 可重定位 rpath：
  libtool 不会自动加 rpath，缺了它在**没有 LD_LIBRARY_PATH** 的环境里加载器找不到同包的
  `libfst.so.26`。注入判据**只看那一行 `LDFLAGS`**，不能看整个 Makefile 是否出现
  `-rpath`（automake 生成的 Makefile 天然含 `am_libfst<ext>_la_rpath = -rpath $(libdir)`，
  按整文件判断会整文件跳过——`src/extensions/far/Makefile` 有 3 处，这正是首轮 W4 审计
  判 P1 的根因，改逐行判断后修复）

### 为什么是 `--disable-bin`

上游 `--enable-bin` 默认 **yes**，且它同时是 `HAVE_SCRIPT` 的开关（`configure.ac:119-126`）。
打开它会连带构建 `src/script`（47 TU）+ `src/bin`（46 个 `fst*` 工具 × 2 TU）+ 9 个 `far*` 工具
+ `libfstfarscript`，约占整包编译量 **80%**。两条理由关掉它：

1. **交付面**：本包是 openfst 的**子库**。`fst::script` 与命令行工具属于主包
   `openfst/1.8.4`；家族先例 `archives/l/libfstconst/1.8.4` 的 notes 也是这句
   「需要 `fst::script` 与命令行工具请用 `openfst/1.8.4`」。同批同 tarball 兄弟包
   `libfstlookahead` 采用同一口径。**注意**：先例 `libfstconst` 的配方注释里另有一句警告
   「子库配方若 `--disable-*-fsts`/`--disable-bin` … 注册表不全 → 上游测试假败」——
   那条**不适用于本包**：本包保留 `--enable-far`（扩展本体照常构建），上游 10 个
   测试程序只链 `../lib/libfst.la`（`src/test/Makefile.am` 的 `LDADD`，无 `HAVE_BIN`
   条件），与工具链无关；实测 10/10 全过。
2. **构建预算（硬约束，如实登记）**：本地/CI 的 G2 `conan create` 超时被**硬编码 3600s**
   （`scripts/ohc/conan_verify.py`，`--timeout` 只作用于外层 `timeout`，
   `OHC_W3_TIMEOUT`/`ci/config/build_timeouts.txt` 只被 `finish` 的 W3 步骤读取）。
   全量（`--enable-bin`）构建在本设备实测**贴着这个上限**：`-j2` 的干净轮一次以
   **约 3550s 通过**（`reports/w3-local-ci.log` 与 `evidence-534ab8f/` 有该轮记录，
   G2 PASS、CLI 8/8），另**两次在 `test_package` 之前被 G2 超时杀掉**（一次 `-j1` 静态轮、
   一次 `-j2`；被杀轮 `reports/conan-create.log` 被整文件写成 7 字节的 `TIMEOUT`）。
   `--disable-bin` 后编译量降到约 20%（实测约 1600–2500s 完成），构建稳定落在预算内。

> 需要 FAR 的 `far*` 命令行工具时用 `openfst/1.8.4`（或 `libfst` / `libfstconst`，
> 它们构建了 openfst 全套工具）。

## 上游测试用例审计（同 tarball 子包按父 tarball 全量清点面取最大值）

`openfst-1.8.4.tar.gz` 是**单 tarball 多子包**结构，libfstfar 只是其中一个交付面，
但上游测试注册面属于整个父 tarball。候选口径逐项清点：

| # | 口径 | 读数 | 取数命令（在解压后的源码根执行） |
|---|------|------|----------------------------------|
| 1 | autotools 注册面（`check_PROGRAMS` / `TESTS`） | **7** | `grep -n 'check_PROGRAMS\|^TESTS' src/test/Makefile.am` |
| 2 | Bazel 注册面（`cc_test`） | **7** | `grep -n 'cc_test\|for weight in' BUILD.bazel` |
| 3 | CMake 注册面（`add_test` / `enable_testing`） | **0** | `find . -name CMakeLists.txt`（tarball 内无 CMake 构建） |
| 4 | 测试源文件数 | **3** | `ls src/test/*.cc`（`fst_test.cc` / `weight_test.cc` / `algo_test.cc`） |
| 5 | **用例分支数（取此最大口径 → N）** | **10** | 2 个独立程序 + `algo_test.cc` 的 8 个 `TEST_*` 分支 |
| — | 源码级断言宏（另一计数单位，仅披露、不并入 N） | `CHECK(` 185 处 | `grep -o 'CHECK(' src/test/*.cc src/include/fst/test/*.h \| wc -l` |

`src/test/algo_test.cc:66-89` 是 8 个互斥分支：`TEST_TROPICAL`、`TEST_LOG`、`TEST_MINMAX`、
`TEST_LEFT_STRING`、`TEST_RIGHT_STRING`、`TEST_GALLIC`、`TEST_LEXICOGRAPHIC`、`TEST_POWER`
（末尾 `#else #error` 保证必须命中其一）。其中 **5 个**在 `Makefile.am` 与 `BUILD.bazel`
均有注册项；**3 个**（left_string / right_string / gallic）在两套构建系统里都**没有**注册项。
主 N 取「用例/注册类」口径的最大值 = **10**。

| # | 用例 | 来源 | 上游注册项 |
|---|------|------|-----------|
| 1 | fst_test | `src/test/fst_test.cc` | ✅ Makefile.am + Bazel |
| 2 | weight_test | `src/test/weight_test.cc` | ✅ Makefile.am + Bazel |
| 3 | algo_test_log | `-DTEST_LOG` | ✅ |
| 4 | algo_test_tropical | `-DTEST_TROPICAL` | ✅ |
| 5 | algo_test_minmax | `-DTEST_MINMAX` | ✅ |
| 6 | algo_test_lexicographic | `-DTEST_LEXICOGRAPHIC` | ✅ |
| 7 | algo_test_power | `-DTEST_POWER` | ✅ |
| 8 | algo_test_left_string | `-DTEST_LEFT_STRING` | ❌ 未注册（同源分支，本配方补编） |
| 9 | algo_test_right_string | `-DTEST_RIGHT_STRING` | ❌ 未注册（同源分支，本配方补编） |
| 10 | algo_test_gallic | `-DTEST_GALLIC` | ❌ 未注册（同源分支，本配方补编） |

**未修改任何上游测试用例**：10 个程序全部由上游 `src/test/*.cc` 原样编译，差异只在
`-D` 宏与链接参数；`make check` 本身未使用（它在精简构建下会因扩展模块动态加载假败）。

**实测 N′ = 10**（`test_package` 真机逐个执行包内 `_ohos_tests/`）：
PASS **10** / FAIL 0 / SKIP 0 / NOT_RUN 0 → 通过率 = **10/10（100%）**。

## 鸿蒙特有测试（`test_package`，不进上游分母）

| 来源 | 项数 | 结果 |
|------|------|------|
| `test_libfstfar.cc`：真机 C++ 消费者——用 clang++ 编译并链接本包安装的 `libfstfar`，直接调用只存在于 libfstfar 的强符号 `fst::IsSTList()` / `fst::IsSTTable()`（定义在 `extensions/far/stlist.cc`、`sttable.cc`，链接期缺失即失败），再走 FAR 公共 API `FarWriter<StdArc>::Create(STLIST)` → `Add` → `FarReader<StdArc>::Open` → 顺序迭代（STList 是**顺序**档案，`Find()` 上游直接 `LOG(FATAL) Operation not supported`）→ `GetFst` 读回比对（含 `Fst<Arc>::Read` 注册表路径） | **14** | **14 PASS / 0 FAIL** |
| `check_libfstfar.sh`：包内 `far*`/`fst*` 工具端到端往返（`fstcompile` → `farcreate --far_type=stlist` / `--far_type=sttable` → `farinfo --list_fsts` 按 key 读回 → `farextract --keys=` → `fstprint` 空白归一化 diff） | **8** | **NOT_RUN**（本包 `--disable-bin`，包内没有命令行工具；见下） |
| **合计** | **14 执行 + 8 NOT_RUN** | 执行部分 14/14（100%） |

**NOT_RUN 的技术原因（不是环境限制，是交付面决定）**：本配方按 `--disable-bin` 构建，
包里不含 `far*`/`fst*` 可执行文件，因此这 8 项检查**没有可测对象**。`test_package` 会检测
`bin/farcreate` 是否存在：不存在就打印
`HMBS_CLI_CHECKS_NOT_RUN={"executed":false,"not_run":8,"reason":"..."}` 并把该段记为
NOT_RUN（既不算通过也不算失败）。**替代验证**：`check_libfstfar.sh` 本身在与本包同源的
历史构建（`--enable-bin` 形态）上跑过 8/8（见 `evidence-534ab8f/conan-create.log` 的 `HMBS_HARMONY_SHELL_CHECKS=8 HMBS_HARMONY_SHELL_FAILED=0`）；本包交付的
`libfstfar` 功能面由上面 14 项消费者断言在真机上覆盖（同一个 `FarWriter`/`FarReader`
代码路径）。需要 FAR 命令行工具请用 `openfst/1.8.4`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 不打开 `--enable-far` 时根本不产出 `libfstfar` | `configure.ac:60-64` 的 `enable_far` 默认 `no`，`src/extensions/Makefile.am` 由 `HAVE_FAR` 决定 `fardir`，为空则整段 `SUBDIRS` 不含 far | 配方 `generate()` 显式加 `--enable-far` |
| 2 | **静态构建下包内交付物读不了 FST**：`fstinfo in.fst` 报 `ERROR: GenericRegister::GetEntry: Error loading shared library vector-fst.so` + `Fst::Read: Unknown FST type "vector"`；`farcreate` 读不进输入 FST，静默写出 12 字节的空档案且 **rc=0**（假成功） | `REGISTER_FST`（`fst/register.h:119-120`）展开成 `lib/fst-types.cc` 里文件作用域的 `static FstRegisterer` 对象，`fst-types.o` 自身没有任何被引用的强符号；`--disable-shared` 静态链接时链接器按需取对象文件，整块剔除该成员 → `FstRegister` 表空 → `GenericRegister::GetEntry` 回退 `dlopen("<type>-fst.so")`（`fst/generic-register.h:96-100`）失败 → `Fst<Arc>::Read` 返回 `nullptr`（`fst/fst.h:265-271`）。判据：`llvm-nm -C <pkg>/lib/libfst.a \| grep -c FstRegisterer` = 72，而静态链接出的二进制里 = 0 | **默认改为 shared 构建**（`default_options.shared = True`）：动态库整库加载即执行全部静态注册器，注册表完好——这也是上游 `./configure` 不带 `--disable-shared` 时的默认形态。静态形态保留为 option，此时下游必须 `-Wl,--whole-archive libfst.a -Wl,--no-whole-archive`（本配方的 `_build_upstream_tests` 两条路径都覆盖） |
| 3 | `$ORIGIN/../lib` rpath 只加到了 `src/bin`，`src/extensions/far` 下的工具 RUNPATH 仍是 `//lib`（裸 PATH 下 rc=127） | `_add_origin_rpath()` 的守卫写成「**整个 Makefile** 里出现 `-rpath` 就跳过」，而 `src/extensions/far/Makefile` 天然含 `am_libfstfar_la_rpath = -rpath $(libdir)`（3 处）⇒ 整文件被跳过。`test_package` 跑在 `conanrun`（有 `LD_LIBRARY_PATH`）里**恰好掩盖**了它，只有 CI 的 L2 裸 PATH smoke 漏出 9 条 warn | 守卫改为**逐行判断**（只看那一行 `LDFLAGS` 是否已含 `-rpath`）。判据：`for b in fstinfo farinfo; do llvm-readelf -d <pkg>/bin/$b \| grep RUNPATH; done` 应都为 `$ORIGIN/../lib`。首轮 W4 审计据此判 P1。**本包 `--disable-bin` 后不再产出 CLI，这条只对 `--enable-bin` 形态有意义**，但修法保留（测试程序仍靠它定位同包 `libfst.so.26`） |
| 4 | 全量（`--enable-bin`）构建在 G2 硬编码的 3600s 内跑不完 | 见上面「为什么是 `--disable-bin`」：`src/script`+`src/bin` ≈ 80% 编译量，设备实测需 3600–3900s | 显式 `--disable-bin`（子库交付面），编译量降到约 20% |
| 5 | `make install` 报 `install: … Error 64` / 头文件权限失败 | E182/E087：OHOS worker 无 GNU install，toybox `install -c` 在 HMDFS 上失败；HMDFS 也不支持 `chmod` | 配方写 install shim（`cp -f` + `mkdir -p`，chmod 容错），`sed` 把各 Makefile 的 `INSTALL = <toybox install>` 改为指向 shim（libtool `--mode=install` 读的正是该变量，故 `.so` 安装同样走 shim） |
| 6 | 测试程序进包后 `Error 126 Permission denied` | E087：HMDFS 不支持 chmod，`open("wb")` 落盘 0644 无执行位 | `package()` 用 `os.open(..., 0o755)` 创建带执行位的目标文件 |
| 7 | `test_package` 执行 `check_libfstfar.sh` 被拒 | 同上，脚本文件无执行位 | 用 `sh <script>` 显式调解释器 |

## 源码修改

无源码级修改；4 个补丁均为平台可移植性补丁（与 libfst/libfstconst 相同 tarball 上已验证）：

| 补丁 | 内容 |
|------|------|
| `0001-config.guess.patch` | 更新到新版 config.guess（识别 `HarmonyOS`，产出 `aarch64-unknown-linux-ohos`） |
| `0002-config.sub.patch` | 同步 config.sub（接受 `linux-ohos*` triplet，`--host=aarch64-linux-ohos` 才能通过校验） |
| `0003-configure.patch` | configure 生成临时目录的 `umask 077` → `022`（HMDFS 权限边界，E011） |
| `0004-flags-help-exit.patch` | `src/lib/flags.cc` 显式 `--help`/`--helpshort` 返回 0 而非 1 |

## 依赖版本

无外部依赖（`w0-deps.txt` 显式 `none`：上游 `configure.ac` 无 `PKG_CHECK_MODULES`／
`AC_CHECK_LIB` 强制依赖，源码 include 全部是系统头 + 自带头；运行时只需
`libc++_shared.so` 与 `libc.so`）。

## 验证结果

```bash
# 干净轮（清缓存后）真机执行
conan create archives/l/libfstfar/1.8.4 \
  -pr:h=<ohos-aarch64 profile> -pr:b=<ohos-aarch64 profile> --build=missing
# 上游 10 用例（test_package 真机运行包内 _ohos_tests/）
#   10 PASS / 0 FAIL / 0 SKIP / 0 NOT_RUN → 10/10（100%）
# 鸿蒙特有测试：消费者 14 项真机断言
#   14 PASS / 0 FAIL → 14/14（100%）
#   包内 CLI 往返 8 项 = NOT_RUN（--disable-bin 无 CLI 交付；原因见上）
```

## 注意事项

- 上游 7 个注册用例是 openfst **整体**测试（测 VectorFst、各 arc type、各扩展运行时
  注册与 `Fst::Read` 通用读取路径），不是 FAR 专属测试；本 tarball 内**没有** FAR 专属
  的注册用例，FAR 功能面由 `test_package` 的真机消费者覆盖。
- 本包与 `libfst` / `libfstconst` / `libfstngram` / `libfstlookahead` 共享同一 tarball：
  补丁与 sha256 一致，仅 configure 扩展开关、`cpp_info.libs` 与子包产物不同。
- 上游测试为本地真机实测，CI 侧未接入门禁（配方 `build()` 编测试、`test_package` 真机执行）。
- **软件级 `commands.json` 未新增（刻意）**：本配方 `package_type = "library"`、不含任何
  可执行交付物、也未声明 `cpp_info.bindirs`，按 R38 的机械判据（CI L0k 的
  `ci/conan/detect_bindirs.py`、create-pr 的 PF8）落在「库包」一侧——此时补
  `commands.json` 反而会被判「纯库包不应有」。
- **W3 本地 CI 的非阻塞告警（如实登记）**：`L4_RESULT=warn: dangerous functions in
  patches` —— 命中的是 `patches/0002-config.sub.patch`，那是 GNU config.sub 原文里本来就
  有的 `strcpy` 之类字符序列，不是我们引入的危险函数。
- `configure_options` 用 YAML 块列表书写；`finish` 第 [3/10] 步的 G0 `clean-verify` 重建在本包**硬失败**
  （`RESULT: FAIL`、`FAILED_STEP: configure`、`g0-configure.log` 报 `getcwd` 相关错误），
  属该步骤自身的重建缺陷而非配方问题——**同一 SHA 的 G2 `conan create` 干净轮同时是 PASS**
  （`reports/conan-create.log`、`reports/w3-local-ci.log` 的 `G2_RESULT`/`L0_RESULT` 可查），
  故按「非阻塞步骤」继续，**不写成通过**。

---

**编译结束**: 2026-09-20
**最终状态**: built（真机门禁通过：编译 + test_package 消费者 + 上游 10 用例执行）
