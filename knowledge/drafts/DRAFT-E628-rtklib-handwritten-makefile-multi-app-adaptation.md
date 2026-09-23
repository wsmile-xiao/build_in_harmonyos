# E-DRAFT E628: 手写 Makefile 多子工程（RTKLIB 形态）适配五件套

- **触发实例**：rtklib 2.4.3.b34 全新包适配（2026-09-20，任务 rtklib-2.4.3.b34，分支 `feat/rtklib-2.4.3.b34`）
- **上游**：`https://github.com/tomojitakasu/RTKLIB` tag `v2.4.3-b34`（sha256 `a9ce1329…461cf`）
- **类别**：无构建系统 / 手写 makefile / 源码布局 / 上游测试口径 / 静态链接
- **严重度**：2（可确定性复现；不影响库本身，但每条都会把排查方向带偏）

> 逐字输出留档：`$HOME/tmp/rtklib-2.4.3.b34/pipeline-logs/`、`$HOME/tmp/rtklib-2.4.3.b34/upstream-tests/`。

## 症状（五类，报错形态互不相似）

1. `init-build` 打印 **"✅ 嵌套源码提升完成: app/consapp → rtklib-2.4.3.b34.orig"**、
   **"✅ 基线指纹: 45 个文件"**——而真实源码有 928 个文件；`.work` 里没有 `src/`、`lib/`、`test/`。
2. `make -C app/consapp` 链接期：`ld.lld: error: cannot find ../../../../lib/iers/gcc/iers.a`。
3. 只编 `src/*.c` 时链接期：`undefined symbol: input_cresf / input_javadf / input_stqf …`。
4. `src/stream.c` 编译失败：`warning: implicit declaration of function 'gethostbyname'` +
   `error: incompatible integer to pointer conversion assigning to 'struct hostent *' from 'int'`。
5. `make: *** No rule to make target 'bin/convbin', needed by 'all'.  Stop.`（makefile 里明明写了规则）。

## 根因

### ① 大小写不敏感文件系统 + `_BUILD_MARKERS` 里的大写 `Makefile`

`ohc/init_build.py` 的 `_BUILD_MARKERS = ("configure", "CMakeLists.txt", "Makefile", "meson.build")`，
判定用 `(directory / m).exists()`。RTKLIB **根目录没有任何构建文件**，而 `app/consapp/` 有
`makefile`（小写）。设备文件系统大小写不敏感（`notes/device-facts.md` §一.3：
`os.path.samefile('MAN','man')` 为 True），于是 `app/consapp` 被 `_find_source_subdir` 认定为
"嵌套的源码根"并被**提升覆盖**整个 `.orig`/`.work`，根目录原有的 `src/ test/ util/ lib/ data/ doc/`
被 `shutil.rmtree` 删除。

后果的隐蔽性在于：工具只打印成功，`refresh-patch --auto` 之后的补丁路径会整体错位
（`convbin/gcc/makefile` 而不是 `app/consapp/convbin/gcc/makefile`），G2 上才炸。

**处置**（不改工具，属框架改动）：按 `--strip-components=1` 重建两个目录并重建指纹

```sh
B=$WORKSPACE_ROOT/tmp/builds; SHA=$(cat $B/<sw>-<ver>.orig/.tarball-sha256)
rm -rf $B/<sw>-<ver>.orig $B/<sw>-<ver>.work
mkdir -p $B/<sw>-<ver>.orig
tar xzf $B/<sw>-<ver>.tar.gz -C $B/<sw>-<ver>.orig --strip-components=1
printf '%s' "$SHA" > $B/<sw>-<ver>.orig/.tarball-sha256
cp -a $B/<sw>-<ver>.orig $B/<sw>-<ver>.work
python3 -c "import sys;sys.path.insert(0,'$TARGET_REPO/scripts');\
from ohc.edit_tracker import snapshot;snapshot('$B/<sw>-<ver>.work','<sw>','<ver>')"
```

并把 `manifest.yaml` 的 `build.system` 显式钉成 `makefile`（`clean_verify` 的 G0 入口探测
CMake > meson > configure > Makefile 对这类工程必然判错）。

### ② 每应用 makefile 的 `LDLIBS` 是"为作者本机写的"

`app/consapp/*/gcc/makefile` 的 `LDLIBS = ../../../../lib/iers/gcc/iers.a -lgfortran -lm -lrt`
无条件生效，而 IERS 的 Fortran 静态库只在定义 `-DIERS_MODEL` 时才有意义，上游 Linux 侧也不生成它
（`lib/iers/gcc/` 只有 makefile 与 `src/`）。**必须用命令行变量覆盖** `LDLIBS`。

### ③ `-ansi -pedantic` 在 musl 下隐藏 POSIX 声明

上游 `CFLAGS = -Wall -O3 -ansi -pedantic …`。`-ansi` 定义 `__STRICT_ANSI__`，musl 的 `netdb.h`
按它守卫 `gethostbyname` 的声明；clang 15 对隐式声明返回 `int` 再赋给 `struct hostent *` 是
**错误**（`-Wint-conversion`），不是警告。改用 `-std=gnu11` 后 `src/*.c` 31 个文件全量通过。

