# pd-cxc 0.5.2 — HarmonyOS PC 适配笔记

## 这是什么

`cxc`（"cxc pd eternals library powered by zt0ln d4ta"）是 jdl@xdv.org 为 Pure Data 写的
一小库外部对象，主题是随机数、统计和系统查看，2013-01-18 发布 0.5.2。
安装形态是 26 个 Pd 外部对象，一个类一个共享对象 `lib/pd-externals/cxc/<class>.pd_linux`，
Pd 第一次在补丁里实例化某个对象时 `dlopen()` 它。**没有可链接的库，也没有命令行程序**。

26 个类：`ENV ascseq ascwave bfilt bfilt2 cxc_counter cxc_prepend cxc_split cxavgdev cxmean
cxstddev delta~ dist_normal hex2dec ixprint mean~ proc random1 random1~ random_fl random_fl~
random_icg random_icg~ random_tw reson~ utime`

## 源码取自哪里

Debian 官方源码池的 orig tarball，理由与取证见 `conandata.yml`（简版）：

- 上游**没有**任何可通过 HTTP 取到的发布归档：GitHub `pd-externals/cxc`、`pure-data/cxc`、
  `xdv.org/~jdl/cxc/`、SourceForge 全部 404；`git.iem.at` 那个 snapshot URL 虽然回 HTTP 200，
  但返回的是 2353 字节的反爬 HTML（`tar tzf` 报 "not in gzip format"），不是归档。
- `https://deb.debian.org/debian/pool/main/p/pd-cxc/pd-cxc_0.5.2.orig.tar.gz`
  → HTTP 200，49033 字节，sha256 `18d752af…e6bc8`。
- 这个 sha256 正是 PGP 签名的 `pd-cxc_0.5.2-9.dsc` 里 `Checksums-Sha256` 记的值
  （同一份 .dsc 还记了 md5 `b61bcaabd018f1e076f4edfd1bf3b17a` 和大小 49033）。
- 归档是自洽的上游发布件：顶层目录就叫 `cxc-0.5.2/`，65 个条目全部是 2013-01-18 的时间戳
  （不是 2025 年的导入时间），`cxc-meta.pd` 里 `#X text 10 110 VERSION 0.5.2;`，
  Debian 自己的改动在另一个文件 `pd-cxc_0.5.2-9.debian.tar.xz`（10296 字节）里，本配方没用。

## 构建：上游 Makefile 原样用，零源码改动

cxc 用的是老一代 **"Pd library template version 1.0.11"** Makefile，不是 pd-lib-builder
（这点和 pd-ekext 不同：cxc 的归档里自带 Makefile，不缺 `Makefile.pdlibbuilder`，所以
不需要像 ekext 那样换 tarball 源）。因此配方全部通过**命令行覆写 make 变量**来驱动：

| 变量 | 覆写为 | 为什么 |
| --- | --- | --- |
| `CC` | profile conf 里的 OHOS clang | 模板的 Linux 分支不设 CC，落到 make 内建的 `cc` |
| `PD_INCLUDE` | `<puredata 包>/include/pd` | 模板写死 `PD_PATH=/usr` → `/usr/include/pd` |
| `LIBS` | `-lm` | 模板只链 `-lc`，但 `dist_normal.c`/`mean~.c`/`ascwave.c` 用 `sqrt`/`pow`/`log`/`fabs`/`sqrtf`；glibc 上这些在 libc 里，OHOS(musl) 上 libm 是独立库，不加就链不过 |
| `STRIP` | `true` | 见下 |
| `objectsdir` | `/lib/pd-externals` | 默认 `$(prefix)/lib/pd-externals`（`prefix=/usr/local`），覆写后落到 `<package>/lib/pd-externals/cxc` |

### 两个会真的把构建打断的坑

1. **`STRIP` 必须是 no-op。** 模板的 `libdir_install` 里有
   `$(INSTALL_PROGRAM) … && $(STRIP) $(addprefix …)`，而 `STRIP = strip --strip-unneeded -R .note -R .comment`
   是**宿主** strip。x86_64 宿主对刚编出来的 aarch64 ELF 只会报
   `strip: Unable to recognise the format of the input file '…/hex2dec.pd_linux'`，
   然后 `make: *** [Makefile:269: libdir_install] Error 1`。所以配方传 `STRIP=true`。
   代价是产物带 DWARF，26 个对象合计 600 KB、整个包 824 KB，不影响 Pd `dlopen`。
   （不能改成 `STRIP=:` 之外的写法去"修"它：宿主架构不是配方能控制的，CI worker 若恰好是
   aarch64 则本来就该 strip。我们选择确定性 no-op 并在此记录。）
