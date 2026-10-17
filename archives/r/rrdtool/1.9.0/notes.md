# rrdtool 1.9.0 — 适配笔记

任务：平台 10267｜档位【中】｜语言 c｜构建系统 autotools｜首次适配
上游：https://github.com/oetiker/rrdtool-1.x （tag `v1.9.0`）
源码：`rrdtool-1.9.0.tar.gz` 2972593 B
sha256 `5e65385e51f4a7c4b42aa09566396c20e7e1a0a30c272d569ed029a81656e56b`
版本串取自上游 `VERSION` 文件（`AC_INIT([rrdtool],m4_esyscmd([tr -d '\n' < VERSION]))`）= **1.9.0，未归一化**。

---

## 1. configure 可选性清点（本包核心取舍）

原文取自 `sh configure --help` 与 `configure.ac`（行号为 1.9.0 上游原文件）。

rrdtool 的依赖探测统一走 `m4/acinclude.m4` 的 `EX_CHECK_ALL(library, function,
header, pkgconfig-module, min-version, hint, extra-includedir)`。其语义（已读源码确认）：

1. **先裸链** `AC_CHECK_LIB($1,$2)` → 即 `-l<library>`；
2. 失败才回落到 **pkg-config** `--exists $4`；
3. 失败置 `EX_CHECK_ALL_ERR=YES`，末尾统一 `AC_MSG_ERROR([Please fix the library issues listed above and try again.])`。

⇒ 凡是**未被 `--disable-*` 关掉**的 EX_CHECK_ALL 项都是**硬失败**。

### 1.1 无条件硬失败（关不掉）

| 探测 | configure.ac 原文 | 结论 |
|---|---|---|
| glib-2.0 | `EX_CHECK_ALL(glib-2.0, glib_check_version, glib.h, glib-2.0, 2.28.7, …)` (L617) | **硬需求**，无开关 |
| gthread-2.0 | 仅当 glib < 2.32 才触发 (`#if !GLIB_CHECK_VERSION(2,32,0)`) | 2.84 下不触发 |
| pcre | `AC_CHECK_FUNC(g_regex_new)` 失败才 `EX_CHECK_ALL(pcre,…)`，两者皆无则 `AC_MSG_ERROR([you need either glib with g_regex support or libpcre to compile rrdtool.])` (L638) | glib≥2.14 自带 GRegex ⇒ **不需要 pcre** |

### 1.2 由 `--disable-rrd_graph` 控制的硬失败

```
108:AC_ARG_ENABLE(rrd_graph,AS_HELP_STRING([--disable-rrd_graph],[disable all rrd_graph functions]),
109:[enable_rrdcgi=$enableval],[enable_rrd_graph=yes])
646: if test $enable_rrd_graph != no; then
655:   EX_CHECK_ALL(pangocairo-1.0, pango_cairo_context_set_font_options, pango/pango.h, pangocairo, 1.28.4, …)
656:   EX_CHECK_ALL(gobject-2.0,    g_object_unref,                       glib-object.h,  gobject-2.0, 2.58.1, …)
647:   EX_CHECK_ALL(png,            png_access_version_number,            png.h,          libpng,      1.4.8,  …)
```

| 项 | pkg-config 名 | 库名 | 最低版本 |
|---|---|---|---|
| pango+cairo | `pangocairo` | `-lpangocairo-1.0` | 1.28.4 |
| gobject | `gobject-2.0` | `-lgobject-2.0` | 2.58.1 |
| libpng | `libpng` | `-lpng` | 1.4.8 |

**注意：`--disable-rrd_graph` 会连带 `enable_rrdcgi=$enableval`**（L109）⇒ 关图 = 同时失去 `rrdcgi`。

上游 1.9.0 已把 zlib / freetype / fontconfig / cairo-png / cairo-svg / cairo-pdf / cairo-ps 七条探测
**全部 `dnl` 注释掉**（configure.ac L648–654）。⇒ 这四项**不再被 configure 直接要求**：
freetype/fontconfig 只作为 cairo 的传递依赖存在，`-lcairo` 经 `libpangocairo-10.so` 的 NEEDED 解析。
但 `src/rrd_graph.c` 仍**直接 `#include <cairo.h> <cairo-svg.h> <cairo-ps.h> <cairo-pdf.h>`**，
故 cairo 仍是本包的**真实编译期依赖**，必须显式声明（否则就是隐式依赖）。

