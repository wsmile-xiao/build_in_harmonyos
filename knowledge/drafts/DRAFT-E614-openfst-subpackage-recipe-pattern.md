# E-DRAFT E614: 同 tarball 子包（OpenFST 家族）配方形态

- **触发实例**：libfstlookahead 1.8.4 全新包适配（2026-09-20，任务 libfstlookahead-1.8.4，分支 feat/libfstlookahead-1.8.4）
- **同族先例**：`archives/l/libfstconst/1.8.4`（已合并）、`archives/o/openfst/1.8.4`（父包全量）
- **类别**：autotools 子包构建 / 静态注册表链接
- **严重度**：2（流程固定、可确定性复现；不影响库本身）

> 实测读数已回填（2026-09-20，采信轮干净轮 + `repro-e614-openfst-subpackage.sh`）；
> 逐字输出留档 `$HOME/tmp/libfstlookahead-1.8.4/repro-e614-output.txt`。

## 症状（三类）

1. `configure` 后**扩展库根本没编**——包内只有 `libfst`/`libfstscript`/`bin`，没有 `lib<ext>.so`。
2. 手工编译的上游测试或消费者程序**链接通过、运行时崩**：
   `Fst::Read: Unknown FST type vector (arc type = standard)` → `GenericRegister::GetEntry: ... vector-fst.so`
   （dlopen 回退失败）。
3. `make install` 在设备上 `install: ... Error 64`（toybox `install -c` 在 HMDFS 上失败）。

## 根因（对应三类）

### ① 扩展开关默认 `no`，`--enable-bin` 默认 `yes`

`configure.ac`（openfst-1.8.4）里每个扩展都是：

```m4
AC_ARG_ENABLE([lookahead-fsts], [...], [], [enable_lookahead_fsts=no])
AM_CONDITIONAL([HAVE_LOOKAHEAD], [test "x$enable_lookahead_fsts" != xno])
```

而 `bin`（fst::script + 命令行）默认 **yes**。于是：

| 写法 | 结果 |
|---|---|
| 不传任何 `--enable-*` | 只有核心库 + bin（**没有**任何扩展库） |
| `--enable-lookahead-fsts` | libfstlookahead + 3 个模块（arc/ilabel/olabel_lookahead-fst） |
| `--enable-lookahead-fsts --enable-bin` | 同上 + bin（bin 本就默认开，显式写是为了钉住默认值） |

子包**不需要**写 `--disable-<其它扩展>`（默认即关）。

### ② 上游注册面 = 7，子包不裁剪

`src/test/Makefile.am`：

```make
check_PROGRAMS = fst_test weight_test
check_PROGRAMS += algo_test_log
check_PROGRAMS += algo_test_tropical
check_PROGRAMS += algo_test_minmax
check_PROGRAMS += algo_test_lexicographic
check_PROGRAMS += algo_test_power
TESTS = $(check_PROGRAMS)
```

`BUILD.bazel` 的 `cc_test` 是**同一组 7 项**（`fst_test`、`weight_test`、`algo_test_%s` 循环
`tropical/log/minmax/lexicographic/power`）。源码面 3 个 `.cc`（`algo_test.cc` 被 5 个宏各编一份），
无 CMake/pytest 测试目标。→ 声明 N 取注册面最大值 **7**，与父 tarball 一致（子包不裁剪 ⇒ 无差额）。

### ③ 静态库链接吃掉 `REGISTER_FST` 静态注册器

`fst/fst.h:266`：

```cpp
const auto reader = FstRegister<Arc>::GetRegister()->GetReader(fst_type);
if (!reader) { LOG(ERROR) << "Fst::Read: Unknown FST type " << fst_type ... }
```

`GetReader` → `GenericRegister::GetEntry`，查不到就 `dlopen("<type>-fst.so")` 回退
（`generic-register.h:78-110`）。注册项来自 `REGISTER_FST(...)` 展开的**静态对象**；
链 `libfst.a` 时无强引用的对象文件被剔除 → 注册表空 → 回退 dlopen 也失败。

上游 `make check` 走 libtool 动态链，天然绕开；**手工编译消费者必须**：

```sh
-Wl,--whole-archive <build>/src/lib/.libs/libfst.a -Wl,--no-whole-archive -lm -ldl
```

## 复现

```sh
TASK_DIR=$HOME/tmp/libfstlookahead-1.8.4
sh "$TASK_DIR/repro-e614-openfst-subpackage.sh" [可选 libfst.a 路径]
```

脚本打印：①`configure.ac` 各扩展开关默认值（实测：11 个扩展全 `no`，只有 `enable_bin=yes`）；
②`src/test/Makefile.am` 的 `check_PROGRAMS` 与 `BUILD.bazel` 的 `cc_test` 两处注册面（都 = 7）；
③`src/test/*.cc` 源文件数与 `weight_test.cc` 的断言位点（59）；④无/有 `--whole-archive` 两种链接下的读数。

实测读数（2026-09-20，libfst.a 取采信轮安装树）：

```text
-- 不用 --whole-archive（链接器按需取对象文件） --
ERROR: GenericRegister::GetEntry: Error loading shared library vector-fst.so: No such file or directory
   FstRegister<StdArc>::GetEntry("vector").reader = NULL
ERROR: GenericRegister::GetEntry: Error loading shared library const-fst.so: No such file or directory
   FstRegister<StdArc>::GetEntry("const").reader = NULL
   ⇒ 注册表缺项（rc≠0）
-- 用 --whole-archive 包夹 libfst.a（未链扩展库） --
   FstRegister<StdArc>::GetEntry("vector").reader = present
   FstRegister<StdArc>::GetEntry("const").reader = present
ERROR: GenericRegister::GetEntry: Error loading shared library arc_lookahead-fst.so: No such file or directory
   FstRegister<StdArc>::GetEntry("arc_lookahead").reader = NULL
   ⇒ 仍有缺项（rc≠0）：扩展库必须一并包夹
```

即：**核心库与扩展库两条都要进 `--whole-archive` 组**；只包夹核心库会让核心类型恢复、
扩展类型继续 NULL（这正是"看起来像子包没编出来"的误判来源）。

## 本任务的验证结果（同族可对照）

`libfstlookahead 1.8.4` 真机采信轮（清缓存干净轮）`conan create` + `test_package`：
上游 `HMBS_UPSTREAM_TEST_RESULT` = `status=passed, discovered=7, executed=7, passed=7, failed=0, skipped=0`；
鸿蒙侧 `HMBS_CONSUMER_ASSERTIONS` = `total=16, passed=16, failed=0`（注册表 3 项 reader + 构造/弧/终态/类型 +
`Matcher`/`LookAheadMatcher` 语义 + 写出后经 `Fst<StdArc>::Read` 读回）+ 产物/头文件检查 9 项。


## 与既有条目的关系

- **E182/E188**（toybox `install -c` 在 HMDFS 失败）：本条只引用其 install shim 处置形态，不重复。
- **E007**（config.guess/config.sub 平台识别）：同族先例的 4 个补丁继续复用（config.guess/config.sub/configure umask/`--help` 退出码）。
- **libgmpxx 子包少报判例**（同 tarball 子包按父 tarball 全量注册面量）：本条给出**反例形态**——
  OpenFST 家族的父 tarball 注册面本身就是 7，子包不裁剪即自然对齐；关键动作是**先数父 tarball 的两处注册面**再声明。
