# GitHub archive 型 autotools 包在 OHOS 上自举的四连失败（E626）

> Draft: `E626-draft-librdata-autotools-github-snapshot-ohos-bootstrap`
> Stem: `E626-draft-librdata-autotools-github-snapshot-ohos-bootstrap` — pairs with the same-stem `.kv`
> 预留知识编号：**E626**（任务 `librdata 0-20210223-git-85757dc6`）
> 复现命令落点：`$HOME/tmp/librdata-0-20210223-git-85757dc6/`（设备可直接执行）

## 基本信息

- **ID**: DRAFT-E626-LIBRDATA-AUTOTOOLS-GITHUB-SNAPSHOT-OHOS-BOOTSTRAP
- **严重度**: 2
- **类别**: autotools-bootstrap-ohos
- **触发工具**: conan
- **阶段**: build-bootstrap（`autoreconf` → `configure`）

## 适用面（什么时候会命中）

源码 tarball 是 **git 快照**（`https://github.com/<owner>/<repo>/archive/<sha>.tar.gz`）
而不是发行 tarball ⇒ 树里**没有 `configure`**，只有 `configure.ac` / `Makefile.am` /
`autogen.sh` ⇒ 配方必须在 `build()` 里 `autoreconf` 自举。本条目覆盖自举路上的
四个独立失败点，它们按顺序出现，且前一个不修就看不到后一个。

## 错误特征（逐条）

```
# ① AM_ICONV
configure.ac:17: error: possibly undefined macro: AM_ICONV
      If this token and others are legitimate, please use m4_pattern_allow.
autoreconf: error: /data/service/hnp/autoconf.org/autoconf_2.72/bin/autoconf failed with exit status: 1

# ② config.status 临时目录不可写（E114 的 configure 内变体）
configure: creating ./config.status
./config.status[974]: can't create ./confKCKaCD/subs1.awk: Permission denied
config.status: error: could not setup config files machinery

# ③ config.guess 猜不出系统
config.guess[1612]: can't create /storage/.../cgodKAgA/dummy.c: Permission denied
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one

# ④ conan perl 与 HNP perl 混用
Can't load '/storage/.../perlbad96edf51f7f/p/lib/perl5/5.42.2/aarch64-linux-thread-multi/auto/Cwd/Cwd.so'
  for module Cwd: Error relocating ...: Perl_my_cxt_init: symbol not found
Compilation failed in require at /data/service/hnp/bin/autoreconf line 48.
```

## 复现（设备实测，librdata 0-20210223-git-85757dc6）

```sh
TASK_DIR="$HOME/tmp/librdata-0-20210223-git-85757dc6"
# 用仓库 profile 的绝对路径（相对名会命中的 $CONAN_HOME/profiles 陈旧副本）
conan install "$TASK_DIR/probe" -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 -of "$TASK_DIR/probe/out"
cd <src> && . "$TASK_DIR/probe/out/conanbuild.sh"
autoreconf -fi                     # ① 命中 AM_ICONV 时 rc=255/1
```

`probe/conanfile.py` 只需声明消费者侧的 `tool_requires`/`requires` 并
`AutotoolsToolchain + AutotoolsDeps` 各 generate 一次，就能拿到与 `conan create`
一致的 `conanbuild.sh`（这是零构建预算预验的最省做法）。

## 根因与修法（逐条）