### 1.3 由 `--disable-rrd_restore` 控制的硬失败

```
111:AC_ARG_ENABLE(rrd_restore, AS_HELP_STRING([--disable-rrd_restore],[disable rrd_restore XML import functions]),
112:  [],[enable_rrd_restore=yes])
661: if test $enable_rrd_restore != no; then
662:   EX_CHECK_ALL(xml2, xmlParseFile, libxml/parser.h, libxml-2.0, 2.7.8, …)
```

⇒ **libxml2 与图渲染无关**：`--disable-rrd_graph` 并不能省掉 libxml2，只有
`--disable-rrd_restore` 才行，而那会砍掉 `rrdtool restore`（XML 回灌）——
dump/restore 是本包核心闭环之一，不划算。

### 1.4 可选降级（探测失败不报错，自动置 no）

| 开关 | 探测 | 缺失行为 |
|---|---|---|
| `--disable-libdbi` (L556) | `AC_CHECK_LIB(dbi, dbi_driver_open)` | `have_libdbi=no`，不报错 |
| `--disable-librados` (L574) | `AC_CHECK_HEADER(rados/librados.h)` + `-lrados` | `have_librados=no`，不报错 |
| `--disable-libwrap` (L590) | `AC_CHECK_LIB(wrap, hosts_access)` | `have_libwrap=no`，不报错 |

这三项**默认都是 yes**。⇒ 构建主机上若有残留头/库，会**静默**产生未声明的运行时依赖。
本配方**显式全部 disable**（参数不是"最少"，而是"可复现"）。

### 1.5 语言绑定

```
696:AC_ARG_ENABLE(perl,  AS_HELP_STRING([--disable-perl]),  [],[enable_perl=yes])
704:if test "x$PERL" = "xno" -o x$enable_perl = xno; then COMP_PERL=   # 找不到 perl 才自动降级
1016:AC_ARG_ENABLE(python, AS_HELP_STRING([--disable-python]), [],[enable_python=yes])
1020:  AM_PATH_PYTHON(2.3,[],[enable_python=no])
```

⇒ 降级是**有条件的**：构建主机上**确实存在** `perl`（`/data/service/hnp/bin/perl`）与
`python3`（`~/.harmonybrew/bin/python3`），所以自动探测会**命中**并尝试编译宿主解释器的
loadable module。交叉编译场景下这条路必然产不出可加载物，且会把 `Makefile.PL` /
`setup.py` 拉进构建。⇒ **全部显式 `--disable-*`**（perl/python/ruby/lua/tcl）。

### 1.6 文档：`--disable-docs` 是硬需求而非优化

```
1033: if test $enable_docs != no; then
1037:   AC_PATH_PROGS(NROFF, [gnroff nroff])
1040:   if test x$NROFF = x; then AC_MSG_ERROR([I need a copy of *nroff to format the documentation]) fi
1043:   AC_PATH_PROGS(TROFF, [groff troff])
1045:   if test x$TROFF = x; then AC_MSG_ERROR([I need a copy of *troff to format the documentation]) fi
```

⇒ 设备上没有 `nroff/gnroff/troff/groff` ⇒ **不禁用 docs 就 configure 直接失败**。

### 1.7 其它开关（保持上游默认，理由见 §3）

`--disable-mmap`（默认 enable；L307 `AC_MSG_ERROR([--enable-mmap requested but mmap() was not detected])`
⇒ 若设备 mmap 探测失败必须显式关掉）、`--disable-pthread`、`--disable-flock`
（L148–153，关掉会 `AC_DEFINE(DISABLE_FLOCK)`）、`--enable-static-programs`。

### 1.8 取舍结论：开图渲染（有实测依据）

台账预判"B潜力：低"，且需要判断"开图 vs 关掉换稳定"。**实测依据**：

