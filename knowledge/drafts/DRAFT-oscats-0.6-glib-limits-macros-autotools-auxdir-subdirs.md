# DRAFT-oscats-0.6：glib 2.80 移除 limits 宏 + AC_CONFIG_AUX_DIR 下的 config.sub + make SUBDIRS 递归污染 + SHELL/TMPDIR 平台坑 + 依赖 gsl-config 硬编码前缀 + musl POSIX select 原型冲突

> Contributor: yanjiaxin | Status: Draft | Updated: 2026-09-11
> Source: PR #9598 feat(oscats): 0.6 适配 HarmonyOS PC（autotools + glib/gsl）
> 关联任务：contrib-5528

## 背景

oscats 0.6 是 2011 年的 autotools 项目（GObject + GSL 的 IRT 自适应测验库）。
依赖 glib/2.84.0.1、gsl/2.8。在 HarmonyOS PC（OHOS aarch64，clang 15，HMDFS）
上做 Conan 适配时，撞到八类**非业务逻辑**的构建期坑（坑 0–7），逐个修复后在 CI 上绿跑
（#44640：L0 结构完整性 + L1 测试执行 + Conan test_package 全过）。其中坑 4/5/6
与 oscats 本身无关，凡在 ohos-aarch64 上走 autotools+libtool 的包都可能复现；
坑 7 是 OHOS musl 与 2011 年代码的命名冲突，同类项目普遍存在。

## 坑 0（最隐蔽，CI 首轮失败的真因）：basic_layout 默认 build_folder 与 source_folder 分离

### 现象

CI #44595（PR #9598 首次构建）33 秒即失败，且**配方里两个 patch 的
`self.output.info` 一行都没打印**：

```text
oscats/0.6: Calling build()
oscats/0.6: RUN: ".../p/b/oscat85c39f592b77b/b/configure" --disable-shared ...
checking build system type... Invalid configuration `aarch64-linux':
    machine `aarch64' not recognized
configure: error: /data/service/hnp/bin/bash ".../b/config/config.sub" aarch64-linux failed
```

即 `config/config.sub` 的替换**被静默跳过**，configure 用的仍是 2009 版。

### 根因

`basic_layout(self, src_folder=".")` 只设 `folders.source="."`；**`folders.build`
默认是 `build-<build_type>`**（`build-release`），并且 `os.getcwd()` 在 `build()`
期间就是 build_folder。于是：

| 项 | 实际值 |
|----|--------|
| `self.source_folder` | `.../p/b/<pkg>/b`（tarball 解包处，含 `config/`、`compat/`） |
| `self.build_folder` | `.../p/b/<pkg>/b/build-release` |
| `os.getcwd()` | `.../p/b/<pkg>/b/build-release` |

配方里 `aux_sub = os.path.join(self.build_folder, "config", "config.sub")` 指向
`build-release/config/config.sub`，其父目录不存在 → `os.path.isdir` 守卫为 False
→ 静默跳过（`configure` 的 umask 替换同理跳过）。

CPython/Conan 侧实测（`conan create` 探针）：

```text
DBG source_folder=...\b
DBG build_folder =...\b\build-release
DBG cwd          =...\b\build-release
DBG aux parent exists=False
```

### 修复

显式传 `build_folder="."` 强制 **in-source 构建**，让
`build_folder == source_folder == os.getcwd()`（先例：`kismet`、`ttfautohint`）：

```python
def layout(self):
    basic_layout(self, src_folder=".", build_folder=".")
```

探针复验：`aux parent exists=True`。

**教训**：`self.build_folder` 只用来放**生成物**（本工程的 `oscats.pc`、
`src/liboscats/.libs`），凡是从 tarball 解出来的**源码树文件**（`configure`、
`config/config.sub`）一律用 `self.source_folder`；两者相同才省心。`Autotools`
helper 的 `configure()`/`install()` 固定以 `self.source_folder` 定位脚本，而
`make()` 用的是 `os.getcwd()`（= build_folder）——这正是 out-of-source 时
`make -C src` 会找不到 `src/` 的原因。

## 坑 1：glib 2.80 移除 G_MIN*/G_MAX* 常量族，shim 必须自带 limits.h/float.h

### 现象

```text
src/liboscats/oscats-exposure-counter.c:88:36: error: use of undeclared identifier 'G_MAXUINT'
src/liboscats/models/oscats-l1p.c:142:23: error: use of undeclared identifier 'G_MAXDOUBLE'
src/liboscats/models/oscats-l1p.c:143:23: error: use of undeclared identifier 'G_MINDOUBLE'
```

