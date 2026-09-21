# libfstlookahead 1.8.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS SDK 15.0.4，`/data/service/hnp/bin/clang++`）
- 设备: HarmonyOS PC（aarch64），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built（真机门禁通过：干净轮 `conan create` + `test_package` + 上游 7 项全过）

## 库定位

libfstlookahead 是 openfst-1.8.4 的 **LookAheadFst 扩展子库**，与已合并的 `archives/o/openfst/1.8.4`、
`archives/l/libfstconst/1.8.4` **共用同一 tarball** `openfst-1.8.4.tar.gz`
（实测 sha256 = `a8ebbb6f3d92d07e671500587472518cfc87cb79b9a654a5a8abb2d0eb298016`，与两个同族包逐字一致）。

交付物：

| 产物 | 说明 |
|---|---|
| `lib/libfstlookahead.a`（或 `.so.26`） | `-version-info 26:0:0`；3 个注册器 TU（arc/ilabel/olabel_lookahead-fst.cc） |
| `lib/fst/{arc,ilabel,olabel}_lookahead-fst.a`（共享构建为 `.so`） | 上游 `libfst_LTLIBRARIES` 模块（`-avoid-version -module`） |
| `lib/libfst.a` | 同 tarball 的核心库（上游 7 个 check_PROGRAMS 只链它） |
| `include/fst/lookahead-matcher.h`、`include/fst/matcher-fst.h` | 扩展类型 `StdArcLookAheadFst` / `StdILabelLookAheadFst` / `StdOLabelLookAheadFst` 与注册类型名 |

> 本包**不构建** `bin/` 与 `libfstscript`（显式 `--disable-bin`）：src/bin 无 lookahead 专用工具、
> 上游测试不依赖它们，且这两部分占整包编译量约 80%。需要 fst\* 命令行请用 `openfst/1.8.4`。

## 配方策略

### 与同族先例 `libfstconst/1.8.4` 的差异（显式登记）

同族已合并先例 `archives/l/libfstconst/1.8.4` 的 `conanfile.py:131-140` 与 `notes.md` 明确警告：

