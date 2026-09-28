# ballandpaddle 0.8.1 适配笔记

## 背景

GNU Ball and Paddle 是 2008 年发布的打砖块游戏（GPLv3），两个「非典型」特征决定了
这次适配的主要工作量：

1. **SDL 1.2 时代的上游**：`configure.ac` 用 `AM_PATH_SDL($SDL_VERSION, ...)` 调
   `sdl-config` 取编译/链接参数，而 ohpcd 只发布 `sdl12-compat`（SDK 兼容层，
   包内**没有** `sdl-config` 脚本）。
2. **内嵌 Guile 脚本引擎**：关卡、皮肤、砖块类型全部由 Scheme 脚本描述，
   `src/main.cpp` 的 `main()` 只调 `scm_boot_guile(argc, argv, inner_main, 0)`，
   游戏主体全在 Guile 回调 `inner_main()` 里。上游开发期（2008）对应 Guile 1.8，
   此处链接 Guile 2.2.7（源码用的已是 2.x API：`scm_to_locale_string` /
   `scm_from_int` / `scm_c_eval_string`，见 `src/extension.cpp`、`src/ball.cpp`）。

## 依赖面

| 依赖 | 版本 | 作用 |
|---|---|---|
| sdl12-compat | 1.2.68 | 提供 `libSDL-1.2`（SDL2 之上的 1.2 ABI 兼容层），静态 |
| sdl_image | 1.2.12 | PNG 贴图加载（`IMG_LoadPNG_RW`） |
| sdl_mixer | 1.2.12 | WAV 音效（`Mix_LoadWAV_RW`） |
| sdl_ttf | 2.0.11 | 字体渲染（`TTF_OpenFontRW`） |
| guile | 2.2.7 | 内嵌 Scheme 解释器（`scm_boot_guile` / `scm_c_define_gsubr`） |
| gmp | 6.3.0 | guile 公开头 `libguile/numbers.h` 直接 `#include <gmp.h>`；与 guile 自身依赖同版本，不引入第二份二进制 |

四个 SDL 侧包静态链接，guile 是 `shared=True`（其 NEEDED 为 libgc / libffi /
libunistring / libgmp）。

依赖 flags 走**两条互不替代**的通路：SDL 那一路走 `sdl-config` 外壳
（`AM_PATH_SDL` 把结果塞进 `SDL_CFLAGS`/`SDL_LIBS`，**不经** `CPPFLAGS`/`LIBS`），
guile 这一路走 `AutotoolsDeps` 生成的 `CPPFLAGS`/`LDFLAGS`/`LIBS`。
所以 `generate()` 里的 `AutotoolsDeps` 不能因为"已经有外壳了"而省掉 ——
反之亦然，两者缺一不可。

## 补丁

### 0001-configure-umask.patch（可移植性，平台专属）

`configure`（及其写进 `config.status` 的同一段文本）用
`(umask 077 && mktemp -d "./confXXXXXX")` 在 cwd 建临时目录。HMDFS 挂载下 0700
目录对构建进程不可写（chmod 不生效，属主位形同虚设），表现为 configure 打印成功
但 Makefile 从未生成，或后续 `./confXXXXXX/subs-1.sed: Permission denied`。
两处 `077` 改为 `022`。同仓库先例：`archives/s/sdl_image/1.2.12` 的
`0001-configure.patch`、`archives/n/ncdc/1.25` 的 `_relax_configure_umask`，
知识库条目 **E011**。

### 0002-configure-guile-soname.patch（可移植性，非平台专属）

上游 `configure.ac:29`：

```m4
AC_CHECK_LIB(guile, scm_boot_guile,
            LIBS="-lguile $LIBS",
            AC_MSG_ERROR(can't find guile. This software REQUIRES guile.))
```

即按 **`-lguile`** 去找库。Guile 1.8 时代的 soname 是 `libguile.so`，Guile 2.x
改成随 minor 走的 `libguile-2.2.so` —— 已发布的 `guile/2.2.7` 包
（`cpp_info.libs = ["guile-2.2"]`）里根本没有 `libguile.so`。结果是探针在
`checking for scm_boot_guile in -lguile` 处报
`can't find guile. This software REQUIRES guile.` 直接终止 configure ——
**尽管 guile 已经通过 Conan 依赖链正确注入**（`-L` / `-I` / `-lguile-2.2` 都在
`AutotoolsDeps` 生成的 flags 里）。

