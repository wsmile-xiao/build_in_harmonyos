# pd-chaos 0.2 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 1. 这是什么软件

`pd-chaos` 是 Pure Data（Pd）的 **"Chaos PD Externals"**：Ben Bogart 与
Michael McGonagle 编写的一整套**混沌吸引子外部对象**（GPLv2+）。

- 上游源码树 `chaos-0.2/` 里是 **28 个吸引子类的 C 实现**：`logistic`、`lorenz`、
  `rossler`、`henon`、`ikeda`、`tent`、`martin`、`tinkerbell`、`base3`、
  `dejong`、`hopalong`、`pickover`、`popcorn`、`quadruptwo`、`three_d`、
  `latoomut*`、`standardmap`、`strange1`、`attract1`、`gingerbreadman`、
  `threeply`、`unity`、`base`、`mlogistic`、`lotkavolterra`、`latoocarfian`；
  外加 `libchaos.c` / `chaos.h`——计算**最大 Lyapunov 指数**的共享辅助库
  （`lyapunov()` / `lyapunov_full()`）。
- 构建系统是 Pd 官方老式 **"Makefile template" 1.0.11**（随 tarball 发布），
  不是 autotools/cmake。
- 每个类编成 **一个 `<class>.pd_linux` 共享对象**（Pd 用 `dlopen()` 按类名加载），
  `libchaos.c` 编成 `libchaos.so` 被它们 `DT_NEEDED` 依赖。
- **不链接任何 Pd 库**：Pd 主程序自身以 `-rdynamic` 链接，插件里的 Pd 符号
  在 `dlopen()` 时从 Pd 进程映像里解析。
- 编译期唯一依赖是 Pd 的 API 头 `m_pd.h`。

### 源码 URL：官方 SourceForge tarball（R39 合规，无需例外）

上游官网 `https://download.puredata.info/chaos/` 可直接抓取，其目录列表里指向
**官方 SourceForge 发布**（Pure Data 传统托管点）：

```
https://downloads.sourceforge.net/project/pure-data/libraries/chaos/chaos-0.2.tar.gz
sha256 c9f10c5d37d83c0af823c722421b7b4173ef1896c97e103f26cd2bb3963a6fe4  (77969 B)
```

**这就是 R39 要求的官方源，没有任何例外。** 为确保来源可信，做了一次独立交叉
验证（2026-10-04，WSL 实测）：

```
$ curl -sS -o /dev/null -w 'http_code=%{http_code} size=%{size_download}\n' \
      https://download.puredata.info/chaos/
http_code=200 size=28070
$ curl -sSL -o chaos-sf.tar.gz 'https://downloads.sourceforge.net/project/pure-data/libraries/chaos/chaos-0.2.tar.gz'
http_code=200 size=77969
$ curl -sSL -o chaos-deb.tar.gz 'https://deb.debian.org/debian/pool/main/p/pd-chaos/pd-chaos_0.2.orig.tar.gz'
$ sha256sum chaos-sf.tar.gz chaos-deb.tar.gz
c9f10c5d37d83c0af823c722421b7b4173ef1896c97e103f26cd2bb3963a6fe4  chaos-sf.tar.gz
c9f10c5d37d83c0af823c722421b7b4173ef1896c97e103f26cd2bb3963a6fe4  chaos-deb.tar.gz
$ cmp -s chaos-sf.tar.gz chaos-deb.tar.gz && echo IDENTICAL
IDENTICAL
```

即 SourceForge 官方包与 Debian 官方源码池的 `pd-chaos_0.2.orig.tar.gz`
**逐字节相同**，且该 sha256 与 Debian `pd-chaos_0.2-5.dsc` 的
`Checksums-Sha256` 一致；tarball 顶层只有 `chaos-0.2/`，不含 `debian/` 目录、
无 `+dfsg` 重命名。配方取官方源，Debian 侧仅作校验，不构成对 R39 的偏离。

## 2. 上游测试清点（R51）

上游**没有任何自动化测试**，证据（`tar tzf` 完整文件清单）：

- 28 个 `<class>.c` + `libchaos.c` + `chaos.h`
- `Makefile`、`Makefile.nt`、`chaos.vcproj` / `chaos.sln` / `chaos.ncb` / `chaos.suo`
- 28 个 `<class>-help.pd`、`chaos-meta.pd`、`fractal-tools.pd`、`search-tools.pd`
- `examples/` 下 11 个示例补丁、`README.txt`、`LICENSE.txt`
- **没有** `tests/` / `test/` 目录；`grep '^check' Makefile` 无匹配，
  即 `make check` 目标不存在。