### 根因

glib 2.80 起从 `glib/gtypes.h` **删除**了一批经典整数/浮点常量：

```text
G_MININT  G_MAXINT  G_MINUINT G_MAXUINT
G_MINLONG G_MAXLONG G_MINULONG G_MAXULONG
G_MINFLOAT G_MAXFLOAT G_MINDOUBLE G_MAXDOUBLE
G_MINSHORT G_MAXSHORT
```

官方理由是改用 C99 `<limits.h>` / `<float.h>`。oscats 0.6 到处用它们做 GObject
属性区间（`g_param_spec_uint(..., 1, G_MAXUINT, ...)`）与数值哨兵
（`±G_MAXDOUBLE` / `G_MINDOUBLE` 作为无界区间端点）。

### 修复

用 `compat/glib-compat.h` + `-include` 强制注入等价定义。**关键细节**：glib 的
`gtypes.h` 自身并不 include `<limits.h>` / `<float.h>`，所以 shim 必须**自己带上
这两个头**，否则 `INT_MAX` / `DBL_MAX` 同样未声明；另每个定义用 `#ifndef` 守卫，
让仍然提供这些宏的旧版 glib 优先（前向兼容）：

```c
#ifndef OSCATS_GLIB_COMPAT_H
#define OSCATS_GLIB_COMPAT_H
#include <limits.h>
#include <float.h>
#ifndef G_MAXUINT
#  define G_MAXUINT  UINT_MAX
#endif
#ifndef G_MAXDOUBLE
#  define G_MAXDOUBLE DBL_MAX
#endif
#ifndef G_MINDOUBLE
#  define G_MINDOUBLE DBL_MIN
#endif
/* ... 其余 G_MIN*/G_MAX* 同理 ... */
#endif
```

配方侧：

```python
tc.extra_cflags.extend([
    "-include", os.path.join(self.source_folder, "compat", "glib-compat.h"),
])
```

## 坑 2：AC_CONFIG_AUX_DIR([config]) 下，config.sub 的替换落点是 config/ 而非构建根

### 现象

```
checking build system type... /bin/sh ./config.sub aarch64-linux
./config.sub: machine 'aarch64' not recognized
configure: error: /bin/sh ./config.sub aarch64-linux failed
```

（实际报错里的 `./config.sub` 是 configure 用 `$ac_aux_dir/config.sub` 拼出来的。）

### 根因

上游 `configure.in` 声明了 `AC_CONFIG_AUX_DIR([config])`，于是 autotools 的
辅助脚本目录是 `config/`，configure 实际调用的是 **`$ac_aux_dir/config.sub`
= `config/config.sub`**——**上游 tarball 根目录根本没有 `config.sub`**。
2009/2010 版 `config.sub` 完全不认识 aarch64（实测
`config.sub aarch64-linux` → `machine 'aarch64' not recognized`，rc=1），必须替换。

### 修复

1. 从 `compat/config.sub`（2022 FSF 版）覆盖到 **`config/config.sub`**：

```python
compat_sub = os.path.join(self.source_folder, "compat", "config.sub")
aux_sub = os.path.join(self.build_folder, "config", "config.sub")
if os.path.exists(compat_sub) and os.path.isdir(os.path.dirname(aux_sub)):
    save(self, aux_sub, load(self, compat_sub))
```

2. 同时给 configure 显式传 `--build=aarch64-linux --host=aarch64-linux`：这样
   `config.guess`（2010 版同样不认 aarch64）**根本不会被调用**，只需修 config.sub
   一处。

代价：`compat/config.sub` 进 `export_sources`（`copy(self, "compat/*", ...)`）。

## 坑 3：`make SUBDIRS=<dir>` 的命令行变量经 MAKEFLAGS 递归污染子目录

### 现象

oscats 顶层 `Makefile.am` 的 `SUBDIRS` 包含 `src doc bindings` 等；`src/Makefile.am`
自己又是 `SUBDIRS = liboscats`。想只编 `src/liboscats`（跳过 gtk-doc 与语言绑定）时：

```sh
make SUBDIRS=src        # 期望只在 src 下递归
# → src/Makefile 的 SUBDIRS 被命令行变量覆盖成 "src"
# → make 试图 cd src/src → No such file or directory / Error 1
```

### 根因

make 命令行里给的变量赋值会写入 `MAKEFLAGS` 并被**递归传给所有子 make**，且命令行
变量优先级高于 Makefile 里的赋值。所以 `SUBDIRS=src` 不只作用于顶层，也把
`src/Makefile` 自己的 `SUBDIRS=liboscats` 改成 `src`，导致 `cd src`（相对 src/）
不存在。