补丁只把探针的库名改成与实际 soname 一致（`configure` 三处 + `configure.ac`
两处），不改任何行为。源码本身用的就是 Guile 2.x API，所以这是「探针与事实不符」，
不是「上游要 Guile 1.8」。

### 0003-src-main-gsubr-subr-cast.patch（可移植性，非平台专属）

Guile 2.2 的 `libguile/gsubr.h:69` 把 `scm_c_define_gsubr` 的第 5 个形参声明为
`scm_t_subr`，而 `libguile/scm.h` 里

```c
typedef void *scm_t_subr;
```

—— 它是 **`void *`**，不是函数指针类型。上游在 `src/main.cpp` 的 `inner_main()`
里注册了 68 个 Guile 子程序，每一处都写成 `(SCM (*)() ) fcn`，即先把函数指针转成
「无参返回 `SCM` 的函数指针」再交给形参。

C 语言允许函数指针**隐式**转 `void *`（只告警），所以上游按 C 编译时一路无事；
`src/main.cpp` 是 C++ 文件，clang 直接判错——`SCM (*)()` 到 `void *` 没有
「已知转换」：

```
src/main.cpp:69:3: error: no matching function for call to 'scm_c_define_gsubr'
  scm_c_define_gsubr ("current-block-width", 0, 0, 0,
  ^~~~~~~~~~~~~~~~~~
libguile/gsubr.h:69:13: note: candidate function not viable: no known conversion
  from 'SCM (*)()' (aka 'scm_unused_struct *(*)()') to 'scm_t_subr'
  (aka 'void *') for 5th argument
```

（`-ferror-limit` 截断前共报 30+ 处，每个注册点一条。）

补丁把 68 处 `(SCM (*)() )` 一律换成 **`(scm_t_subr)`** —— 正是 Guile 对这个
形参的期待类型，等价于 C 编译器私下的那次隐式转换，语义完全不变：只把断言的类型
从「某种函数指针」改成「该 API 声明的形参类型」。不新增函数、不改调用顺序，整个
注册块落在同一个 hunk 里。

选 `scm_t_subr` 而不是字面 `(void *)`：前者是 API 自己的 typedef，既自证来意，
又能在 Guile 日后把 `scm_t_subr` 改回函数指针类型时仍然编译通过。

> **通用教训**：C++ 里给「以 `void *` 收函数指针」的 C API 传参，必须显式转换；
> 上游能在 C 下编过，不代表 C++ 下能过。凡依赖方的公开头把回调形参 typedef 成
> `void *`（Guile 2.x 的 `scm_t_subr` 即典型），消费者侧一律 `(该 typedef) fcn`。

## 已发布 guile 包的两处头文件缺口（消费者侧兜底）

链接面完好，缺的只是**编译期**的头文件。两处都由本配方在消费者侧兜底，不改上游、
也不依赖 guile 包重新发布：

**(a) 顶层 `libguile.h` 从未安装。** 上游 `Makefile.am:46-47` 把
`libguile.h` 装到 `$(libguileincludedir) = $(pkgincludedir)/$(GUILE_EFFECTIVE_VERSION)`
即 `include/guile/2.2/libguile.h`，而已发布 `guile/2.2.7` 包的 `package()`
只把 `libguile/*.h` 拷进 `include/guile/2.2/libguile/` —— 顶层那一份整个漏掉。
`AutotoolsDeps` 给出的 `-I<guile>/include/guile/2.2` 因此是对的、却找不到东西：
CI 报 `src/ball.h:28:10: fatal error: 'libguile.h' file not found`，
而同一行编译命令里的 `-I` 明明存在。

处理：`compat/libguile.h` 放一份**上游 `guile-2.2.7/libguile.h` 的逐字副本**
（142 行，sha256 `baffa7e9d97488eac7b773ce2858c65d1a127491ae01f9d4ad145937d0bedd82`），
在 `export_sources()` 里随配方导出（conan 会在 `source()` 之前把它合并进
`source_folder`），`generate()` 再把 `-I<source_folder>/compat` 追加进 `CPPFLAGS`。
该副本只做 `#include "libguile/*.h"` 的转发，不含任何实现，与包内已安装的
`libguile/` 子目录天然配套。同仓库先例：`archives/a/abiword-plugin-*/3.0.8`
的 `compat/` 导出方式。