2. **`-lm` 不能省。** 见上表。

### 不需要 patch

上游 tarball 缺 `Makefile.pdlibbuilder` 这类问题在本包不存在（自带 Makefile），
27 个 help patch 一个不缺（`HELPPATCHES ?= $(SOURCES:.c=-help.pd)`，而 `SOURCES` 在
Linux 分支已 `+= $(SOURCES_linux)`，即 26 个类各有 help patch；另有 `fader-help.pd`）。
所以 `patches_applied: []`。

### `uname -m` 会把宿主架构印进日志，但这无害

`make showsetup` 还会打印 `CPU: x86_64` —— 模板在 Linux 分支做 `CPU := $(shell uname -m)`，
即**构建主机**的架构，交叉编译时当然是 x86_64。它只是被记录、**不参与任何 flag**：
这一代模板不像 pd-lib-builder 那样塞 `-mcpu=cortex-a53`，所以最终 `ALL_CFLAGS` 里没有任何
`-march`/`-mcpu`，用的是 OHOS clang 自己的 aarch64 默认目标。showsetup 的输出被配方
逐行打进构建日志（`showsetup| …`），就是为了让这一点可核对。

## 完整的类清单怎么来

不用在配方里硬编码 26 个名字：`make showsetup` 会打印**已经完全展开**的
`SOURCES: ENV.c ascseq.c … proc.c`（那已经是 `SOURCES += $(SOURCES_linux)` 之后的结果），
`build()` 解析这一行，再用它反查 26 个 `.pd_linux` 是否都产出 —— 清单不会和上游漂移。
顺带断言 `LIBRARY_VERSION`（从 `cxc-meta.pd` 里 sed 出来的）等于配方版本 `0.5.2`。

## 一个容易踩的假设：一个文件 ≠ 一个入口

`cxavgdev.c`、`cxmean.c`、`cxstddev.c` 三个文件都只有一行 `#include "mean~.c"`。
所以 `mean~.pd_linux`、`cxmean.pd_linux`、`cxstddev.pd_linux`、`cxavgdev.pd_linux`
**四个产物内容完全相同**，且每个都导出 `mean_tilde_setup`、`cxmean_setup`、
`cxstddev_setup`、`cxavgdev_setup` 四个入口符号。按文件名一一对应入口去检查会漏。

## 测试

上游没有任何自动化测试（Makefile 的 target 只有 all/install/clean/dist/…，没有 check；
tarball 里只有 27 个 help patch 和 `fader.pd`，都是"人在 Pd 里打开"的补丁，没有可比对的输出）。
所以补了消费者测试 `test_package/pd_cxc_test.c`：自建一份最小 Pd 运行时 shim
（`nm -u` 实测 26 个对象的未定义符号并集 73 个，其中 45 个是 Pd API），
以 `-rdynamic` 链接把 shim 导出给外部对象解析，然后：

- **Tier A（26 个对象全覆盖）**：文件是 64 位小端 aarch64 ELF 共享对象；
  `dlopen(RTLD_NOW|RTLD_LOCAL)` 成功（RTLD_NOW 证明它 import 的每个 Pd 符号都能从加载映像
  里解析，RTLD_LOCAL 证明它只靠 Pd 就能满足）；按 Pd 自己 `s_loader.c` 的 mangle 规则
  （`~`→`_tilde`、其它非字母数字→`0x%02x`、前缀 `setup_`）找到入口；`setup()` 之后真的注册出
  同名 Pd 类、实例大小非零、至少一个方法。
- **Tier B（5 个对象驱动真实方法）**：`hex2dec`（sprintf 格式化，含 42.9→42 的 int 截断）、
  `cxc_prepend`（selector 前缀 list + `set` 换前缀）、`cxc_split`（单字符分隔符，
  数字段变 float、其余留 symbol，含"以分隔符结尾会多出一个 atof("")==0.0"这条上游真实行为）、
  `cxc_counter`（上数/下数/回绕/回绕 bang/reset/clear/fl1 的完整状态机）、
  `ENV`（`RAND_MAX` 用 C 库自己的 `RAND_MAX` 断言而非写字面量；`setenv`→`getenv` 真读写进程环境；
  未设变量返回 -1）。