### 修复

改用 `make -C <dir>`：`-C` 是 make 自身的选项，只改变工作目录，**不产生任何
变量覆盖**，子目录自己的 `SUBDIRS` 保持原样：

```python
autotools.make(target="-C src")   # 只进 src/，其 SUBDIRS=liboscats 不被覆盖
```

（先例：`abiword-plugin-docbook` 用 `autotools.make(target="-C plugins/docbook")`。）

## 附带：两个 2011 年代码 + 新工具链的小坑（非本文重点）

- **`-Wall -Werror` 覆盖**：`src/liboscats/Makefile.am` 把 `-Wall -Werror` 硬编码
  进 `liboscats_la_CFLAGS`。automake 生成的编译行里 per-target CFLAGS 排在
  `$(CFLAGS)` **之前**，故把 `-Wno-error` 追加进 `CFLAGS` 即可覆盖（后写者胜）。
- **`-fcommon`**：2011 年代码头文件里的 tentative definition 在 gcc10/clang15
  默认 `-fno-common` 下会报 multiple definition，须加 `-fcommon`。
- **写消费者测试时的坑**：`oscats_space_dim_get_max(space, dim)` 只接受**自然**维度
  （内部 `g_return_val_if_fail((dim & OSCATS_DIM_TYPE_MASK) == OSCATS_DIM_NAT, 0)`），
  对连续维度调用会打 `OSCATS-CRITICAL ... oscats_space_dim_get_max: assertion
  failed` 并返回 0（不是崩溃，但断言必然失败）。连续维度应改用
  `oscats_space_dim_get_name()` / `oscats_space_validate()`。本 PR 的 L1 测试最初
  就踩了这个（CI #44623：`13 checks, 1 failed`）；改用 `dim_get_name`/`validate`
  后 CI #44640 打印 `14 checks, 0 failed`。

## 坑 4（平台级，CI #44609）：SHELL/CONFIG_SHELL 指向 HNP bash 致 libtool 引号失衡

### 现象

```text
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
checking how to print strings... print -r
config.status: line 685: print: command not found      （×60）
../../libtool: line 315: syntax error near unexpected token `}'
../../libtool: line 315: `	    echo "local: *; };" >> $output_objdir/$libname.ver~'
make[1]: *** [Makefile:484: liboscats_la-bitarray.lo] Error 2
```

### 根因（两层叠加）

1. **shell 语义不一致**：ohos-aarch64 profile 的 `[buildenv]` 把 `SHELL` 与
   `CONFIG_SHELL` **都**指向 `HNP bash`（`/data/service/hnp/bin/bash`）。autoconf 在
   configure 阶段用 `print -r -- -n` 探测 ECHO 能力，只要**当时运行 configure 的
   shell 有 `print` 内建**就把 `ECHO='print -r --'` 写进 `config.status`；而
   `config.status` / `make` / 生成的 `libtool` 由 **make 侧 shell** 执行——HNP bash
   没有 `print` 内建 → 60+ 次 `print: command not found` → libtool 赋值的引号失衡，
   在 linux 分支生成 version script 的那行炸掉。
2. **HMDFS 上 getcwd 失败**：HNP bash（5.3.0）对整棵 HMDFS 树 `getcwd()` 失败，
   于是满屏 `shell-init: ... getcwd: cannot access parent directories: Not supported`。

### 修复

`generate()` 里**实测选 shell**，并对 configure 与 make 两侧**统一**（先例：`blogc/0.20.1`）：

```python
def _pick_working_shell(self):
    for cand in [shutil.which("bash"),
                 os.path.expanduser("~/.harmonybrew/bin/bash"),
                 "/bin/sh"]:
        if not cand or not os.path.exists(cand):
            continue
        probe = subprocess.run([cand, "-c", "pwd"], cwd=self.build_folder,
                               capture_output=True, timeout=30)
        bad = (b"Not supported" in probe.stderr
               or b"getcwd" in probe.stderr
               or b"shell-init" in probe.stderr)
        if probe.returncode == 0 and not bad:
            self.buildenv.define("SHELL", cand)
            self.buildenv.define("CONFIG_SHELL", cand)
            os.environ["SHELL"] = os.environ["CONFIG_SHELL"] = cand
            return
    self.output.warning("no getcwd-capable shell found; keeping profile SHELL")
```

复验：重跑后 `print: command not found` / `libtool: line 315` / `getcwd` 计数全为 0。