**(b) 公开头依赖 `<gmp.h>` 未随包暴露。** `libguile/numbers.h` 第一件事就是
`#include <gmp.h>`，而 `guile/2.2.7` 的 `package_info()` 没有把 gmp 作为头文件
依赖传递出去（`cpp_info` 里没有 gmp 的 `includedirs`），消费者的 `-I` 里于是没有
gmp。处理：`requirements()` 显式 `self.requires("gmp/6.3.0", headers=True)` ——
版本与 `guile/2.2.7` 自身依赖的 gmp 完全一致，不引入第二份二进制；声明成直接依赖
后 `AutotoolsDeps` 会把 gmp 的 `-I` 一并算进 `CPPFLAGS`。

## 构建处理

| 问题 | 处理 |
|---|---|
| 上游调 `sdl-config`，ohpcd 只发布 sdl12-compat（无该脚本） | `_write_sdl_config()` 在 build_folder 写一个 `sdl-config` 外壳（`--version/--prefix/--cflags/--libs`），经 `SDL_CONFIG` + `PATH` 注入。`AM_PATH_SDL` 用 `AC_PATH_PROG` 找 sdl-config，但它**对已按绝对路径赋值的 `SDL_CONFIG` 直接采信**，所以外壳路径必须绝对。同款做法见 `archives/s/sdl_image/1.2.12` |
| 上游 2011 年的 `config.guess`/`config.sub` 不认识 HarmonyOS | configure 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（gnu 三元组）；设备侧 clang 的真实 target 仍由 conan profile 决定，且 host==build 使 `AM_PATH_SDL` 的 `AC_TRY_RUN` 得以在真机上实跑 |
| OHOS HMDFS 不保留 tarball 里的可执行位 | `_restore_helper_modes()` 给 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/`depcomp`/`mdate-sh`/`config.rpath` 补 `+x` |
| **补丁同时改 `configure` 与 `configure.ac` 导致 mtime 倒挂** | 见下节 |
| **guile 的 `-I`/`-L`/`-l` 必须经 `AutotoolsDeps` 注入** | `generate()` 里 `AutotoolsDeps(self).generate()` → `AutotoolsToolchain(self).generate()`。它不是可选装饰：`AM_PATH_SDL` 只管 SDL 那一路，`AC_CHECK_LIB(guile, scm_boot_guile)` 与 `<libguile.h>` 的搜索路径**完全**来自 `CPPFLAGS`/`LDFLAGS`/`LIBS`（上游 `configure.ac` 没有 pkg-config 兜底），少了它直接死在 `can't find guile. This software REQUIRES guile.` |
| **`sdl_image`/`sdl_mixer`/`sdl_ttf` 的头在 `include/SDL/` 下，`package_info()` 却只声明 `includedirs = ["include"]`** | `generate()` 里在 `AutotoolsDeps` 的 `environment` 上追加 `CPPFLAGS`：`-I<pkg>/include/SDL` ×3（`_sdl_family_include_flags()`）。CI 表现为 `src/main.cpp:29:10: fatal error: 'SDL_image.h' file not found`，**而 configure 上一行刚报过 `checking for IMG_LoadPNG_RW in -lSDL_image... yes`** —— 那一步是纯链接探测，不看头文件，所以「依赖找到了」不等于「头能找到」。只补这三个包：`sdl12-compat`（唯一直接依赖 SDL 头的包）已正确声明 `["include/SDL"]`，其 `-I` 在编译行里本来就是对的。三包各自 `lib/pkgconfig/*.pc` 里写的正是 `Cflags: -I${includedir}/SDL`，`include/SDL` 才是它们对外承诺的搜索路径 |
| **已发布 `guile/2.2.7` 包没装顶层 `libguile.h`，也没暴露 `<gmp.h>`** | 消费者侧兜底：`compat/libguile.h`（上游逐字副本，随 `export_sources()` 导出）+ `-I<source_folder>/compat` 追加进 `CPPFLAGS`；另 `self.requires("gmp/6.3.0", headers=True)`。详见上文专节 |
| **Guile 的 `scm_t_subr` 是 `void *`，而 `main.cpp` 是 C++** | `patches/0003`：68 处 `(SCM (*)() ) fcn` → `(scm_t_subr) fcn`。C 允许函数指针隐式转 `void *`，C++ 不允许（clang 报 `no matching function for call to 'scm_c_define_gsubr'`）。详见上文补丁专节 |
| OHOS libc（musl）无 libintl，`AM_GNU_GETTEXT([external])` 会去找 `-lintl` | `--disable-nls`（知识库 **E027**；同仓库 110 个配方使用）。上游 `po/` 只有 de / ja 两份翻译，且 `src/gettext.h` 在未定义 `ENABLE_NLS` 时把 `gettext()` 退化为恒等宏，功能面无损失 |
| 沙箱内没有 texinfo | `MAKEINFO=/bin/true`（`doc/ballandpaddle.info` 随 tarball 发布，make 若试图重建会被置空） |
| OHOS 沙箱不支持 mkfifo，jobserver 会炸 | `make -j1` |
| **`src/ball.cpp:48-49` 的列表初始化窄化** | `AutotoolsToolchain.extra_cxxflags` 追加 `-Wno-c++11-narrowing`。见下节 |
| **上游 `desktopdir` 硬编码成绝对路径 `/usr/share/applications`** | `make install` 命令行加 `desktopdir=/share/applications`。见下节 |