结论：上游测试用例数 **N = 0**，无可移植用例；由本次适配新增**鸿蒙特有消费者
测试**（见第 5 节，**80 项断言**）。

## 3. 构建：命令行覆盖，零补丁

**未打任何补丁**，`patches: []`。全部适配都在 `make` 命令行变量上完成：

| 覆盖项 | 值 | 为什么 |
|---|---|---|
| `CC` | OHOS clang（`tools.build:compiler_executables`） | R33：编译器只能来自 Conan profile，不能裸用 `${CC}`。上游默认 `CC = cc` |
| `PD_INCLUDE` | `<puredata 包>/include/pd` | 上游默认 `PD_PATH = /usr` → `-I/usr/include/pd`，worker 上不存在 |
| `UNAME` | `Linux` | **必需**，见 3.1 |
| `prefix` | （空） | 让 `objectsdir` 落到 `/lib/pd-externals`，见 3.2 |
| `STRIP` | `true` | `make libdir_install` 会对每个插件跑宿主 `strip`；不保证宿主有能处理 aarch64 的 `strip`，打包步骤不应依赖环境里的宿主工具（R33 精神）。副作用只是产物未 strip |

### 3.1 坑一：`UNAME != Linux` 时整个平台分支被跳过（CI 必红，本地完全看不出来）

上游 Makefile 用 **全串精确匹配** 判定平台：

```make
UNAME := $(shell uname -s)
ifeq ($(UNAME),Linux)
  EXTENSION = pd_linux
  ALL_CFLAGS += -fPIC
  ALL_LDFLAGS += -rdynamic -shared -fPIC -Wl,-rpath,"\$$ORIGIN",--enable-new-dtags
  SHARED_LDFLAGS += -Wl,-soname,$(SHARED_LIB) -shared
endif
```

分支条件是 `Linux` / `Darwin` / `ANDROID` / `MSYS` / `MINGW` / `GNU` / `Cygwin` …
**没有 OHOS**。而 OHOS CI worker 的 `uname -s` 是 **HarmonyOS**，于是：

- 所有 `ifeq` 都不命中 → `EXTENSION` 为空、`PD_PATH` 为空、`-fPIC` / `-shared` /
  `-rdynamic` / `-Wl,-soname` **一个都没设**；
- 产物名退化成 `attract1.`（空扩展名），链接命令没有 `-shared`，CI 会报
  `ld.lld: error: undefined symbol: main` 以及一串未定义 Pd 符号。

**这个坑在本地 100% 复现不出来**：WSL 开发机 `uname -s` 就是 `Linux`，自动走
Linux 分支，一切正常。只有真机 worker 才暴露——正是 W0b 说的「历史命令/本地命令
在 CI 里逐字可执行吗」那类问题。同类问题在 `pd-libdir/1.11` 的 `system=Linux`
（pd-lib-builder 同样按 `uname` 全串匹配）上已经踩过一次。

修复：`make ... UNAME=Linux`。命令行变量优先级高于 Makefile 里的 `:=` 赋值，
**不需要改 Makefile、不需要补丁**。

### 3.2 坑二：`prefix` 必须留空，否则装到 `/usr/local` 下

```make
prefix = /usr/local
libdir = $(prefix)/lib
pkglibdir = $(libdir)/pd-externals
objectsdir = $(pkglibdir)
# libdir_install:
	$(INSTALL_DIR) $(DESTDIR)$(objectsdir)/$(LIBRARY_NAME)
```

`prefix` 是**字符串拼接**（`$(DESTDIR)$(objectsdir)`，中间没有 `/`）。若沿用默认
`/usr/local`，产物会落到 `<pkg>/usr/local/lib/pd-externals/chaos/`，Pd 找不到。
命令行给 `prefix=`（空值）后 `objectsdir` 变成 `/lib/pd-externals`，配合
`DESTDIR=<package_folder>` 正好得到 Pd 期望的
`<pkg>/lib/pd-externals/chaos/`。

> 注意：**不能**写 `prefix=/`——那会让路径变成 `<pkg>//lib/...`（双斜杠虽能用，
> 但 manifest/门禁里会出现畸形路径）。同理 `PDLIBDIR`（pd-lib-builder）也必须写
> `/lib` 而不是 `lib`。

### 3.3 坑三：`package()` 里的 `make` 也会回落宿主 gcc（R33）

`libdir_install` 依赖 `$(SOURCES:.c=.$(EXTENSION))`，**会重链make 判定为过期的
插件**。第一次 W3 就撞上了：build() 阶段 `CC` 传对了（28 个 .o/.pd_linux 都是
aarch64），package() 阶段漏传，日志里出现