1. `ci/conan/profiles/ohos-aarch64`（`os=OHOS arch=armv8 compiler=clang
   compiler.version=15 compiler.libcxx=libc++ build_type=Release`）+
   **全新 `CONAN_HOME`**（本机无任何前序缓存）下逐个跑
   `conan install --requires=<p>/<v> --build=never -pr:h -pr:b`：

   | 包 | 版本 | recipe_rc | binary_rc |
   |---|---|---|---|
   | zlib | **1.3.1（对照组）** | 0 | **0** |
   | glib | 2.84.0.1 | 0 | 0 |
   | pango | 1.50.14.1.1 | 0 | 0 |
   | cairo | 1.18.4 | 0 | 0 |
   | libpng | 1.6.58 | 0 | 0 |
   | libxml2 | 2.15.3.1 | 0 | 0 |
   | freetype | 2.14.3.1 | 0 | 0 |

   对照组与目标包同批同语法 ⇒ "0" 确实代表已发布、"未发布"的报错形态可区分
   （该远端对缺失包会报 `system acceleration policy not enabled`）。
2. 五依赖合并图 `conan install --requires=…(5) --build=never` → **rc=0，无冲突**。
3. 关键副作用：cairo/libpng **必须钉在 pango 解析到的版本**。首次尝试
   `cairo/1.18.4.2`、`libpng/1.6.58.3` 直接
   `ERROR: Version conflict: Conflict between cairo/1.18.4 and cairo/1.18.4.2`
   （`Conflict originates from pango/1.50.14.1.1`）。
   ⇒ 这不是 rrdtool 的问题，是 Conan 图约束；钉低版本既满足 pango 也满足 rrdtool
   自身最低版本（cairo≥1.10.2、libpng≥1.4.8）。

⇒ 图渲染栈**在制品仓有真实 OHOS 二进制**，因此**保留 `--enable-rrd_graph`**（上游默认），
用 §5 的 `rrdtool graph` 出图实测来证明可用性，而不是先验地砍功能。
若图渲染实测失败，再按失败证据降级（见 §5 记录）。

---

## 2. 产物口径（安装后）

`src/Makefile.am`：
```
107: lib_LTLIBRARIES = librrd.la      （+ noinst librrdupd.la）
124: include_HEADERS = rrd.h rrd_format.h rrd_client.h
126: bin_PROGRAMS = rrdtool rrdupdate
129:   bin_PROGRAMS += rrdcgi      # if BUILD_RRDCGI
133:   bin_PROGRAMS += rrdcached   # if BUILD_RRDCACHED
```

⇒ **4 个命令**，其中 `rrdtool` 是**多路调用**主程序（create/update/graph/fetch/… 是子命令，
不是独立二进制），`rrdupdate`/`rrdcached`/`rrdcgi` 才是独立二进制。
`commands.json` 申报集合必须与实装 `bin/` 做集合差为 0（见 §6）。

---

## 3. 已知的 OHOS 适配点（构建实测回填，主理-35 2026-09-25）

1. **E011/E114（configure umask 077）**：首次 configure 即
   `can't create ./confbvBzIN/subs1.awk: Permission denied` →
   `could not setup config files machinery`。配方 build() 内
   `replace_in_file(configure, "umask 077 && ", "")`（probabel 同法）。
2. **陈旧 rrd_config.h（tarball 自带物）**：上游 tarball 里 `src/rrd_config.h` 是维护者
   glibc 机器的 configure 产物（2024-07-29，#define HAVE__NL_TIME_WEEK_1STDAY 等）。
   `rrd_tool.h` 以引号 include `rrd_config.h`，就近命中源码树这份，压掉 build 目录里
   configure 刚生成的正确版（其已 #undef）⇒ `rrd_rpncalc.c:557` 编进 glibc 专属
   `_NL_TIME_FIRST_WEEKDAY` 分支直接编译失败。配方 build() 开头删除该陈旧文件。
   教训：**上游 release tarball 也可能带进 stale 的生成文件**，configure 判对了也白搭。
3. **E386（CONFIG_SHELL 能力探针）**：按配方 `_config_shell()` 实测选择并钉在命令行
   （`/data/service/hnp/bin/bash -c pwd` 在 HMDFS rc=1 的既有结论复核成立）。