## 坑 5（平台级，CI #44609）：TMPDIR 落在 HMDFS 致 make jobserver `mkfifo` 失败

### 现象

```text
make: jobserver mkfifo: /storage/.../b/.conan_tmp/GMfifo31639: Operation not permitted
```

### 根因

GNU make 4.4+ 用**命名管道**做 jobserver，路径取自 `$TMPDIR`（`mkfifo`）。HMDFS
不支持 `mkfifo`；反过来，把 TMPDIR 直接指到沙箱外又常常不可写（clang 报
`C compiler cannot create executables`）。所以既不能留在构建目录，也不能想当然清空。

### 修复

`generate()` 里**逐候选实测**「可写 + mkfifo 可用」，buildenv 与 `os.environ` 双写，
`build()` 开头再兜底一次：

```python
def _pick_tmpdir(self):
    fallback = os.path.join(self.build_folder, ".conan_tmp")
    for c in [os.path.expanduser("~/tmp"),
              "/data/storage/el2/base/cache",
              os.environ.get("TMPDIR") or ""]:
        if not c:
            continue
        try:
            os.makedirs(c, exist_ok=True)
            p = os.path.join(c, ".probe"); open(p, "w").close(); os.remove(p)
            f = os.path.join(c, ".probe_fifo")
            os.mkfifo(f); os.remove(f)          # HMDFS 上会抛 OSError
        except (OSError, AttributeError):
            continue
        self.buildenv.define("TMPDIR", c); os.environ["TMPDIR"] = c
        return c
    self.buildenv.define("TMPDIR", fallback); os.environ["TMPDIR"] = fallback
    return fallback
```

（注意 `os.mkfifo` 在 Windows 上是 `AttributeError`，故 except 两个都要接。）

## 坑 6（依赖包缺陷，CI #44619）：发布的 gsl/2.8 `gsl-config` 硬编码 `-I//include` / `-L//lib`

### 现象

```text
models/l2p.c:26:10: fatal error: 'gsl/gsl_vector.h' file not found
models/gr.c / l3p.c / nominal.c / l1p.c / gsl.h:22 / integrate.h:22 同样
```

### 根因

已发布的 `gsl/2.8` 包里 `bin/gsl-config` 写死了空根前缀：

```sh
prefix=/
exec_prefix=/
includedir=//include
...
--cflags)  echo -I//include ;;
--libs)    echo -L//lib -lgsl $GSL_CBLAS_LIB -lm ;;
```

oscats 用 `AX_PATH_GSL` 把 `gsl-config --cflags/--libs` 的**原样字符串**抄进
`GSL_CFLAGS`/`GSL_LIBS`；配方又传了 `--disable-gsltest`，跳过了 AX_PATH_GSL 的
编译+运行自检，于是错误的 `-I//include` 直到编译 `src/liboscats/models/*.c` 才暴露。

### 修复

不盲信依赖提供的 `*-config`：取其 `package_folder`，把 `gsl-config` **复制到构建目录**
后就地改写（先例思路同 E011 的就地 patch）：

```python
gsl_pf = self.dependencies["gsl"].package_folder
text = load(self, os.path.join(gsl_pf, "bin", "gsl-config"))
text = (text.replace("-I//include", "-I%s/include" % gsl_pf)
            .replace("-L//lib",     "-L%s/lib"     % gsl_pf))
lines = []
for ln in text.splitlines():
    if   ln.startswith("prefix="):      ln = "prefix=%s" % gsl_pf
    elif ln.startswith("exec_prefix="): ln = "exec_prefix=%s" % gsl_pf
    elif ln.startswith("includedir="):  ln = "includedir=%s/include" % gsl_pf
    lines.append(ln)
save(self, dst, "\n".join(lines) + "\n"); os.chmod(dst, 0o755)
os.environ["GSL_CONFIG"] = dst
```

本地对下载下来的实际 `gsl-config` 跑同一变换，复验 `remaining //include: 0`、
`remaining //lib: 0`。**通用教训**：跨平台 Conan 包里凡提供 `*-config` / `.pc` 的，
都要先验证其路径是否对得上 `package_folder` 再交给 autotools 的 `AX_PATH_*`。

## 坑 7（OHOS musl 命名冲突，CI #44620）：私有 `static select` 回调撞上 POSIX `select(2)`

### 现象

```text
algorithms/max_kl.c:626:13: error: static declaration of 'select' follows non-static declaration
static gint select (OscatsTest *test, OscatsExaminee *e,
            ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/select.h:40:5: note: previous declaration is here
int select (int, fd_set *__restrict, fd_set *__restrict, fd_set *__restrict, struct timeval *__restrict);
    ^
make[1]: *** [Makefile:701: liboscats_la-max_kl.lo] Error 1
```