```
cc  -rdynamic -shared -fPIC ... -o "latoomutalpha.pd_linux" "latoomutalpha.o" -lc libchaos.so
/usr/bin/ld: latoomutalpha.o: Relocations in generic ELF (EM: 183)
/usr/bin/ld: error adding symbols: file in wrong format
```

修复：把 `CC="<clang>" UNAME=Linux prefix= STRIP=true` 收进 `_make_opts()`，
**build() 与 package() 共用**，杜绝第二次回落。与 `vtgrab 0.1.8`
（Conan 2.29 `tc.generate()` 放 build() 导致工具链静默失效）是同一类根因：
「一次 make 传对了不代表第二次 make 还传对」。

### 3.4 上游 `ALL_LDFLAGS` 的一个 typo：不用改

```make
ALL_LDFLAGS += -rdynamic -shared -fPIC -Wl,-rpath,"\$$ORIGIN",--enable-new-dtags
```

`$ORIGIN` 与 `--enable-new-dtags` 之间是**逗号**而不是空格。但 clang 的 `-Wl,`
本身就按逗号切分，于是 lld 实际收到的是三个独立选项 `-rpath`、`$ORIGIN`、
`--enable-new-dtags`，结果正是上游想要的 `DT_RUNPATH=$ORIGIN`。实测
`readelf -d logistic.pd_linux` → `RUNPATH [$ORIGIN]`、`NEEDED [libc.so]`、
`NEEDED [libchaos.so]`，**无需补丁**（GNU ld 未必宽容，故记录在此）。

### 3.5 产物没有 `setup()` 也不影响加载（实测结论）

上游只导出 `<class>_setup`（`logistic_setup` 等），**没有**传统 Pd 外部对象约定
的 `setup()` 分发函数（Windows 工程 `chaos.vcproj` 里
`/EXPORT:rossler_setup henon_setup ...` 也印证了这是老式的按类 setup 约定）。
实测（本机 qemu-aarch64 + 制品仓 `puredata/0.54.1` 的真 OHOS `pd` 二进制）：
把 28 个 `.pd_linux` 放进 `-path` 目录，`pd -nogui -nosound -open patch` 能**按类名
正常实例化并驱动全部 28 个类**（`[logistic 0.1 4]` 连打两个 bang 输出
`0.36` / `0.9216`）。所以**不能**自造一个 `setup()` 分发文件——那既无必要，也会
改变上游的加载语义。

## 4. 依赖与头文件（W0）

### 4.1 W0 依赖发布检查

```bash
conan download "puredata/0.54.1" -r=ohpcd --only-recipe     # → 存在
conan install --requires=puredata/0.54.1 -pr:h=ohos-aarch64-wsl \
              -pr:b=ohos-aarch64-wsl --build=never           # → Package installed
```

`pd-chaos` 唯一依赖就是 `puredata/0.54.1`（Pd API 头），**已发布**，
无 `dependency_missing`。

### 4.2 坑：`puredata` 是 application，导不出 include 路径

`puredata/0.54.1` 的 `package_info()` 写着 `self.cpp_info.includedirs = []`
（它是 CLI 应用，不是库）。所以光 `self.requires("puredata/0.54.1")` **拿不到
`-I<...>/include/pd`**，必须自己从依赖的 package folder 探测：

```python
root = self.dependencies["puredata"].package_folder
for candidate in (root + "/include/pd", root + "/include"):
    if os.path.isfile(candidate + "/m_pd.h"): return candidate
```

找不到就抛 `ConanInvalidConfiguration`（而不是让 clang 报一个难懂的错）。
实测 `puredata/0.54.1` 制品里确实有 `include/pd/m_pd.h`、`include/m_pd.h`
以及 `include/pd/{s_stuff,g_canvas,m_imp,x_vexp,...}.h`。

> 仓库内另有两条路：`pd-libdir/1.11` 走**依赖 package_folder 探测**（本包采用），
> `pd-maxlib/1.6.0`、`pd-mjlib/0.2.0` 走**额外拉 pure-data 源码树**。前者少一次
> 网络下载、少一个 sha256 面，选它。
>
> 顺带说明为什么**没有**去改 `puredata` 的配方补 `includedirs`：那属于另一个软件，
> 按 W2/JC6「一个 PR 只含一个软件」必须单独提 PR。

## 5. 测试：80 项断言，驱动真实插件代码

上游无测试可移植 → 新增鸿蒙特有消费者测试
`test_package/pd_chaos_test.c`（`assertion_count = 80`）。

