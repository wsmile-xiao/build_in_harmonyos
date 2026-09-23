# libfstngram 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-20
- 编译器: clang/clang++（`clang version 15.0.4`）
- 状态: built（真机门禁通过：编译 + `test_package` + 上游 10 用例全过）

## 库定位

libfstngram 是 openfst-1.8.4 的 NGramFst 扩展子库：LOUDS（Level-Order Unary
Degree Sequence）位图压缩的 n-gram 语言模型 FST。本包按默认 `shared=False`
（`--enable-static --disable-shared`）构建，**交付静态库 `libfstngram.a`**
（上游 `-version-info 26:0:0`，`shared=True` 时对应 `libfstngram.so.26`；
`find <pkg> -name '*.so*'` 为空是预期结果）、`lib/fst/ngram-fst` 扩展模块，以及
`include/fst/extensions/ngram/{ngram-fst,bitmap-index,nthbit}.h`。
源码包与同 tarball 兄弟包 `libfst` / `libfstconst` **同为 `openfst-1.8.4.tar.gz`**
（sha256 `a8ebbb6f…8016`）；上游 configure 用 `--enable-ngram-fsts` 单独打开本扩展
（configure.ac:87，默认 `no`）。

## 配方策略

- 源码：复用 openfst-1.8.4.tar.gz（sha256 与 libfst/libfstconst 配方一致）
- 补丁：复用 openfst 1.8.4 已验证的 4 个平台补丁（config.guess / config.sub /
  configure umask / `--help` 退出码），逐条 `git apply --check` 通过
- 构建开关：`--enable-ngram-fsts --enable-bin --enable-static --disable-shared`
  （与已合并兄弟包 libfstconst 同形态，只把 `--enable-const-fsts` 换成本扩展开关）
- Conan 包名：libfstngram，`cpp_info.libs = ["fstngram"]`
- 并发：`autotools.make(args=["-j2"])`（设备 `os.cpu_count()=20` 但 affinity=8，
  且 `conan create` 不传 `tools.build:jobs`，配方内显式限制）

## 上游测试用例审计

`make check` 的入口是 `src/test/Makefile.am`：
`check_PROGRAMS = fst_test weight_test` + `algo_test_{log,tropical,minmax,lexicographic,power}`
共 7 个，`TESTS = $(check_PROGRAMS)`；`BUILD.bazel` 里对应的 `cc_test` 也是同 7 个
（1 + 1 + `algo_test_%s` × 5 个 weight，见 BUILD.bazel:310/330/345）。**同 tarball
子包按父 tarball 全量清点面取最大值**，四个候选口径逐项如下：

| # | 口径 | 读数 | 取数命令 |
|---|------|------|----------|
| 1 | autotools 注册（`check_PROGRAMS`/`TESTS`） | 7 | `grep -c 'check_PROGRAMS' src/test/Makefile.am` + 逐行展开 |
| 2 | Bazel 注册（`cc_test`） | 7 | `BUILD.bazel:310/330/345`（含 `for weight in [tropical, log, minmax, lexicographic, power]`） |
| 3 | 测试源文件数 | 3 | `ls src/test/*.cc` |
| 4 | **用例分支数（取此最大口径 → N）** | **10** | 2 个独立测试程序 + `algo_test.cc` 的 8 个 `TEST_*` 分支 = 10 |
| — | 断言行数（另一单位，仅披露、不并入 N） | `CHECK` 宏 260 处 | `grep -o 'CHECK' src/test/*.cc src/include/fst/test/*.h \| wc -l` |

`src/test/algo_test.cc:66-88` 定义 8 个互斥的 arc 分支：`TEST_TROPICAL`、`TEST_LOG`、
`TEST_MINMAX`、`TEST_LEFT_STRING`、`TEST_RIGHT_STRING`、`TEST_GALLIC`、
`TEST_LEXICOGRAPHIC`、`TEST_POWER`。其中 **5 个**（tropical/log/minmax/lexicographic/power）
在 Makefile.am 与 BUILD.bazel 均注册；**3 个**（left_string/right_string/gallic）
在两套构建系统中都**没有**注册项（无对应的 `check_PROGRAMS`/`cc_test`）。
`WeightGenerate` 对 `StringWeight`/`GallicWeight` 的特化在 `fst/string-weight.h:514/667`
（`algo_test.cc` 已 include），故这 3 个分支可编译可运行，本配方一并构建执行以覆盖最大
清点口径 —— **10 个用例全部真机执行，10 PASS / 0 FAIL / 0 SKIP / 0 NOT_RUN**。