### C++11 列表初始化窄化是 hard error

CI #62238 实测：

```
src/ball.cpp:48:18: error: non-constant-expression cannot be narrowed from type
    'int' to 'Sint16' (aka 'short') in initializer list [-Wc++11-narrowing]
  SDL_Rect s = { (powerBalls ? width : 0), 0, width, height };
src/ball.cpp:49:18: error: non-constant-expression cannot be narrowed from type
    'int' to 'Sint16' (aka 'short') in initializer list [-Wc++11-narrowing]
  SDL_Rect d = { (int) x, (int) y, 0, 0 };
```

`SDL_Rect` 的四个域是 `Sint16 x, y; Uint16 w, h;`，而 `ball.cpp` 把 `int` 表达式直接
写进**列表初始化**（`{ ... }`）。C++11 起，列表初始化里的窄化转换（`int` → `short`
/ `unsigned short`，即使源码里已经写了 `(int)` 显式转换也仍是 `int`）是**语言规则
层面的硬错误**，不是可以忽略的 warning——`-Wc++11-narrowing` 只是这条语言诊断的名字。
CLI 的 profile 是 `cppstd=17`，于是必然失败。

上游 2011 年的代码是照 C++98 的 `SDL_Rect s = {...}` 写的（那时这是**赋值**语义、
窄化合法），不会为 C++17 回头改；这是老 SDL1.2 代码库的普遍形态。处理沿用本仓库
已验证的「构建期旗标优于补丁」路线（`nuvie/0.5`、`freeimage/3.18.0` 的
`-Wno-register`；`buddy/2.4` 的 `-Wno-error=register`）：`AutotoolsToolchain(self)`
之后 `toolchain.extra_cxxflags.append("-Wno-c++11-narrowing")`，让 clang 把这条诊断
降回 warning。零补丁、不改上游源码，且只影响 C++（ball.cpp 是 `.cpp`，走 `CXXFLAGS`）。

判据：报错行带 `[-Wc++11-narrowing]` 且 cppstd ≥ 11 时，优先用旗标而不是改源码；
换成打补丁则要给每一处窄化补 `static_cast<Sint16>`，改动面随代码库规模增长。

### 桌面文件目录：上游写死绝对路径，用 make 变量覆盖

上游 `Makefile.am:3`：

```make
desktopdir = /usr/share/applications
```

是**绝对路径**、且不带 `$(prefix)`。本配方 configure 时传 `--prefix=/`，
`DESTDIR` 在 install 阶段才生效 —— 但 `desktopdir` 压根不吃 `--prefix`，
于是 `make install DESTDIR=<package_folder>` 把文件装到

```
<package_folder>/usr/share/applications/ballandpaddle.desktop
```

而本仓库的约定是 `<package_folder>/share/applications/`（`--prefix=/` 家族里
其它 `*dir` 变量如 `docdir`、`fontdir` 都写作 `$(datadir)/...` = `/share/...`，
只有这一个例外）。同仓库先例：`algobox/1.1.1` 传 `DESKTOPDIR=/share/applications`，
`nuvie/0.5` 的 `test_package` 也断言 `share/applications/nuvie.desktop`。

本包自己的 `test_package/test_ballandpaddle.sh` E 组断言
`share/applications/ballandpaddle.desktop` 存在且非空（CI #62299 报
`FAIL - 缺失或无内容 share/applications/ballandpaddle.desktop`，
而同一份 CI 日志的 install 段写明文件实际落在
`.../p/usr/share/applications/ballandpaddle.desktop`）。

处理：**不改源码、不加补丁**，在 `package()` 的 install 命令行上加一个 make
变量覆盖：

```
make -j1 install desktopdir=/share/applications DESTDIR=<package_folder>
```

