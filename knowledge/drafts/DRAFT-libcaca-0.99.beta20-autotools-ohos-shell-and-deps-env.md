# DRAFT — OHOS autotools 配方两处高发坑（libcaca 0.99.beta20 实证）

> 状态：草稿，待评审提升为 E 条目。配套 `.kv` 文件同名同目录。
> 来源：`archives/l/libcaca/0.99.beta20/`（设备实机，2026-09-14）

## 一句话

在 OHOS 上用 autotools 适配 C/C++ 库时，有两个坑会反复出现且报错信息完全指错方向：

1. **构建 shell 选错**：为绕开 autoconf 的 `exec 7<&0` 而把 `SHELL`/`CONFIG_SHELL`
   全设成 zsh，会连带让 `make` 也用 zsh——而 zsh 不做需要 IFS 词分割的展开，
   automake 的 `all-recursive` 会把整个 `SUBDIRS` 当成一个目录名。
2. **依赖 env 送不到**：conan 生成的 `conanautotoolsdeps.sh` 里有正确的 `-I/-L/-l`，
   但它只被 conan 自己的 `Autotools()` 助手 source；配方用裸 subprocess 跑 configure 时，
   conan 不把 build env 写进 `os.environ`，configure 于是"看不见"任何依赖。

## 坑 1：zsh 与 IFS 词分割

### 现象

```text
zsh:cd:21: no such file or directory: kernel caca src examples tools cxx caca-sharp python ruby java doc
make[1]: *** [Makefile:546: all-recursive] Error 1
```

注意被 `cd` 的是一个**目录名列表**，不是一个路径。

### 根因

automake 生成的循环：

```make
list='$(SUBDIRS)'; for subdir in $$list; do \
  ($(am__cd) $$subdir && $(MAKE) $(AM_MAKEFLAGS) $$local_target) || exit 1; \
done
```

`for subdir in $list` 依赖 POSIX 的 IFS 词分割。**zsh 默认不做该分割**
（需 `SH_WORD_SPLIT`），于是 `$list` 的整串内容成为一次迭代的单个单词。

`make` 的 recipe shell 取自 `SHELL`，所以配方一旦把 `SHELL` 全局设成 zsh，
`make` 也一起变成 zsh。

### 为什么容易踩

这个坑是为了修**另一个**坑才引入的：autoconf 2.69/2.71 的 `configure` 用
`exec 7<&0` 保存 stdin，而 OHOS 的 `/system/bin/sh`（toybox）不支持多位数 fd 重定向：

```text
./configure[557]: 7<&0 : bad file descriptor
```

ncrack 0.7 的解法是把 `SHELL`/`CONFIG_SHELL` 设成 `/usr/bin/zsh`——**并存**，因为
ncrack 的 `Makefile.in` 是手写的、没有 `all-recursive`，所以从未暴露坑 1。

### 正确做法

用平台 profile **自己声明的**构建 shell——`ci/conan/profiles/ohos-aarch64` 的
`[buildenv]` 里就是：

```text
CONFIG_SHELL=/data/service/hnp/bin/bash
SHELL=/data/service/hnp/bin/bash
```

bash 同时满足两个条件：支持 `7<&0`；对未加引号展开做 IFS 词分割。
`/system/bin/sh`（toybox）不可用。zsh 仅可作 configure 的兜底，**不能让 make 用 zsh**。

## 坑 2：conan 的依赖 env 脚本不会被裸 subprocess source

### 现象

```text
configure: error: cannot find ncurses development files
```

而配置日志里：

```text
CPPFLAGS='-I/storage/Users/currentUser/usr/local/include'
```

即只有设备环境自带的路径，**没有** ncurses 的 `-I`。四个候选头
（`ncursesw/ncurses.h`、`ncurses/ncurses.h`、`ncurses.h`、`curses.h`）全部探测失败。

### 根因

`generate()` 后 conan 在生成目录写了正确的脚本：

```sh
# conanautotoolsdeps.sh
export CPPFLAGS="${CPPFLAGS:-}${CPPFLAGS:+ }-I.../ncursf4c8bb2f1a955/p/include"
export LIBS="${LIBS:-}${LIBS:+ }-lformw -lmenuw -lpanelw -lncursesw"
export LDFLAGS="${LDFLAGS:-}${LDFLAGS:+ }-L.../ncursf4c8bb2f1a955/p/lib"
```

并被聚合进 `conanbuild.sh`：

```sh
. ".../conanautotoolstoolchain.sh" && . ".../conanautotoolsdeps.sh" && . ".../conanbuildenv-*.sh"
```

