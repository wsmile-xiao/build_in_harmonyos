# E678（草稿）：autotools 包在 HarmonyOS + HMDFS 上的 configure 双杀——`config.guess` 不认 uname（第一关）与 `umask 077` 临时目录不可写（第二关）必须成对处理

> Draft: DRAFT-E678-SOLLYA-AUTOTOOLS-CONFIG-GUESS-STATUS-HMDFS-HARMONYOS
> Stem: `DRAFT-E678-sollya-autotools-config-guess-status-hmdfs-harmonyos` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-E678-SOLLYA-AUTOTOOLS-CONFIG-GUESS-STATUS-HMDFS-HARMONYOS
- **严重度**: 2
- **类别**: platform | portability | autotools | hmdfs-permission
- **触发工具**: configure | make | autoreconf
- **阶段**: compilation | configuration
- **来源任务**: sollya 8.0（任务卡 10797）W0 原生探索「一跑一修」R1→R6
- **关联既有条目**: **E114**（HMDFS `umask 077`/`0700` → `drwx--S---`）、`device-facts §一.10`（目录模式落盘后不可改、属主映射）、`§一.13`（mkfifo jobserver 噪声）

## 错误特征（逐字，`error_signature` 5 条子模式对 5 条原文实测 **5/5 命中、零死签名**）

**第一关（`config.guess`）**：

```
checking build system type... ./build-aux/config.guess: line 125: /storage/Users/currentUser/ws/tmp/cgJCKBKk/dummy.c: Permission denied
./build-aux/config.guess: line 1621: /storage/Users/currentUser/ws/tmp/cgJCKBKk/dummy.c: Permission denied
./build-aux/config.guess: unable to guess system type

This script (version 2026-05-17), has failed to recognize the
operating system you are using.
uname -m = aarch64
uname -r = HongMeng Kernel 1.12.0
uname -s = HarmonyOS
configure: error: cannot guess build type; you must specify one
```

**第二关（`config.status`）**——即便给了 `--build` 绕过第一关，仍会在这里炸：

```
checking that generated files are newer than configure... done
configure: creating ./config.status
./config.status: line 873: ./confimdpcH/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**同根源第三种表现（链接期）**：

```
CXXLD    libsollya.la
libtool: link: clang++ -fPIC -DPIC -shared -nostdlib … -L…/usr/local/lib -lstdc++ -L<SDK …> … -lc++ -lc++abi …
ld.lld: error: unable to find library -lstdc++
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
make: *** [Makefile:793: libsollya.la] Error 1
```

## 根因分析

两个 configure 失败点**同源于**「上游发布形态为 git 归档 / 只带 `configure.ac`、须 `autoreconf` bootstrap」的包在 HarmonyOS + HMDFS 上的环境差异，且是**串联的两道关**：

1. **第一关 · 平台识别**：`build-aux/config.guess`（2026-05-17 版）读到 `uname -s = HarmonyOS`、`uname -r = HongMeng Kernel 1.12.0` 无法归类，转入 fallback 分支 `set_cc_for_build` 自建临时目录写 `dummy.c` 编译探测。
2. **第二关 · 临时目录权限**：该 fallback 与 `config.status` 自身都用 `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")` / `./confXXXXXX` 建临时目录，而 **HMDFS 强制给目录加 setgid 并按共享属主映射落盘**。**A/B 对照实测**：

   | 建目录方式 | 落盘 mode | uid | 结果 |
   |---|---|---|---|
   | `(umask 077 && mktemp -d)`（config.guess 同款） | **`0o2700`** | `20001006` | **WRITE FAIL: Permission denied** |
   | 普通 `mkdir(0o700)`（对照组） | `0o2771`（文件系统增益 group rwx） | `20001006` | write ok |

   进程侧：`euid=20020085`、目录 `gid=1006 group=file_manager` **不含该 egid** ⇒ 走 other 位 ⇒ `02700` 的 other 为 `0` ⇒ 不可写。

3. **为什么只改 `AC_COMPILE_IFELSE → AC_LINK_IFELSE` 修不了**（省一轮的关键推论）：`configure.ac:678-690` 用 `AC_COMPILE_IFELSE`（**只编译不链接**）去测链接选项 `-lstdc++` ⇒ 恒成功 ⇒ `ADD_LSTDC` 恒 `yes` ⇒ `LIBS` 恒保留（生成 `Makefile:425 LIBS = … -lstdc++` 可证）；而即便改成 `AC_LINK_IFELSE`，configure 阶段走的是**裸 clang**（无 libtool `-nostdlib`、无 `-L` 位置约束，`config.log` 可证）**也会通过**，无法复现 `make`/`config.status` 期的失败。⇒ 必须**无条件**给三元组 + **无条件**剥 `umask 077`。

4. **同根源第三种表现（`-lstdc++`）三层叠加**：① libtool 链 `.so` 必加 `-nostdlib` ⇒ clang driver 不再注入标准库处理、**不做 `-lstdc++→libc++` 内部映射**；② 硬编码 `-lstdc++` **排在 SDK `-L` 路径之前**，而 **lld 按位置向左解析 `-L`**（未来 `-L` 不生效）；③ 文件系统**无 `libstdc++` 实体**（`find -name 'libstdc++*'` 空；SDK `lib/aarch64-linux-ohos/` 只有 `libc++.a/.so/libc++_shared.so/libc++abi.a`）。裸 driver 环境 `clang++ -lstdc++` 直读 rc=0（driver 内部映射生效），**这不能代表 make 环境**——两环境差异即上面 ①②。

## 修复方案（两步成对 + 一条顺序硬约束）

**第一步（绕第一关）**：configure 显式加 GNU 三元组

```sh
./configure --build=aarch64-unknown-linux-ohos …
```