`Makefile.in:235` 是普通赋值（`desktopdir = /usr/share/applications`，没有
`override`），automake 对 `*dir` 类变量一律不加 `override`，所以命令行变量
优先级更高、必然生效。这属于「上游把安装目录写死成绝对路径」这一通用类问题：
只要该变量在 Makefile 里不是 `override` 赋值，就能在 install 命令行上改，
无需触碰 tarball。

> **通用教训**：autotools 的 `--prefix` 只影响以 `$(prefix)` 为基准的那些目录；
> 上游若有 `xxxdir = /绝对/路径` 这样的硬编码，install 出来的位置既不听 `--prefix`
> 也不听 `DESTDIR` 的“层级”语义（`DESTDIR` 只是前置拼接）。先 `grep -n 'dir = /'
> Makefile.in` 把这类变量找全，再决定是否需要覆盖。

### mtime 归一化（`_keep_generated_newer`）

`patches/0002` 同时改了 `configure` 与 `configure.ac`。GNU patch 会把被打补丁文件的
mtime 设成 diff 头里的时间戳，而 `configure.ac` 的 hunk 排在 `configure` 之后，
于是 **`configure.ac` 反而比 `configure` 新**。根 `Makefile.in` 里有
`$(top_srcdir)/configure: $(am__aclocal_m4_deps)`（= `configure.ac`）与
`Makefile: $(srcdir)/Makefile.in` 这类重生成规则，mtime 一倒挂 make 就会试着重跑
`autoconf`/`automake` —— 沙箱里没有 `aclocal-1.11`/`autoconf`，直接失败。

处理：先把 autotools 输入统一 `touch -d '2000-01-01 00:00:00'`，再把生成物
`touch` 成当前时间。同仓库先例：`archives/l/libmodbus/3.2.0`。

## 测试账本

| 维度 | 数量 |
|---|---|
| 上游静态声明（`TESTS` / `check_PROGRAMS`） | 0 |
| 构建系统注册（automake check 目标） | 0 |
| 上游实际执行 | 0 |
| 新增消费者断言（`test_package/test_ballandpaddle.sh`） | 30 |

上游确无测试套件：`Makefile.am` / `src/Makefile.am` 里没有 `TESTS`、没有
`check_PROGRAMS`，`check` 目标只按 `SUBDIRS = src po` 递归；`src/` 下 24 个
`.cpp` 全是游戏本体。证据链见 `test_package/MANIFEST.yml`。

**未执行项**：真正的游戏主循环（SDL 开窗 + 音频 + 从编译期 `BAP_DATADIR`
读关卡脚本与皮肤）。CI 沙箱无显示设备；且 `BAP_DATADIR` 是编译期绝对路径
`/share/ballandpaddle`（`--prefix=/` 的产物，对应「整包安装到根」的部署方式），
测试期包目录并不是安装根，无法在不改动被测产物的前提下满足。故本脚本只断言数据面
**已安装且非空**，不把它计入通过率。

### 为什么其中 10 项断言是「鸿蒙特有测试」

30 项断言里，**B 组（`--version` 5 条）+ C 组（`--help` 5 条）共 10 条**是鸿蒙特有的
（其余 20 条：A 组 1 条可执行性、D 组 5 条参数校验、E 组 14 条安装布局，
在别的平台同样成立）。

`--version` / `--help` 的文本由 `scm_boot_guile(argc, argv, inner_main, 0)` 的
回调 `inner_main()`（`src/main.cpp:66`）打印，且这两条路径在 `initAudio()` /
`gameStateManager.init()`（SDL 初始化）之前就 `exit(0)`（`src/main.cpp:239-248`）。
因此「实跑后能打印出版本串」同时证明：

1. 该 ELF 在 OHOS aarch64 上可执行 —— 动态加载器解析了 `libguile-2.2.so`
   等全部 NEEDED（含传递依赖 libgc / libffi / libunistring / libgmp）；
2. 内嵌的 Guile 2.2 解释器在 OHOS 上 boot 成功（Guile 初始化完成前不会回调
   `inner_main`），即 `GUILE_LOAD_PATH` / `GUILE_LOAD_COMPILED_PATH` 体系可用；
3. `patches/0002` 生效 —— 探针库名与产物实际链接的 guile 一致（否则 configure
   阶段就报 `can't find guile`）。

`test_package/conanfile.py` 聚合了全图依赖的 libdir 进 `LD_LIBRARY_PATH`
（VirtualRunEnv 不覆盖传递依赖，ncdc CI #44337 先例），并用 `bash` 包一层
（OHOS `/system/bin/sh`（mksh）不能可靠执行 ELF 二进制）。