| # | 根因 | 判据（可机械核对） | 修法 |
|---|------|-------------------|------|
| ① | `AM_ICONV` 来自 GNU gettext 的 `iconv.m4`；conan `gettext/0.22.5.1` 只装 `bin/lib/include`、**不装 m4**，HNP 也不带 ⇒ `aclocal` 找不到该宏，`autoconf` 把 `AM_ICONV` 当未定义宏 | `autoreconf -fi` 输出含 `possibly undefined macro: AM_ICONV` | 补丁改 `configure.ac`：`AM_ICONV` → `AC_CHECK_HEADERS([iconv.h], [], [AC_MSG_ERROR(...)])` + `AC_CHECK_FUNCS([iconv_open iconv iconv_close], [], [AC_MSG_ERROR(...)])`。OHOS musl libc 自带 `iconv.h` 与 iconv 函数，**保留硬失败语义**、不静默降级（先例：zbar 0.23.93 直接删掉 `AM_ICONV`） |
| ② | autoconf 生成的 `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；HMDFS 强制 setgid 并把目录属主映射成共享属主 ⇒ 落成 `drwx--S---`（mode `0o42700`）owner `20001006`，而进程 euid 是 `20020085` ⇒ 不可写 | `ls -ld` 该目录 + `python3 -c "import os;print(os.geteuid())"`；`grep -c 'umask 077 && mktemp' configure` | `build()` 里 `autoreconf` **之后**就地改生成的 `configure`：去掉 `umask 077 &&` 前缀与 fallback 分支里的同一前缀。去掉后目录落成 `drwxrws--x`（继承父目录组写位）= 可写。**必须判在 autoreconf 之后**，改在前面会被重新生成覆盖 |
| ③ | `AC_CANONICAL_HOST` 跑 `config.guess`，后者在同类 mktemp 目录里写 `dummy.c` ⇒ 同样 Permission denied ⇒ `unable to guess system type` | `sh <automake>/share/automake-1.18/config.guess` 的 stderr | `AutotoolsToolchain.configure_args` 显式加 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，跳过 `config.guess`。automake 1.18 的 `config.sub` 接受该三元组（实测 `aarch64-linux-ohos` 也被规范化为 `aarch64-unknown-linux-ohos`）。build==host ⇒ 仍是原生 configure，`AC_CHECK_LIB` 做的是真实链接探测 |
| ④ | `tool_requires("autoconf/2.72")` 带出 conan `perl/5.42.2`，其 `buildenv_info` 把 `PERL5LIB` 指向自己的 XS 模块；而 OHOS 上 `autoreconf`/`autoconf` 解析到 `/data/service/hnp/bin/*`，shebang **钉死在 HNP perl 5.42.0** ⇒ 两套 perl 混用，XS 模块 `Cwd.so` 重定位失败 | `grep -n PERL5LIB conanbuildenv-*.sh`；`head -1 $(command -v autoreconf)` | `tool_requires` 只放 `automake/1.18` + `libtool/2.5.4`（HNP 自带 autoconf 2.72 + m4 1.4.20 + perl 5.42.0）。实测同一命令由 rc≠0 变 rc=0 |

## 附带的第五个陷阱：sysroot 里的 stub 库会被 `AC_CHECK_LIB` 命中

上游用 `AC_CHECK_LIB([z],[deflate])` 探测压缩后端。OHOS SDK sysroot 的
`.../sysroot/usr/lib/aarch64-linux-ohos/libz.so` 是一个 **stub**：

```
$ ls -l libz.so            # 13888 B
$ llvm-readelf -d libz.so | grep SONAME
  0x000000000000000e (SONAME)  Library soname: [libz.so]
$ llvm-nm -D --defined-only libz.so | grep -c deflate   # 全部符号同址 0x26b8
```

设备运行期 `/system/lib64` 下**没有** `libz.so`，只有 `/usr/lib/libz.so.1`。
若让 configure 命中它，`librdata.so` 会写进 `DT_NEEDED libz.so` ⇒ 运行期装载失败。
修法：压缩后端全部走 Conan（`zlib/1.3.1.1`、`bzip2/1.0.8.2`、`liblzma/5.8.1`），
并显式 `AutotoolsDeps(self).generate()` —— **`AutotoolsToolchain` 本身不再为依赖注入
`-I/-L/-l`**（conan 2.29 实测 `LDFLAGS` 为空、`CPPFLAGS` 只有 `-DNDEBUG`），
只有 `AutotoolsDeps` 会生成 `conanautotoolsdeps.sh`（`LIBS=-llzma -lbz2 -lz` +
对应 `-L`/`-I`）。三者制品均为静态库，链接结果为内链：交付的 `librdata.so`
`DT_NEEDED` 只有 `libc.so`。

## 验证要点

- `readelf -d <pkg>/lib/*.so`：`NEEDED` 只应有 `libc.so`（不得出现 `libz.so`/`liblzma.so`/`libbz2.so`）；
  `SONAME` 必须存在且不是绝对路径。
- 生成 `configure` 后 `grep -c 'umask 077 && mktemp' configure` 必须为 **0**。
- `make check` 的 `test-suite.log` 要出现 `# TOTAL: n` / `# PASS: n`（这是 automake 框架注册数的权威读数）。