- 打包不变量：26 个 help patch、`fader.pd`、`cxc-meta.pd`（含 `VERSION 0.5.2`）、
  `README.txt`、GPL v2 文本都在位。

期望值全部先从上游 `.c` 源码逐行推导再与实测比对，没有 `echo`/`print` 占位，
也没有改任何期望值去迁就实现。实测：`PD_CXC_TEST checks: 254, failures: 0`，
`HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true}`。

### 写这个 shim 时踩到的三个 Pd 调用约定（都已在测试里写死并注释）

1. **`outlet_new()` 会把对象的第一个 outlet 挂到 `owner->ob_outlet`。**
   Pd 自己的 `m_obj.c` 里 `outlet_new(t_object *owner, t_symbol *s)` 在
   `owner->ob_outlet` 为空时把它设成新 outlet，之后的用 `o_next` 串成链表。
   `hex2dec_new`/`cxc_split_new`/`ENV_new` 都是 `outlet_new(&x->x_obj, …);` **丢弃返回值**，
   以后靠 `x->x_obj.ob_outlet` 找回 outlet。shim 一开始没写这一步，于是这三条路径上
   每个 outlet 的编号都是 -1。cxc_counter 不受影响，因为它自己把返回值存进了
   `t_out1`/`t_out2`。
2. **`s_float`/`s_bang`/`s_list`/`s_symbol`/`s_signal`/`s_anything` 是有名字的真符号。**
   `cxc_split` 直接把 `&s_list` 交给 `outlet_list()`，shim 若让 `s_name` 留 NULL，
   记下来的 selector 就是空串。而 `s_`（Pd 的空符号）必须**保持** `s_name == NULL`，
   因为 `cxc_prepend_new`/`cxc_split_new` 要拿它跟创建参数比（`if (s != &s_)`）。
3. **`t_newmethod` 的调用形状由 class 声明的创建参数类型决定。**
   `A_DEFSYM` 的类（hex2dec / cxc_prepend / cxc_split）Pd 调 `(*newf)(symbol)`，
   `A_DEFFLOAT` 的类（cxc_counter，三个 float）调 `(*newf)(f1, f2, f3)`，
   无创建参数的类（ENV）调 `(*newf)(0)`。**参数在第一个槽位**。
   写成 `(*newf)(NULL, sym)` 会让 `hex2dec_new` 里的 `if (!s->s_name)` 空指针解引用直接段错误
   —— 这条是实测崩出来的，不是猜的。

### `t_float` 是 32 位，别拿 double 字面量去比

`PD_FLOATSIZE=32`，`cxc_split` 的 `SETFLOAT(a, (float)atof(v))` 对 `"3.4"` 给出的是
`3.4000000953674316`。断言必须写 `(double)(t_float)3.4`，写 `3.4` 会假失败。
`ENV` 的 `RAND_MAX` 同理：断言用 C 库自己的 `RAND_MAX` 转 `t_float` 后的值，不写字面量。

### `cxc_counter` 上下数方向不对称（按源码如实断言）

`counter_bang` 的 `case 1`（上数）：越过 `c_high` 时走第一个分支、**静默**回绕到 `c_low`；
正好落在 `c_high` 才发 bang。`case 2`（下数）：落到 `c_low` 发 bang，
再往下一步（越过 `c_low`）才**静默**回绕到 `c_high`。所以"发 bang 的那一步"和
"静默回绕的那一步"在两个方向上是错开的，测试分别断言了这两种情形。

## 已知限制

- **端到端 `pd` 装载已经做了，但本机要过一个 qemu 包装脚本。** `puredata/0.54.1` 的 `pd`
  是 aarch64 OHOS musl 可执行文件，在 WSL 宿主机上直接跑会
  `Error relocating …: __fd_chk: symbol not found`（musl 版本不匹配）。
  本地验证时把 conan 缓存里 `puredata/0.54.1` 的 `bin/pd` 临时换成**放在仓库外**的
  qemu 包装脚本（`LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so` + `qemu-aarch64 -L`），
  跑完按 sha256 还原；包装脚本不参与提交，配方与 `test_package/` 里没有任何一行提到它。
  CI worker 上 `pd` 是原生执行，不需要任何包装。`test_package/run_pd_cxc_e2e.py`
  自带探针：宿主跑不动 `pd` 时整段如实报 SKIP（`executed=0`），绝不把没执行的算成通过。