### ④ 源文件不在 `src/`

接收机原始日志解码器在 `src/rcv/`：`binex.c crescent.c javad.c novatel.c nvs.c rt17.c
septentrio.c skytraq.c ss2.c ublox.c`。只收集 `src/*.c` 会在**链接期**才暴露 `input_*f` 未定义。

顶层 makefile 用一句 `vpath %.c $(SRCDIR) $(SRCDIR)/rcv` + `$(OBJDIR)/%.o : %.c` 同时覆盖两层。

### ⑤ GNU make 的 pattern rule 前提只能有一个 `%`

`$(OBJDIR)/%.o : app/consapp/%/%.c` **不报语法错**，只是永远匹配不上（第二个 `%` 被当成字面量），
报错形态落在目标侧：`No rule to make target 'bin/convbin'`。逐应用写显式规则即可（本例 6 条，
`rtkrcv` 另带 `vt.c`）。

## 交付形态：静态链接从根上规避 RUNPATH/SONAME 家族

`libRTK.a` + 5 个全静态 CLI 使 `readelf -d` 只剩一条 `NEEDED libc.so`，
**`DT_RUNPATH`/`DT_RPATH` 完全不存在**，因此：

- 不存在"共享库无 `-Wl,-soname` → 互相链接时 `DT_NEEDED` 退化成相对路径 → 运行期 `Permission denied`"；
- 不存在"错误 RUNPATH 被 `conanrun` 注入的 `LD_LIBRARY_PATH` 掩盖、只有 CI 的 L2 裸 PATH smoke 才暴露"；
- `test_package` 里仍然要**裸环境**跑一遍（`env -u LD_LIBRARY_PATH <pkg>/bin/<tool> -h`，`rc==127` 即失败），
  这是一个零成本、与产物形态无关的强判据。

## 上游测试口径：N 是"makefile 注册的测试目标数"，不是统一 test 目录

这类工程没有测试框架，测试就是各 makefile 里的 `testN:`/`utestN:` 目标。取数：

```sh
cd <src>
tot=0
for m in $(find . -name makefile | sort); do
  n=$(grep -cE '^(test|utest)[0-9]+ *:' "$m")
  [ "$n" -gt 0 ] && { printf '%3d  %s\n' "$n" "$m"; tot=$((tot+n)); }
done
echo "N=$tot"
```

RTKLIB 2.4.3 b34 = **107**：`test/utest` 13 + `app/consapp/rnx2rtkp/gcc` 25 +
`rnx2rtkp/gcc_mkl` 25（同名前缀的 MKL 变体）+ `convbin/gcc` 18 + `str2str/gcc` 6 + `rtkrcv/gcc` 3 +
`util/rnx2rtcm` 11 + `util/testlex` 4 + `util/geniono` 2。

三条判读纪律：

1. **空配方目标不能记 PASS**：`test/utest/makefile` 的 `utest10:` 配方整行被注释掉，
   `make utest10` 返回 **rc=0 且什么都不做**。判据必须是"rc=0 **且**产出文件存在"，
   否则会凭空多一个假绿。
2. `make` 的 rc 就是配方命令的 rc，所以断言崩溃（`Assertion failed` → SIGABRT / rc=134）能被正确捕获；
   但上游这些目标**只跑不判**（没有期望输出比对），报告里必须如实写成 smoke 性质。
3. 差额要逐项归因到"上游源码/夹具问题"还是"环境问题"：本包 13 个 utest 目标里
   `utest2`(t_time.c 用了未声明的 `j`)、`utest4`(t_rinex.c 引用已移除的 `nav_t.leaps`)
   是**上游测试源码编译不过**；`utest8/9/11` 依赖本版本不存在的 `src/qzslex.c`；
   `utest14` 是**上游夹具与解析器不匹配**（`tle_sgp4.txt` 的星名写在别名行，
   而 `tle_pos()` 查的是只由 `0 NAME` 行填充的 `tled_t::name`）。

## 复现命令

```sh
sh $HOME/tmp/rtklib-2.4.3.b34/run_upstream_tests.sh \
   $HOME/ws/tmp/builds/rtklib-2.4.3.b34.work \
   $HOME/tmp/rtklib-2.4.3.b34/upstream-tests
# 产出 $HOME/tmp/rtklib-2.4.3.b34/upstream-tests/results-A.tsv 与 results-B.tsv
#（各 107 行，逐条 PASS/FAIL/NOT_RUN/TIMEOUT + 原因；RUN_ID 环境变量决定后缀）
```

## 相关

- `notes/device-facts.md` §一.3（大小写不敏感文件系统是**破坏性**事实）、§二.19（test_package 真跑消费者）
- `DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing`（同为 raw makefile + OHOS 交付；那条讲代码签名，本条讲构建入口与源码布局）
- `DRAFT-libharu-2.3.0-missing-dt-soname`（共享库路线下必须处理的面；本条给出"静态路线不需要处理"的对照）