4. **musl rindex 无符号**：见 §4.1（0003 补丁，链接级实证）。
5. 依赖钉版：cairo/1.18.4 + libpng/1.6.58（pango 解析版本；高版本 Conan 冲突，见 §1.8）。

---

## 4. musl `rindex()`（预判家族，实测复核）

`src/rrd_daemon.c:4026`：
```c
        port = rindex(addr, ':');
```
`rindex()` 是 GNU/BSD 遗留符号，musl 只在 `_BSD_SOURCE/_GNU_SOURCE` 下经 `<strings.h>` 暴露；
`rrd_config_bottom.h:104-113` 的 `#define strrchr rindex` 是**反方向**的 Solaris/无 STDC_HEADERS
兜底，对本场景无帮助。⇒ 该符号只在 `rrdcached` 这一个编译单元出现（1.4.8 时代在 `rrd_client.c`）。

仓库先例：`archives/n/ntopng/6.6/patches/0004-rrdtool-rindex-to-strrchr.patch`
（对 1.4.8 的 `third-party/rrdtool-1.4.8/src/rrd_client.c` 做 `rindex`→`strrchr`）。
⇒ 本包**复用同一改法**，但目标文件/行上下文已变（1.9.0 在 `src/rrd_daemon.c:4026`），
**按 1.9.0 上下文重写**，非盲套旧补丁。

B 判定：该家族已有 **E534**（musl 缺 GNU/BSD 函数的 weak 兼容层）等条目 ⇒ 见 §7。

---

## 5. 功能实测（主理-35 2026-09-25，A 机第 10 轮构建全绿）

五维账本：

| 维度 | 读数 |
|---|---|
| 上游静态注册 N_static | **0**（上游未接线 make check/TESTS） |
| 本环境注册/执行 | 0 / 0 |
| 通过 | 0 |
| 未执行 | 0（无注册即无未执行） |
| 消费者 | **2 程序 / 27 断言**，27/27 PASS |

- **C API（test_rrd_api）9/9**：rrd_version/rrd_strversion/rrd_create_r/rrd_update_r/
  rrd_info_r 真实调用（建库→写样→元数据链）。注意 1.9.0 的 info 键名换代：
  `pdp_step`→`step`（RD_I_CNT）、数据源按名 `ds[temp].*`（设备探针实测键序）。
- **CLI 全回路（test_rrdtool.sh）18/18**：create→update→fetch→last→first→info→tune→
  dump→restore→graph/graphv→xport 全链 + rrdupdate/rrdcached/rrdcgi 三辅助二进制执行。
  **graph 出非空 PNG 3.4KB**（§1.8 保留图渲染的决策得到实证）；restore 往返数据一致；
  xport 带 XPORT 声明正常导出。
- **能力边界（诚实声明）**：rrdcached 实际绑定端口/常驻行为未深测（仅执行面断言）；
  rrdcgi 仅 CGI 环境外响应检查。

---

## 6. commands.json 集合差

安装清单（src/Makefile.am bin_PROGRAMS）：rrdtool、rrdupdate、rrdcgi（BUILD_RRDCGI）、
rrdcached（BUILD_RRDCACHED）。commands.json 申报四者，与打包 bin/ 集合差 **0**
（消费者 harness [18] 逐一执行验证）。

---

## 7. 路径 B 判定

（待 §4/§5 实测结论出来后回填）

---

## 4.1 rindex 链接级实证（主理-35 2026-09-25 01:2x，A 机）

不依赖整包构建的 5 秒探针：

```
char *rindex(const char *, int);
int main(void){ return rindex("a:b",58)==0; }
clang -x c ridx-probe.c -o ridx-probe
=> ld.lld: error: undefined symbol: rindex
   did you mean: index (defined in .../sysroot/usr/lib/aarch64-linux-ohos/libc.so)
```

结论：OHOS musl sysroot **连符号都没导出**（不是"声明缺失"而是"链接必败"），
0003 补丁（rindex→strrchr，1.9.0 上下文 src/rrd_daemon.c:4026）必要性实锤，
机制同 ntopng/6.6 0004（1.4.8 rrd_client.c），判 hit 复用既有家族条目。
补丁已过 `patch -p1 --dry-run` 干跑校验。
---

**编译结束**: 2026-09-25 04:49
**最终状态**: built