- **shim 与真 Pd 在「无创建参数」上不同。** shim 给 `hex2dec` 这类对象传 NULL 符号，
  于是走到上游 `if (!s->s_name) s = gensym("file.%d")` 的回落分支；
  真 Pd 传的是空符号（`s_name == ""`，非 NULL），所以 `[hex2dec]` 的真行为是
  **空格式串**（输出空 symbol）。shim 那条断言测的是 shim 契约，真 Pd 的行为由端到端
  用例另行钉住，两边都写在测试与 `MANIFEST.yml` 里，不混为一谈。
- **`error()` 是隐式声明。** `m_pd.h` 0.54 里没有声明 Pd 的 `error()`，
  `cxc_counter.c` 因此靠隐式声明调用它（`-Wimplicit-function-declaration`）。
  这是上游自带告警，没为消警去改上游源码，也没加 `-Werror`；
  测试的 shim 里补了 `error()` 的定义，否则 `dlopen` 解析不到。
  （Debian 的补丁系列里另有 `error.patch` 修这个；本 PR 只带 `array64.patch` 加下面的
  return 修复，其余 Debian 补丁留给后续单独评审。）
- **`split_anything` 有个上游瑕疵**：它把一个未初始化的 `t_atom *a` 传给 `split_anything`
  转发路径（`split_symbol` 里 `t_atom* a; split_anything(x, s, 0, a);`）。
  因为 `argc` 恒为 0，`argv` 永不被解引用，所以是安全的；测试也按这个前提走，
  并在注释里写明。没有改上游。
- **strip 被关掉了**（见上），产物不是 stripped。
- 未纳入范围：上游 `EXTRA_DIST` 里的 `cxc.c` 没有进 `SOURCES`，上游就没构建它，
  本配方保持上游行为（它随源码分发但不作为类安装）；`TODO`/`REFERENCES` 同理。

## LP64 数组访问缺陷与补丁（2026-10-11）

### 现象（都发生在**真 pd** 里，shim 测试看不见）

用 `puredata/0.54.1` 的真实 `pd` 装载打包产物（本机过仓库外的 qemu 包装脚本，见下）：

1. `[cxmean buf]` 对装了 1..8 的 `[table buf 8]` 报 **1.25**（应为 4.5），Pd 同时打印
   ```
   error: an operation on the array 'buf' in the patch 'buf'
   error: failed since it uses garray_getfloatarray while running 64-bit
   ```
2. `[cxmean nosuchtable]` 收到 `mean` 消息时**整个 pd 进程段错误**（rc=139，
   qemu 侧 `uncaught target signal 11`）。

### 根因

`mean~.c` 里四处数组访问都用 `garray_getfloatarray()`，它把数组的 `t_word` 存储强转成
`t_float *` 交出去。这个转换只在 `sizeof(t_word) == sizeof(t_float)` 时成立，而 LP64 上
**`t_word` 是 8 字节 union（它带指针成员）、`t_float` 是 4 字节** —— 于是 Pd 打印上面那两行，
并且**照样把 words 数组交出去**（`g_array.c` 里就是打印错误后
`return garray_getfloatwords(...)`），调用方按 4 字节步长读 8 字节数据，每个采样只读对一半。

`t_word` 的大小是**宿主 Pd 的属性**，不是外部对象编译期能知道的：本构建系统
（上游模板 Makefile 1.0.11）的 `ALL_CFLAGS` 里根本没有 `-DPD_FLOATSIZE`，
`m_pd.h` 会回落到自己的 `#define PD_FLOATSIZE 32`。所以「`#if PD_FLOATSIZE == 64` 包一层」
在这条构建路径上**永远走错分支** —— 实测第一版补丁就是这样：编译通过、日志一切正常，
但产物仍然 import `garray_getfloatarray`，行为一字未变（`nm -D --undefined-only` 一看就露）。