| # | 用例 | 来源分支 | 上游注册 |
|---|------|----------|----------|
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
`-D` 宏与链接参数；`make check` 本身未使用（它会在精简构建下因扩展模块动态加载假败）。

## 验证步骤

1. `conan create libfstngram/1.8.4` — 应用 4 个补丁 + `configure` + `make -j2`
   + 手动编译 10 个上游测试程序
2. `make install` — 走配方内 install shim（OHOS 无 GNU install，toybox `install -c`
   在 HMDFS 上 Error 64）
3. `test_package` — `check_libfstngram.sh` 校验产物 + 头文件 + `NGramFstImpl` 符号指纹；
   随后真机逐个执行包内 `_ohos_tests/` 的 10 个上游测试程序

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make check` 会假败（`Fst::Read` 找不到 `vector-fst.so`） | 链接 `libfst.a` 时链接器按需取对象文件，`fst-types.o` 的 `static FstRegisterer` 无强引用被剔除 → 注册表空 → `GenericRegister::GetEntry` 回退 `dlopen("<type>-fst.so")` 失败 | 手动 `clang++` 编 10 个测试程序，链接时 `-Wl,--whole-archive libfst.a -Wl,--no-whole-archive` 强制保留全部 `REGISTER_FST` 符号 |
| 2 | `make install` 报 `install: ... Error 64` / 头文件权限失败 | E182/E087：OHOS worker 无 GNU install，toybox `install -c` 在 HMDFS 上失败；HMDFS 也不支持 `chmod` | 配方写 install shim（`cp -f` + `mkdir -p`，chmod 容错），`sed` 把各 Makefile 的 `INSTALL = <toybox install>` 改为指向 shim（`INSTALL_DATA/PROGRAM` 随 `${INSTALL}` 重算） |
| 3 | 测试程序进包后 `Error 126 Permission denied` | E087：HMDFS 不支持 chmod，`open("wb")` 落盘 0644 无执行位 | `package()` 用 `os.open(..., 0o755)` 创建带执行位的目标文件 |
| 4 | test_package 执行 `check_libfstngram.sh` 被拒 | 同上，脚本文件无执行位 | 用 `sh <script>` 显式调解释器（`test_package/conanfile.py`） |

## 源码修改

无源码级修改；4 个补丁均为平台可移植性补丁（与 libfst/libfstconst 完全相同）：

| 补丁 | 内容 |
|------|------|
| `0001-config.guess.patch` | 更新到 automake 1.18 的 config.guess（识别 `HarmonyOS`/`aarch64-unknown-linux-ohos`） |
| `0002-config.sub.patch` | 同步 config.sub（接受 `linux-ohos*` triplet） |
| `0003-configure.patch` | configure 生成临时目录的 `umask 077` → `022`（HMDFS 权限边界，E011） |
| `0004-flags-help-exit.patch` | `src/lib/flags.cc` 显式 `--help`/`--helpshort` 返回 0 而非 1 |

## 依赖版本

无外部依赖（`conan install --build=never` 检查 0 个引用）。

## 验证结果

```bash
# 干净轮（清缓存后）真机执行
conan create archives/l/libfstngram/1.8.4 -pr:h=<ohos-aarch64 profile> --build=missing
# 上游 10 用例（test_package 真机运行包内 _ohos_tests/）
#   10 PASS / 0 FAIL / 0 SKIP / 0 NOT_RUN → 10/10（100%）
```

## 注意事项

- 上游 7 个注册用例是 openfst **整体**测试（测 VectorFst、各 arc type、各扩展运行时注册），
  子库配方若 `--disable-bin` / 关掉扩展，`lib/fst/` 下的扩展模块不编、注册表不全 → 假败。
  本配方照同 tarball 兄弟包全开构建，包内含完整 openfst 运行面（`libfst.a`、`libfstscript.a`、
  `libfstngram.a`、`lib/fst/ngram-fst.a`，以及 37 个 `bin/` 命令；均为静态，见「库定位」）。
- 上游测试为本地实测，CI 侧未接入门禁（配方 `build()` 编测试、`test_package` 真机执行）。
- 本包与 `libfst` / `libfstconst` 共享同一 tarball：三者补丁、sha256 一致，仅 configure
  扩展开关与 `cpp_info.libs` 不同；`--enable-ngram-fsts` 之外的扩展仍为上游默认 `no`。

---

**编译结束**: 2026-09-20
**最终状态**: built（真机门禁通过：编译 + test_package + 上游 10 用例全过）