### 根因

OHOS musl 的 `sys/select.h` **在默认模式下无条件**声明 POSIX `select(2)` 原型
（不需要任何 feature-test 宏），而该头经 `glib/gmain.h` 被间接引入。oscats 的四个
选题算法各自定义了一个**文件内 static** 信号回调：

| 文件 | 定义 | 引用 |
|------|------|------|
| `algorithms/closest_diff.c` | :178 | :197 `G_CALLBACK(select)` |
| `algorithms/max_fisher.c` | :268 | :301 |
| `algorithms/max_kl.c` | :626 | :664 |
| `algorithms/pick_rand.c` | :38 | :58 |

`select` 是 oscats 给 `OscatsTest` 注册的 GObject 信号名，回调按信号名取了同名函数。
在 glibc 上 `select` 的声明只在 `<sys/select.h>` 被显式（或经 `<sys/time.h>` 在
特定宏下）引入时才出现，所以上游二十年没撞到；OHOS musl 头文件依赖关系不同，必撞。

**这是 clang 硬错误，不是警告**——`-Wno-error` 无能为力（`-Wno-error` 只能把警告
降级，改不了约束违规）。**宏改名（`-Dselect=...` / `#define select ...`）同样无效**：
宏会同时改写 `sys/select.h` 里的 POSIX 声明和 oscats 的私有定义，两者仍是
「一名两态」（一个非 static 声明 + 一个 static 定义），冲突原样保留。

### 修复

把私有定义**重命名出 POSIX 命名空间**（GObject 信号名字符串 `"select"` 保持不变），
做成一枚 patch：

```diff
-static gint select (OscatsTest *test, OscatsExaminee *e,
+static gint select_cb (OscatsTest *test, OscatsExaminee *e,
                     GBitArray *eligible, gpointer alg_data)
...
-  g_signal_connect_data(test, "select", G_CALLBACK(select),
+  g_signal_connect_data(test, "select", G_CALLBACK(select_cb),
```

`patches/0001-rename-select-signal-callbacks.patch` 覆盖 4 个文件共 8 处
（4 处定义 + 4 处 `G_CALLBACK`），在 `conandata.yml` 的 `patches:` 下声明、配方里
`apply_conandata_patches(self)` 应用。（本地用 `patch -p1 --dry-run` 与 conan 自带的
`patch_ng` 各验一次，均 4/4 应用成功。）

**这正是知识库既有条目 `DRAFT-musl-posix-decl-conflict-rename-legacy`
（blimps 3.9 的 legacy `getline` 同款问题，rec_approach=`rename-legacy-definition`）
的复用**；该条目 `forbid_1`（靠 -Wno-error 降级）与 `forbid_2`（宏改名）两条死路
在本例中同样被印证。

## 验证

```sh
conan create . -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
    -pr:b=$HOME/.conan2/profiles/ohos-aarch64 --build=missing
```

完整通过 configure / make -C src / test_package（14 次断言的 1D CAT 闭环，
程序末尾打印 `14 checks, 0 failed`）。

## 关系

- 类似 E011（HMDFS umask 077 临时目录）——本配方同样用 E011 方法 2 把发布
  tarball 的 configure 内 `umask 077` 改成 `022`（先例 cracklib / libgsf）。
- 本草稿补充：**`basic_layout` 默认 build_folder 与 source_folder 分离，源码树 patch
  必须走 `self.source_folder`（或显式 build_folder="."）**；**glib 2.80 删 limits
  宏时 shim 必须自带 limits.h/float.h**；**AC_CONFIG_AUX_DIR 决定 config.sub 的
  替换落点**（不能想当然放构建根）；**make 命令行变量会经 MAKEFLAGS 递归污染子目录
  SUBDIRS，应改用 make -C**；**SHELL/CONFIG_SHELL 必须实测选中并让 configure 与
  make 两侧统一，否则 libtool 引号失衡**（先例 blogc 0.20.1）；**TMPDIR 不能落在
  HMDFS（make jobserver 需 mkfifo），须实测「可写+mkfifo」候选**；**依赖包的
  `*-config`/`.pc` 路径不可盲信，须验后（或就地改写）再交给 AX_PATH_***；
  **与 libc/POSIX 同名的私有 static 定义必须重命名（-Wno-error 与宏改名都无效）**，
  同 `DRAFT-musl-posix-decl-conflict-rename-legacy`（blimps 3.9 legacy getline）。