> 「子库配方若 `--disable-*-fsts`/**`--disable-bin`**，注册表缺 vector、`lib/fst/*.so` 不编，
> `Fst::Read` 回退 `dlopen("vector-fst.so")` **假败**。故本配方照 openfst 完整配方全开构建
> （**`--enable-bin`** + 不 disable 扩展），包内含完整 openfst 产物供测试运行时找注册符号与扩展模块。」

**该警告对本包不适用，逐条对照如下**（本包只关 `bin`、**没有**关任何扩展）：

| 先例警告的成因 | 本包状态 |
|---|---|
| `--disable-*-fsts` 导致注册表缺 vector 类型 | 本包 `--enable-lookahead-fsts` 打开本扩展；`vector`/`const` 等核心类型的 registerer 在 **libfst 自身**（`src/lib/fst-types.cc`，24 处 `REGISTER_FST`），与 `bin` 开关无关；实测 `--disable-bin` 构建下 `FstRegister<StdArc>::GetEntry("vector").reader` = present |
| `lib/fst/*.so` 不编导致 dlopen 回退失败 | `lib/fst/` 下 3 个 lookahead 模块由 `--enable-lookahead-fsts` 控制（**保留**）；`bin` 不产出 `lib/fst/*` 任何模块 |
| 测试运行时找不到注册符号 / 扩展模块 | 上游 7 个 check_PROGRAMS 在 `src/test/Makefile.am` 里 `LDADD = ../lib/libfst.la`，**无 `HAVE_BIN` 条件**——它们只链核心库；本次真机逐项执行给出逐用例结果，且 `fst_test` 确实在读 FST（见「验证步骤」的逐字输出） |

关 `bin` 的收益与依据：`src/script`(47 TU) + `src/bin`(74×2 TU) 占整包编译量约 80%，在设备共享窗口下
22 分钟只能编完 11/47 个 script TU，而 G2 的 `conan create` 超时在 `conan_verify.py:751` **硬编码 3600s**
（`--timeout`/`OHC_W3_TIMEOUT` 均不作用于它）；`grep -l lookahead src/bin/*.cc` 为空（无 lookahead 专用 CLI）。
**需要 `fst::script` 与命令行工具请用 `openfst/1.8.4`**（命令行属该包交付面）。

- 源码：复用 openfst-1.8.4.tar.gz（`conandata.yml` 的 URL/sha256 与同族包一致，官方源，未改）
- 补丁：复用同族已验证的 4 个平台补丁（config.guess / config.sub / configure umask / `--help` 退出码），
  与 `archives/o/openfst/1.8.4/patches/` 逐字节一致（`cmp` 实测）
- 构建开关：`--enable-lookahead-fsts`（本扩展）+ `--disable-bin`（库子包最小化，见下）
  - `configure.ac` 里 `const/compact/far/linear/lookahead/mpdt/ngram/pdt/python/special`
    各扩展默认值都是 **`no`**（子包必须显式开自己那一个），而 `--enable-bin`（fst::script + 37 个 fst\*）默认 **`yes`**
  - 显式 `--disable-bin` 的依据：①`grep -l lookahead src/bin/*.cc` 为空——上游 1.8.4 没有 lookahead 专用命令行；
    ②`src/test/Makefile.am` 的 `LDADD = ../lib/libfst.la`、无 `HAVE_BIN` 条件——上游 7 个测试不依赖 bin；
    ③src/script(47 TU) + src/bin(74×2 TU) 占整包编译量约 80%，设备高负载实测 22 分钟只编完 11/47 个 script TU，
    开着 bin 会让 G2/CI 的 3600s 硬预算必然超时；④fst\* 命令行的交付面属 `openfst/1.8.4` 包
- 链接口径：`cpp_info.libs = ["fstlookahead"]`；`runenv_info` 追加 `lib`、`lib/fst` 到 `LD_LIBRARY_PATH`
- install：`package()` 前把生成的 Makefile 里 `INSTALL = <toybox install -c>` 改指 cp/mkdir shim
  （HMDFS 上 toybox `install -c` 报 Error 64；同族已验证形态）

## 上游测试用例审计（AGENTS §3.5 / rule4）

**计数单位 = automake `check_PROGRAMS`（`TESTS = $(check_PROGRAMS)`），两种注册面都数过：**

| # | 候选口径 | 读数 | 取数命令 |
|---|---|---|---|
| A | 注册面：`src/test/Makefile.am` 的 `check_PROGRAMS` / `TESTS` | **7** | `grep -c 'check_PROGRAMS' src/test/Makefile.am` → 6 行（1 基础 + 5 `+=`）→ 展开 7 项；`grep -n 'TESTS' ` → `TESTS = $(check_PROGRAMS)` |
| B | 注册面：`BUILD.bazel` 的 `cc_test` | **7** | `fst_test` + `weight_test` + `algo_test_%s`（循环 `tropical/log/minmax/lexicographic/power`）= 2 + 5 |
| C | 源文件面：`src/test/*.cc` | 3 | `fst_test.cc`、`weight_test.cc`、`algo_test.cc`（后者被 5 个宏各编一份） |
| D | CMake `add_test` / pytest 目标 | 0 | 无 `CMakeLists.txt`；`src/extensions/python/` 无测试文件 |
| E | assertion 面（**另一单位，不并入 N**） | 59+ | `weight_test.cc` 内 59 处 `CHECK`；`fst_test`/`algo_test` 经 `fst/test/*.h` 宏 |

**主 N = max(A, B) = 7**（父 tarball 注册面）。本子包**不裁剪上游测试面**（`src/test` 不随扩展开关变化），
故 N 与父 tarball 相同、差额 0；声明的 7 与实测 7 一致。

7 个程序（真机逐项执行，退出码统计）：

| # | 程序 | 源 | 说明 |
|---|---|---|---|
| 1 | fst_test | src/test/fst_test.cc | FST 读写/拷贝/属性/IO（含 `Fst::Read` 注册表分派与 tmpdir 往返） |
| 2 | weight_test | src/test/weight_test.cc | 权重半环语义 |
| 3 | algo_test_log | algo_test.cc `-DTEST_LOG` | LogArc 算法回归 |
| 4 | algo_test_tropical | `-DTEST_TROPICAL` | StdArc 算法回归 |
| 5 | algo_test_minmax | `-DTEST_MINMAX` | MinMaxArc |
| 6 | algo_test_lexicographic | `-DTEST_LEXICOGRAPHIC` | LexicographicArc |
| 7 | algo_test_power | `-DTEST_POWER` | PowerWeight |

**统计（单位同上）**：TOTAL = PASS + FAIL + SKIP + NOT_RUN = 7 = 7 + 0 + 0 + 0。
真机逐项读数（未跑 `make check` 的汇总，而是逐项执行 + 退出码）：7/7 PASS。

**鸿蒙侧新增用例（另一栏，不并入上游分母）**：25 项 ——
`test_package/lookahead_consumer.cc` 16 项断言（真机用**包内安装产物**现场编译执行：
`FstRegister<StdArc>::GetRegister()->GetEntry("<type>").reader != nullptr` ×3、构造/状态/弧/终态/类型、
`Matcher` 与 `LookAheadMatcher` 语义、写出后经注册表 `Fst<StdArc>::Read` 读回）
＋ `test_package/check_libfstlookahead.sh` 9 项产物与头文件声明检查。合计 25/25 PASS。

## 验证步骤（真机）

```sh
. "$HOME/tmp/libfstlookahead-1.8.4/env.sh"
sh "$HOME/ws/tools/conan_verify_round.sh" libfstlookahead 1.8.4 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

采信轮内含清缓存四步 + `conan-verify`（G0–G4/L2/L4/L5）+ 证据副本三份 + finish 前快照；
`conan create` 日志中 test_package 段打印 `HMBS_TEST_PACKAGE_RESULT`、`HMBS_CONSUMER_ASSERTIONS`、
`HMBS_UPSTREAM_TEST_RESULT` 三行标记，用例数即由此复算。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `init-build --auto` 找不到源码（4 个候选 URL 全是 `libfstlookahead-1.8.4.tar.gz` 形态，实测不存在） | 搜索按**包名**拼 URL，而本包是 openfst 的子库（tarball 名是 `openfst-1.8.4.tar.gz`）；HEAD 探测对这些不存在的路径是假阳性 | 显式传官方 URL：`--url https://openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.4.tar.gz` |
| 2 | 手工编译上游测试可链接但运行期崩（`Fst::Read: Unknown FST type vector` → dlopen 回退失败） | `REGISTER_FST` 的静态 registerer 无强引用被链接器剔除 | 链 `libfst.a` 时 `-Wl,--whole-archive … -Wl,--no-whole-archive` |
| 3 | `fst_test` 会向 `FST_FLAGS_tmpdir`（默认 `TMPDIR`，回落 `/tmp`）写文件，设备 `/tmp` 只读 | 上游 `flags.cc:31-36` 读环境变量；test_package 继承的环境不保证 | test_package 显式传 `--tmpdir=<可写目录>`，不依赖继承环境 |
| 4 | `make install` 头部文件安装失败（toybox `install -c`，HMDFS Error 64） | HMDFS 不支持 chmod / toybox install `-c` 行为 | 生成 cp/mkdir 版 install shim 并 sed 改写 Makefile 的 `INSTALL` 变量 |
| 5 | 消费者程序首版编译失败：`no member named 'NumStates' in 'fst::Fst<...>'` | `NumStates()` 属 `ExpandedFst`，不属 `Fst` | 读回后 `dynamic_cast<const fst::ExpandedFst<Arc>*>` 再取 `NumStates()` |
| 6 | 测试程序随包安装后无执行位（HMDFS 不支持 chmod） | `open(...,"wb")` 默认 0644 | `os.open(dst, ..., 0o755)` 落盘执行位（同族形态） |
| 7 | 开着上游默认的 `--enable-bin` 时，构建在设备高负载下**不可能**在 G2/CI 的 3600s 硬预算内完成（实测 22 分钟只编完 11/47 个 `src/script` TU，`src/bin` 还有 148 个 TU 未开始） | `configure.ac` 的 `enable_bin=yes` 默认值把 `src/script`(47 TU) + `src/bin`(74×2 TU) 一起打开，占整包编译量约 80%；而 G2 的 `conan create` 超时在 `conan_verify.py` 里**硬编码 3600s**（`--timeout`/`OHC_W3_TIMEOUT` 都不作用于它） | 显式 `--disable-bin`：本包是库包、src/bin 无 lookahead 专用工具、上游 7 个测试只链 `libfst.la`；关掉后编译量降到约 20% |

## 注意事项

- 本包与 `openfst/1.8.4`、`libfstconst/1.8.4` 同源同 tarball：三者 `conandata.yml` 的 URL/sha256 必须保持一致，
  任一升级都要同步（本包 README 已写明）。
- 静态构建（默认 `shared=False`）下扩展模块是 `lib/fst/*.a`；共享构建才产生可 dlopen 的 `.so`。
  本包的消费者验证走「注册表查询 + 读回」，两种形态都可验证。
- 上游 7 项是 openfst **整体**回归（不针对 lookahead 扩展）；扩展自身可用性由鸿蒙侧 16 项消费者断言覆盖。
  这是子包证据的固有分工，不是"上游测试没跑"。
- 上游测试为本地真机实测；CI 侧 `can_run=False` 走产物布局分支（跨构建不可执行），与同族包一致。

## 知识增量评估（路径 B）

本任务沉淀出可复用增量，已建草稿 **E614**（`knowledge/drafts/DRAFT-E614-openfst-subpackage-recipe-pattern.{kv,md}`）：
同 tarball 子包的「三坑一形态」——①扩展开关默认 `no` 而 `bin` 默认 `yes`；②父 tarball 注册面要先数
两处（automake + Bazel）再声明 N；③`REGISTER_FST` 静态注册器必须 `--whole-archive`，以及
「注册表查询 + 写读回」作为扩展可用性的可执行证据形态。

---

**编译结束**: 2026-09-20
**最终状态**: built（真机门禁通过：干净轮 conan create + test_package 25/25 + 上游 7/7）