关键点：**Pd 的 API 没有可链接的库**（Pd 是 `-rdynamic` 的可执行文件，
`puredata` 包里也没有 `libpd.so`），而本机/部分 OHOS 环境里 `puredata` 的
`bin/pd` 报 `__fd_chk: symbol not found`（guest musl 版本不匹配，与本包产物无关）。
因此测试用**与 Pd 完全相同的方式**驱动插件：自带最小 Pd 运行时 shim + `dlopen`。

shim 只提供插件真正 import 的 **14 个 Pd 符号**（`readelf --dyn-syms` 对 28 个
`.pd_linux` 取并集得到，其余都是 libc 的）：

```
atom_getfloat  atom_getfloatarg  class_addbang  class_addmethod  class_new
gensym  outlet_anything  outlet_float  outlet_list  outlet_new
pd_new  post  s_float(数据符号)  s_list(数据符号)
```

测试覆盖（80 项）：

| 组 | 项数 | 内容 |
|---|---|---|
| 28 个插件逐个 `dlopen(RTLD_NOW)` + `dlsym(<class>_setup)` + 调用 | 56 | 每个类恰好注册 1 个；类名与文件名一致；`c_classsize > 0`；有 bang 方法；有 reset 方法 |
| 汇总 | 1 | 28 个类全部注册成功 |
| `libchaos.so` | 3 | `dlopen` 成功；导出 `lyapunov()`；导出 `lyapunov_full()` |
| `lyapunov()` 数学 | 5 | a=4 混沌映射 → 指数**为正**；a=1.5 稳定映射 → 指数**为负**；两次均有限值；相同输入**结果完全可复现** |
| `lyapunov_full()` | 2 | 填充并**返回调用者传入的缓冲区指针**；写入有限值 |
| 真实 `logistic` 对象 | 8 | 构造函数建对象；每 bang 输出 1 个值；bang#1 = `4*0.1*(1-0.1)`=0.36；bang#2 = 0.9216；只从第 1 个 outlet 输出；`reset 0.25` 后有响应；结果 = 0.75 |
| 真实 `martin` 对象 | 5 | 构造函数建对象；每 bang 输出 2 个值；y outlet = `a-x`=3.13；x outlet = `y-sin(x)`=-0.0099998；两个值来自**两个不同的 outlet** |
| **合计** | **80** | 与 `PD_CHAOS_CHECK_SUMMARY checks=80 failures=0` 及 `MANIFEST.yml` 的 `assertion_count` 一致 |

写这个 shim 时踩到的五个真实语义坑（都已按 Pd 真实行为修正）：

1. **`pd_new()` 是「分配」原语，不是「构造并调用」**。插件的构造函数第一行就是
   `pd_new(<class>)` 去拿自己的结构体。若 shim 在 `pd_new()` 里再回调
   `cls->c_new`，就变成 `pd_new → ctor → pd_new → …` **无限递归**，
   实测直接爆栈 SIGSEGV。正确分工：`pd_new()` 只 `calloc(c_classsize)` 并写
   `ob_pd`；测试自己提供 Pd 的 `newobject()` 等价物
   （`(*cls->c_new)(gensym(name), argc, argv)`）来带创建参数。
2. **`class_addbang` 在 `m_pd.h` 里是宏**（`#define class_addbang(x,y)
   class_addbang((x),(t_method)(y))`）。要提供同名符号必须先 `#undef`，否则
   编译器把函数**定义**也展开掉，报 "function cannot return function type"。
3. **`gensym` 必须做驻留（intern）**。Pd 每个名字返回固定 `t_symbol`；插件把
   `gensym("reset")` 存进 class 后还要 `gensym("float")`/`gensym("list")`。
   复用同一槽位会覆盖已存的 selector。
4. **`t_float` 在 puredata 构建里是 32 位 float**（`PD_FLOATTYPE`）。吸引子映射在
   `double` 上迭代，但 `outlet_float()` 会把结果**收窄成 float**。测试的期望值
   必须同样过一道 `(t_float)` 收窄，否则 `0.36` 会变成 `0.360000014305` 而误判
   失败。写成 `out_value()` 辅助函数后，32/64 位 float 两种构建都对。
5. `struct _class` / `struct _outlet` 在 `m_pd.h` 里只是**前置声明**（完整定义在
   Pd 私有的 `m_globals.h`，不随 `puredata` 包发布）。插件自己从不解引用它们，
   只把指针交回给 shim，所以在测试里补一个够用的定义即可；
   `t_object`（`struct _text`）在 `m_pd.h` 里有完整定义，`te_outlet` 偏移是对的。

## 6. 环境与验证