取值依据（grep 既定写法、未自造）：`notes/device-facts.md` 附录记本机 clang `Target: aarch64-unknown-linux-ohos`；仓库既有配方 `--build=…ohos` 69 例、`--host=…ohos` 108 例；`config.sub` 实测认识该值（`…-gnu`、`…-pc-linux-gnu` 亦可）。给 `--build` 后 `config.guess` **完全不再被调用**。

**第二步（过第二关）**：在 `autoreconf` **之后**、`configure` **之前**，对**生成物** `configure` 做两处替换（与参考配方 `abiword-plugin-clarisworks` 的 `_drop_umask_077()` 逐字一致）：

```python
data = data.replace(
    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
    'tmp=`mktemp -d "./confXXXXXX") 2>/dev/null`'.replace(')) 2>/dev', ') 2>/dev'))
data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp")`'.replace(')`', ')'))
```

（字面替换目标以 `.kv` 的 `rec_description` 为准：`tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\`` → `tmp=\`mktemp -d "./confXXXXXX") 2>/dev/null\`` 中的括号配平、以及 `(umask 077 && mkdir "$tmp")` → `mkdir "$tmp")`。）

**第三步（同根源的 `-lstdc++`，若链接期命中）**：改**上游源文件**两处 → **必须走 `refresh-patch` 正规登记**：

- `configure.ac` `ADD_LSTDC="yes"` → `"no"`（末尾 `if` 触发 `LIBS="$OLD_LIBS"` 移除 `-lstdc++`）
- `tests-lib/Makefile.am` `LDADD = $(top_builddir)/libsollya.la -lstdc++` → `-lc++`

**⚠ 顺序硬约束（本次踩坑，代价一整轮 R5）**：凡改 `configure.ac` / `Makefile.am` 这类**上游源文件**，补丁必须在 `autoreconf` **之前**打。否则 `autoreconf` 已用补丁**前**的源生成 `configure` / `Makefile.in`，**后改源对生成物零效果**。实测证据链：

| 位置 | 读数 | 判定 |
|---|---|---|
| `configure.ac:680`（源） | `ADD_LSTDC="no"` | 源已补丁 ✓ |
| `configure:21791`（生成物） | `ADD_LSTDC="yes"` | **仍旧** ✗ |
| `Makefile:425` | `LIBS = … -lstdc++` | **仍旧** ✗ |
| `tests-lib/Makefile.in:3182` / `Makefile:3182` | `-lstdc++` | automake 同样用旧 `.am` ✗ |

**补丁义务边界**（本工作区 2026-09-23 裁定）：剥 `umask 077` 只改 **autoreconf 生成物**（不进 git、每次重建、留痕在 `build()` 同名函数）⇒ **免** refresh-patch；改 `configure.ac` / `Makefile.am` 是**动 tarball 上游源文件** ⇒ **必须** `refresh-patch` + conandata 登记。三条件（生成物 + 可复现代码 + 每次重建执行）同时成立才免登记。

## ⚠ 自证陷阱（与本条根因配套，务必一起传播）

1. **自证必须读生成物，不能读源**：本次 `remaining_targets=0` 只证明「**源文件已改**」，不证明「**生成物已采纳**」——它证明了**不相干的命题**。正确自证（本次 `step2b`）在 `configure` 之后读三项：
   - 生成的 `configure` 内**不再有** `ADD_LSTDC="yes"`
   - `Makefile` 的 `LIBS` 行**不含** `-lstdc++`
   - `tests-lib/Makefile` 的 `LDADD` **不含** `-lstdc++`（且应含 `-lc++`）
2. **管道吃退出码**：`cmd | head && echo OK` 永远是 `head` 的 rc；`awk … "$UNDEF" | grep -c` 因打不开文件返回**空输入的 0**，把「读不到」伪装成「没有」。自证一律**直读 rc** 或 `${PIPESTATUS[0]}`，且 `grep -c` 得 0 前先自证「输入文件存在且非空」。

## 验证（设备可直接执行，路径落 `$TASK_DIR` / `$SRC`）

```sh
SRC=/storage/Users/currentUser/ws/tmp/builds/sollya-8.0.work
# 两关应已过
grep -nE 'cannot guess build type|could not setup config files machinery' \
  "$TASK_DIR/native-explore.log" && echo "仍命中(坏)" || echo "两关已过(好)"
# 生成物自证（不是读源）
grep -n 'ADD_LSTDC="yes"' "$SRC/configure" && echo "仍旧(坏)" || echo "已采纳(好)"
grep -n '^LIBS = .*-lstdc++' "$SRC/Makefile" && echo "LIBS仍旧(坏)" || echo "LIBS已清(好)"
grep -n 'LDADD.*-lstdc++' "$SRC/tests-lib/Makefile" && echo "tests-lib仍旧(坏)" || echo "tests-lib已清(好)"
```

**本任务实测结果**：`step2b_generated_adopted=0`（三项全清）+ `step2_configure=0`；`error_signature` 对 5 条真实原文 **5/5 命中、零死签名**；`prescan_pattern`（`AC_INIT\(|autogen\.sh|autoreconf -i|LT_INIT|AC_CONFIG_MACRO_DIR`）正向命中本包 `configure.ac`（`AC_INIT(`）。

## 推广价值

- 覆盖**所有** autotools + git 归档（无预生成 `configure`）的鸿蒙移植：bootstrap（`autoreconf`）与 `configure` 两阶段都必经这两关。
- 与参考先例 `archives/a/abiword-plugin-clarisworks/3.0.8/conanfile.py` 同款（其注释逐字记载同两层归因 + `config.sub supports *-linux-ohos`），可与既有 **E114**、`device-facts §一.10` 组成完整诊断链。
- 配套传播「读生成物 vs 读源」的自证判据，避免同族假绿。