### 修法：照 Debian 的 `array64.patch`，无条件改用 `garray_getfloatwords()`

补丁 `patches/0001-array-access-64bit-safe.patch`，来源是 Debian 对本版本自己的打包：

```
https://deb.debian.org/debian/pool/main/p/pd-cxc/pd-cxc_0.5.2-9.debian.tar.xz
  sha256 3140537a8a54694b83d0b729ab584e0241b62810bd397e0e8ac435a57d66ef76
  -> debian/patches/array64.patch
     sha256 adf938389664a0dadc954708fad9350eed1b33075705deabea1632e624488f40
     Subject: make array-access 64bit safe
     From: Debian Multimedia Maintainers <debian-multimedia@lists.debian.org>
     Last-Update: 2018-02-01, Forwarded: no
```

改动（`mean~.c` 一个文件、14 个 hunk）：

- 四处 `garray_getfloatarray()` → `garray_getfloatwords()`；`float *x_vec` → `t_word *x_vec`；
  取值处 `*fp++` → `fp->w_float` + `fp++`（与 Debian 的做法逐行对齐）；
- **附加改动**：三个 compute 方法（`cxmean_mean`/`cxavgdev_float`/`cxstddev_float`）与
  `mean_tilde_mean` 在报出「no such table / cannot read the array」后**直接 return** ——
  上游没有 return，会拿未初始化的 `x_nsampsintab` 和空指针进求和循环，上面那个 rc=139 就是它。

### 证据（真实 pd，逐条可复现）

| 场景 | 未打补丁 | 打完补丁 |
|---|---|---|
| `[cxmean buf]`（buf 装 1..8） | `MEAN: 1.25` + 两行 64-bit 报错 | `MEAN: 4.5`，无报错 |
| `[cxavgdev buf]`（喂入均值） | `AVGDEV: 1.3125` | `AVGDEV: 2` |
| `[cxstddev buf]`（喂入均值） | `STDDEV: 1.58114` | `STDDEV: 2.44949` |
| `[cxmean nosuchtable]` + `mean` | **rc=139 段错误** | rc=0，`error: nosuchtable: no such table` |

参考值由 Python 按上游公式独立算一遍再比对（`run_pd_cxc_e2e.py` 的 `ref_stats`），
不是把 pd 的输出抄回去当期望。

## 端到端消费者用例：把打包产物放进**真 pd** 里跑

`test_package/run_pd_cxc_e2e.py`（17 项检查，全部实跑）：

| 用例 | 输入 | 校验 |
|---|---|---|
| load | 一个补丁里实例化全部 26 个类 | 无 `couldn't create`；同一补丁配空 `-path` 必须 26 个全部失败（否则这条检查是空的） |
| stats | `[table buf 8]` 用数组自己的 `list` 消息填 1..8，再 `[cxmean]`→`[cxavgdev]`→`[cxstddev]` | 4.5 / 2.0 / 2.44949，与 Python 独立实现比对；日志里不得出现 64-bit garray 报错 |
| hex2dec | `hex:%x` × {0,255,4096}；`tag-%s` × symbol z | `hex:0` / `hex:ff` / `hex:1000` / `tag-z`，与 Python 的 `%` 一致 |
| counter | 用**计数过的** `[until]`（float 进 0 号入口）打 12 个 bang | 恰好 1..10 加第 10 步的 wrap bang，随后静默回绕到 1；与按源码写的 Python 复刻一致 |
| prepend / split | `[list foo 1 2]`→`[cxc_prepend pre]`；symbol `ab/cd`→`[cxc_split /]` | `pre foo 1 2`；`list ab cd` |
| badtable | `[cxmean nosuchtable]` + `mean` | rc=0 且日志里有 `no such table`（上游在这里段错误） |

两个踩过的坑，写在脚本注释里：`[until]` 的**计数从 float 消息进**（`[until 12]` 是普通
`[until]`，给它 bang 会无限循环 —— 实测刷出 200 万行日志，脚本因此加了日志上限）；
补丁文件名不能与对象同名（否则 Pd 报 `can't load abstraction within itself`）。

**这次能发现上面那个缺陷，靠的就是这一层**：shim 的数组是 4 字节/采样、Pd 的数组是
8 字节/采样，所以「读错数据」和「段错误」在 shim 里完全看不见。