- 交叉工具链：OHOS clang 15，target `aarch64-linux-ohos`，profile
  `ohos-aarch64-wsl`（host/build 同 profile，与 CI 一致）。
- W3：`conan create archives/p/pd-chaos/0.2 --name=pd-chaos --version=0.2
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing`
  → **rc=0**，`PD_CHAOS_CHECK_SUMMARY checks=80 failures=0`。
- 产物（77 个文件，不含 conan 自身的 conaninfo.txt / conanmanifest.txt）：
  ```
  lib/pd-externals/chaos/<class>.pd_linux   × 28   ELF64 aarch64 ET_DYN
  lib/pd-externals/chaos/libchaos.so                DT_SONAME=libchaos.so
  lib/pd-externals/chaos/<class>-help.pd     × 28   28 个吸引子的 Pd 帮助补丁
  lib/pd-externals/chaos/fractal-tools-help.pd      工具对象帮助补丁
  lib/pd-externals/chaos/search-tools-help.pd       工具对象帮助补丁
  lib/pd-externals/chaos/chaos-meta.pd              库标记
  lib/pd-externals/chaos/fractal-tools.pd / search-tools.pd
  lib/pd-externals/chaos/examples/*.pd       × 11
  lib/pd-externals/chaos/README.txt, LICENSE.txt
  include/chaos.h                                  lyapunov() 公共头
  licenses/LICENSE.txt
  ```
- 运行期依赖：每个 `.pd_linux` 只有 `NEEDED libc.so` + `NEEDED libchaos.so`
  （后者靠 `RUNPATH=$ORIGIN` 就地解析），**不指向任何第三方库**，不污染
  `/lib` / `/lib64`（R26）。
- L5 说明：产物是 Pd 用 `dlopen()` 加载的**插件**，不是下游要链接的库，
  所以刻意**不**给它们加 `DT_SONAME`（上游意图如此）；CI L5a 只扫
  `lib/` 一级的 `lib*.so`，插件在 `lib/pd-externals/chaos/` 子目录，本来就不在
  扫描范围。唯一按库语义导出的 `libchaos.so` **自带上游的
  `DT_SONAME=libchaos.so`**（`SHARED_LDFLAGS += -Wl,-soname,$(SHARED_LIB)`）。
- 无 `commands.json`（R38）：产物无 `main()`、不可命令行调用，唯一用法是
  `pd -path ...` / `pd -lib chaos`；`pd` 属于 `puredata` 包，那里已声明
  commands.json。故按「库类型不需要」处理：`package_type = "library"`、
  `bindirs = []`、无 `bin/` 安装。

## 7. 已知上游缺陷（本次**如实复现**，未擅自修改）

1. **`gingerbreadman` 的 `|x|` 项恒为 0**：`gingerbreadman.c:54`
   `x_0 = 1-vars[M_y]+abs(vars[M_x]);`。该文件只 `#include <math.h>` 与
   `<stdlib.h>`，`abs()` 取的是 **`int abs(int)`**，实参 double 被截断，
   所以 `|x| < 1` 时该项永远是 0，吸引子退化。本适配不做数值修正
   （那是上游数学问题，改了就等于裁剪软件），在此登记。
2. **部分类构造函数只初始化 `vars_init[]` 不初始化 `vars[]`**（无参创建时
   `vars[]` 是未初始化内存）。真机 Pd 里实测确实打出 `LOADED_threeply: -42`、
   `LOADED_quadruptwo: -0.784812` 之类的随机值。这是上游行为，正常用法是
   `[class <参数>]` 创建或 `reset` 消息。本测试因此用 `newobject()` 语义
   **带创建参数**建对象。
3. 上游用 2013 年的 K&R 风格代码（`logistic -> a` 之类空格箭头、
   `static char *version` 未使用、`t_gotfn` 在 aarch64 上被声明成 varargs），
   clang 15 会给一批 `-Wunused-parameter` 警告。**未加 `-Werror`、未改源码**。

## 8. 遗留 / 后续建议

- 若要真正端到端跑 `pd -lib chaos`，需要先有一个「puredata 制品在干净 OHOS
  运行环境可直接启动」的验证包（当前部分环境 `bin/pd` 报
  `__fd_chk: symbol not found`）。本包的测试用 shim 路径规避了这一环境依赖。
- `Makefile template` 里 `single_install` / `chaos.pd_linux` 单体合并模式需要
  一个上游没提供的 `chaos.c`（含 `setup()` 分发），因此本包**没有**使用单体模式；
  若将来上游补上 `chaos.c`，可以把 28 个插件合成单个 `.so`（Pd 侧更易分发）。

---

**编译结束**: 2026-10-04
**最终状态**: built