但该聚合脚本是**给 conan 的 `Autotools()` 助手（或用户 `conan build` 时）source 的**。
配方若自行 `subprocess.run(cmd, env=dict(os.environ))` 跑 `./configure`，
`os.environ` 里没有 `CPPFLAGS` 的依赖部分。

### 正确做法

在配方内显式重建，并注意**顺序**：自己的 `-I` 在前、设备原有值在后，
否则会命中设备 prefix 下的同名头却连不到对应的库（libcaca 的 zlib 就是这样：
`AC_CHECK_HEADERS(zlib.h)` 命中了设备自己的 zlib.h，配置打开了 zlib 支持，
静态 `libcaca.a` 因此带上无人解析的 `-lz`，test_package 报
`undefined symbol: gzgets / gzopen`）：

```python
cppflags, ldflags, libs = [], [], []
zlib = self.dependencies["zlib"].package_folder
cppflags.insert(0, f"-I{zlib}/include")
ldflags.insert(0, f"-L{zlib}/lib")
libs.insert(0, "-lz")
...
for name, value in (("CPPFLAGS", cppflags), ("LDFLAGS", ldflags), ("LIBS", libs)):
    ambient = os.environ.get(name, "")
    parts = [*value, ambient] if ambient else list(value)
    if parts:
        environment.define(name, " ".join(parts))
```

## 附带：设备无 pkg-config 时怎么过 PKG_CHECK_MODULES

`PKG_CHECK_MODULES([CPPUNIT], [cppunit])` 展开后是：

```sh
if test -n "$CPPUNIT_CFLAGS"; then
    pkg_cv_CPPUNIT_CFLAGS="$CPPUNIT_CFLAGS"
elif test -n "$PKG_CONFIG"; then
    ... 调用 pkg-config ...
else
    pkg_failed=untried
fi
```

即 **`$CPPUNIT_CFLAGS` 非空时短路**，根本不碰 pkg-config。configure 自己的报错文案
也这么提示：

```text
Alternatively, you may set the environment variables CPPUNIT_CFLAGS
and CPPUNIT_LIBS to avoid the need to call pkg-config.
```

所以在 `_build_environment()` 里一并导出 `CPPUNIT_CFLAGS`/`CPPUNIT_LIBS` 即可，
**不需要**引入 pkgconf。

> 注意：交叉模式下 configure 还有一段 `if test "${build}" != "${host}" -a
> "${PKG_CONFIG_LIBDIR}" = ""; then export PKG_CONFIG_LIBDIR=/dev/null; fi`——
> 显式设置 `PKG_CONFIG_LIBDIR` 或走上面的变量短路，二选一。

## 两个工程性坑（记录备查）

### 并发：两个 agent_worker 会让同一 job 跑两次

设备上若有两个 `agent_worker.sh` 同时轮询同一 mailbox，同一 job 文件会被两个进程
先后取走执行（`tail -1` 检查与 `mv` 之间存在竞态）。两个 `conan create` 并发导出同一
recipe 时，后者的导出会覆盖前者的缓存目录，留下"revision 已登记但目录缺失"的残留，
下次运行直接跳过 export 段并报：

```text
ERROR: Package 'libcaca/0.99.beta20@ohpcd/stable' not resolved: Cannot load recipe.
Error loading conanfile at '.../libca1ddead8dbfdbe/e/conanfile.py': not found!
```

同类并发还会让 `conan download()` 在**下载成功之后**报
`FileNotFoundError: .../libcaca-source.tar.gz`——把网络/TLS 失败伪装成"文件不存在"，
URL 与 HTTP 状态全部丢失。

对策：任务脚本首行 `mkdir "$LOCK" || exit 0` 加互斥锁；缓存被污染时
`conan remove "<pkg>/*" -c` 清干净再跑。

### 误判：R47 lang-preflight 会把绑定子目录的 manifest 当顶层构建系统

`ohc-run.py lang-preflight libcaca 0.99.beta20` 报 `detected_language=python`
（`build_system: setuptools`）——因为 dist 里有 `python/setup.py`。
那是**可选 SWIG 绑定子包**的打包文件；项目顶层是 autotools
（`configure.ac` + `Makefile.am` + 预生成 `configure`），交付物是 C ABI 库。

按 AGENTS.md §1.2「混编项目按主体语言判，主体为 C/C++ 即在范围内」：
libcaca 主体是 C（92 个 `.c`、8 个 `.cpp`、22 个 `.h`），且配方已
`--disable-python/ruby/java/csharp`，构建面不含非 C/C++ 语言。
判定依据应落到**顶层构建系统 + 交付物形态**，不能只看 tarball 根下的 manifest。