## 本地 AI 验视的整改（2026-10-12，P0=0 / P1=0）

平台 AI 检视车道对 `/ai review` 一直不出结论（08:28:03「正在进行中」之后再无结果，
08:40 重试被判「已有 AI 任务在处理中」），按本仓 `review_state.cjs` 的 `RE_LOCAL_AI` 口径
由作者侧补了本地验视。该验视给了 **P0=0 / P1=0**、2×P2 + 2×P3 + 1×P3（非本 PR 引入），
逐条处置：

| 级别 | 意见 | 处置 |
|---|---|---|
| P2 | `package_info()` 里 `includedirs = []` 是死代码；且把**依赖包的绝对路径**写进本包 `cpp_info`（cache 迁移即失效） | **改**：`package()` 把 Pd 头文件复制进本包 `include/pd/`，`package_info()` 用包内相对路径 `["include/pd"]`；`test_package` 解析 includedirs 时兼容绝对/相对两种形态（相对则与 `package_folder` 拼接）。本地 `conan create` 复跑 254 断言全过，证明走的是新路径 |
| P2 | `pd_cxc_test.c` 没有断言数下界守卫（同批 #14783 有三道） | **改**：新增 `PD_CXC_TEST_MIN_CHECKS 254`，退出前 `g_checks < 254` 即打印 `FAIL: only N check(s) ran, the suite defines 254 ...` 并 `return 1`。反证：把门限改成 999 重编同一份源码 → 退出码 **1**；原门限 → 退出码 **0**（同一份产物、同一条命令，只差那个宏） |
| P3 | e2e 层 SKIP 与「跑过且通过」在退出码上不可区分 | **改**：`checks == 0 && skipped` 时在 `HMBS_TEST_PACKAGE_RESULT` 里加 `end_to_end_status: "skipped-on-host"`，并在构建日志里打 warning（原来只有 `end_to_end_skipped: 1`）；「未执行不计通过」的口径不变。CI worker 上该层会真执行——同批 `pd-creb` 的 CI 构建在 CI-014 上跑出了上游单测的真实判定，说明 worker 能原生执行 OHOS 的 `pd` |
| P3 | 读 summary 的代码在文件缺失时静默得 0、字段不足时抛裸 `ValueError` | **改**：summary 缺失 → `ConanException("... produced no summary at ...")`；字段 <4 → 带回显的 `ConanException`（不再静默 0，也不再抛裸异常） |
| P3（非本 PR 引入） | `mean~` 的 `while(n--)` 结束后 `n == -1` 还拿去当除数 | **不修**：改动会改变 DSP 输出，已作为上游待办写在「已知限制」里，与本 PR 的补丁无关 |

本地复跑（两层，含上述改动）：

```
PD_CXC_TEST checks: 254, failures: 0
PD_CXC_E2E checks=17 fails=0
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "end_to_end_checks": 17,
  "end_to_end_passed": 17, "end_to_end_failed": 0, "end_to_end_skipped": 0,
  "end_to_end_status": "executed"}
```

## 干净构建的告警

0 error。告警全部上游自带（每个 TU 5 条左右：未用参数、未使用但已赋值的局部变量、
`error()` 隐式声明），没有为了消警改上游代码，也没有 `-Werror`。

## 本地验证记录（2026-10-05，WSL 原生盘）

- `conan create . -pr:h=ohos-aarch64-lkyz -pr:b=default --build=missing` → rc=0
- 配方 revision `6ed8e87a9848dd325dcf26649e1d14f1`，包 id `01d92cf349a0dd98ff915f4bd99a04430171517f`
- 包内容：`lib/pd-externals/cxc/` 57 个文件 = 26 个 `.pd_linux` + 27 个 `-help.pd` +
  `fader.pd` + `cxc-meta.pd` + `README.txt` + `LICENSE.txt`；`licenses/LICENSE.txt`；整包 824 KB
- 26 个 `.pd_linux` 全部 `ELF 64-bit LSB shared object, ARM aarch64`
- 消费者测试 `PD_CXC_TEST checks: 254, failures: 0`
- 构建目录在 WSL 原生 ext4（`/root/.conan2/p/b/...`，conan 缓存也在原生盘），全程没在 `/mnt/*` 上干重活
