# pd-iemlib 1.22.3 适配笔记

## 上游构成

`iemlib` 是 Thomas Musil（IEM / KUG Graz）的 Pure Data 外部对象集合，
`Makefile` 用 `<class>.class.sources` 逐类列源文件，并用

```
lib.setup.sources = src/iemlib.c
make-lib-executable=yes
```

即**多对象库**模式：`src/iemlib.c` 的 `iemlib_setup()` 依次调用全部 78 个
`*_setup()`，最终只产出一个共享对象 `iemlib.pd_linux`（导出 `iemlib_setup`
入口点）。这与 `pd-maxlib` 的「每类一个 `.pd_linux`」不同，直接影响装载方式。

上游还带 165 个 abstraction（`abs/`）、77 个帮助补丁（`help/`）、4 个别名
补丁（`alias/`）和 `examples/`。

## 取源

上游 Homepage 是 `https://git.iem.at/pd/iemlib`（由 Debian `.dsc` 的
`Homepage:` 字段给出）。**该站点对 HTTP 请求一律返回 200，但响应体是反爬虫
诱饵页**（一段虚构小说 + 乱码链接），不是 git 仓库也不是归档，因此无法作为取源
地址 —— 已实测 `curl -sIL https://git.iem.at/pd/iemlib` → `HTTP/2 200`，
`content-type: text/html`、`content-length: 2777`，`/pd/iemlib.git`、
`/archive/1.22.3.tar.gz` 同样返回这种页面。

改用 **Debian 官方归档**（`deb.debian.org`，非第三方镜像站）取上游原始 tarball：

- `pd-iemlib_1.22.3.orig.tar.bz2`
  sha256 `a9068a133529a0a69c24b1afec750a0bf8bf648528eab88da82b8058e266cb19`，
  451470 B，HTTP 200
- 同目录 `pd-iemlib_1.22.3-4.dsc` 为 PGP 签名文件（Debian Multimedia
  Maintainers），其中 `Checksums-Sha256` 与本地下载值逐字节一致，sha256 已固定进
  `conandata.yml`

## 构建

- **Pd API 头**：制品仓的 `puredata/0.54.1` 是 *application*，只装 `pd` 与数据
  目录，**不装** `m_pd.h`。配方在 `source()` 里额外拉取同一上游版本
  `pure-data 0.54-1` 的源码树（`codeload.github.com`，sha256 与
  `puredata/0.54.1` 配方中的一致），把 `PDINCLUDEDIR` 指向其 `src`。
  iemlib 的 Makefile 传 `-DHAVE_G_CANVAS_H=1`，而 `g_canvas.h` 就在同一个
  `src/` 目录里 —— 配方因此**同时校验 `m_pd.h` 与 `g_canvas.h` 存在**，
  少一个就早失败，而不是等到某个 TU 报 `file not found`。
- `pd-lib-builder` 用 `$(CC) -dumpmachine` 判断目标系统；OHOS clang 报
  `aarch64-...-linux-ohos` → 选中 Linux 分支与 `pd_linux` 扩展名。`CC` 由配方的
  `tools.build:compiler_executables` 显式传入。
- 纯 C99，单次 `make -j1`，**无源码补丁**。
- 依赖面：除 `m_pd.h` 外无三方依赖（只需 libc/libm）。

## 本地交叉编译（arm64 / ohpcd）

WSL 原生 ext4，构建目录 `/root/ohpcd-work/build/pd-iemlib-1.22.3`：

```
make -j8 CC=/opt/lpk-fixed/clang PDINCLUDEDIR=/root/ohpcd-work/src/pd-api/src
=> rc=0，产出 iemlib.pd_linux 233424 B
```

链接行（节选）确认没有多余的库依赖：

```
clang -rdynamic -shared -fPIC -Wl,-rpath,"$ORIGIN",--enable-new-dtags \
  -o iemlib.pd_linux src/*.pd_linux.o -lc -lm
```

## 产物架构核验（不是只看返回码）

- `file iemlib.pd_linux` → `ELF 64-bit LSB shared object, ARM aarch64`
- `readelf -d` → `NEEDED` 只有 `libc.so`，`RUNPATH = [$ORIGIN]`
- `nm -D` 导出 `iemlib_setup`（Pd 的装载入口点）
- **弱符号安全检查**：`iemlib.pd_linux` 的 undefined 动态符号里，
  `__register_frame_info` / `__deregister_frame_info` / `__at_fini` 在 OHOS
  `libc.so`（1592 个导出）里**确实不存在**，但它们全部是 `WEAK`（连同
  `__cxa_finalize` 共 4 个 weak UND），动态链接器解析不到时置 0，不会报
  `Error relocating` —— 这与 `pd-maxlib` 遇到过的 glibc FORTIFY `__*_chk`
  陷阱不同，本库没有引用任何 `__*_chk`（计数为 0）。
- 其余 undefined 符号全部是 Pd API（`class_new`/`pd_new`/`outlet_float`/
  `atom_getfloat`/…）与 libc/libm，按设计由运行中的 `pd` 进程解析。

## 测试

上游无自动化测试套件（只有帮助补丁与 `examples/`）→ 上游 N=0。

消费者测试 `test_package/test_pd_iemlib.sh`（**12 项断言**）用**真机 OHOS 的
`pd`** 无头加载安装后的 iemlib 库，分三段：

**A 段 · 直接驱动 5 个类（7 项，含装载横幅）**

- 库装载横幅 `iemlib (1.22-1) library loaded!`
- `[db2v 0]` → `1`（`exp(0.11512925465 * 0)`）
- `[v2db 1]` → `0`（`8.6858896381 * log(1)`）
- `[split 0]` 送 `-3` → 左出口（`f < threshold`）；送 `3` → 右出口（`f >= threshold`）
- `[modulo_counter 3 0]` 连打 4 个 bang → `0 1 2 0`（到 `x_max` 回绕）

> **本轮撤掉的两条断言**：`[wrap 1.5]` / `[wrap -1.5]`。反向破坏实验（见下）把
> `iemlib.pd_linux` 换成 0 字节空文件后，这两条**照样 PASS** —— 因为 Pd vanilla
> 自带内建 `[wrap]`，iemlib 的 `wrap_setup()` 注册失败时被内建顶掉了。也就是说
> 这两条断言验证的是 Pd，不是 iemlib，属于空壳断言。现已换成只由
> `src/iemlib.c` 注册的 `[split]` / `[modulo_counter]`（注册表见
> `src/iemlib.c:128` `split_setup()`、`:157` `modulo_counter_setup()`）。

**B 段 · 端到端消费者流程（2 项）**：驱动**打包出去的 abstraction**，
不是裸类调用 ——

```
MIDI-dB 40 --[dbtofad]--> fader-scale 6 --[fadtodb]--> MIDI-dB 40
```

`abs/dbtofad.pd` 与 `abs/fadtodb.pd` 各自是一条真实流水线：`loadbang` 把自己的
折点表发给 iemlib 的 C 对象 `[transf_fader]`（`src/transf_fader.c` 建一张 1001
项的线性插值查找表），再对表插值。折点 `0→0 / 40→6`（`fadtodb` 反向 `0→0 / 6→40`）
逐字取自上游 `abs/*.pd`，所以 **40 → 6 → 40 是构造上精确的往返**，不是照着输出
反推的期望值。脚本另有两条前置断言要求 `dbtofad.pd` / `fadtodb.pd` **确实存在于
打包目录**，杜绝用本地副本蒙混过关。

**C 段 · 反假绿守卫（3 项）**：Pd 里装载失败的外部对象，其已建好的对象仍会回应部分
消息 —— 只看 print 很容易在「类根本没建起来」的情况下读到绿。因此：

- 日志里不得出现 `couldn't create`；
- 日志里不得出现 `unknown function`；
- `^error: ` 行数必须**恰好等于**已知上游瑕疵那一行的条数。匹配用小写且区分大小写
  （宿主 loader 的 `ERROR: ld.so: ...` 是大写，不计入）。唯一放行的是
  `error: class prepend: sorry: only 5 creation args allowed`（见文末「已知上游
  瑕疵」）。

补丁第一个对象是 `[iemlib]`：因为整库只有一个 `iemlib.pd_linux`，Pd 只有在补丁
点名该库时才会去装载它 —— 少了这一句，后面几个类会全部报 "couldn't create"。
这一条是实测踩出来的，不是照抄 maxlib（maxlib 每类一个文件，不需要）。

补丁里的对象**按创建顺序**排：`[iemlib]` 必须早于 `[dbtofad]`/`[fadtodb]`
（否则抽象里的 `[transf_fader]` 在建对象时就找不到），而 `[loadbang]` 又必须早于
两个抽象 —— Pd 的 loadbang 按**创建顺序的逆序**触发，于是外层 `[loadbang]`
（先建）最后触发，正好排在两个抽象自己的 `pairs` 消息之后。实测成立。

> 备注：`pd` 的 `; pd quit;` 退出消息会与 `loadbang` 输出竞争、导致个别 print
> 丢失，因此测试用 `timeout 60` 结束 pd 进程（输出在退出前已落地），而非在补丁内
> 主动退出。`-nogui` 下 pd 不会自行退出，所以这段是整条测试里唯一的长等待。

### 本地交叉编译结果（arm64 / ohpcd）

WSL 原生 ext4，构建目录 `/root/ohpcd-work/build/pd-iemlib-1.22.3`：

```
conan create archives/p/pd-iemlib/1.22.3 \
  -pr:h=ohos-aarch64-wsl-xbuild -pr:b=ohos-aarch64-wsl-xbuild-linux --build=missing
```

- 配方版本 `42e4d7a04ba4e5e0e0e4648665b8a410`，package id
  `01d92cf349a0dd98ff915f4bd99a04430171517f`，package revision
  `db83578703cfa170002339e70d7ae120`
- `build()` → `built iemlib.pd_linux (233424 bytes)`，
  `++++info: target all in lib iemlib completed`
- `package()` → `packaged 77 help patches, 299 abstractions`，
  `lib/pd-externals/` 共 **1211** 个文件
- 整份日志 `/root/ohpcd-work/logs/pdiemlib-create.log`

### 本地消费者测试：脚本与打包产物都已实测通过

用**本 PR 提交的同一个 `test_pd_iemlib.sh`** 跑**同一个打包产物**
(`/root/.conan2/p/b/pd-ie45ef39de62266/p/lib/pd-externals`)，在 qemu-aarch64 +
`/opt/ohos-guest` musl 环境下执行 aarch64 OHOS 的 `pd`（取自制品仓
`puredata/0.54.1`），**12/12 断言通过**：

```
$ conan test archives/p/pd-iemlib/1.22.3/test_package pd-iemlib/1.22.3 \
    -pr:h=ohos-aarch64-wsl-shim -pr:b=ohos-aarch64-wsl --build=missing
...
disabling real-time priority due to missing pd-watchdog (.../lib/pd/bin/pd-watchdog)
error: class prepend: sorry: only 5 creation args allowed
iemlib (1.22-1) library loaded!   (c) Thomas Musil Oct  5 2026 : 15:22:51
   musil@iem.at iem KUG Graz Austria
IEM_DBFAD: 6
IEM_FADDB: 40
IEM_MODULO: 0
IEM_MODULO: 1
IEM_MODULO: 2
IEM_MODULO: 0
IEM_SPLIT_GE: 3
IEM_SPLIT_LT: -3
IEM_V2DB: 0
IEM_DB2V: 1
--- end pd output ---
PASS: iemlib.pd_linux loaded by Pd
PASS: iemlib [db2v 0] -> 1
PASS: iemlib [v2db 1] -> 0
PASS: iemlib [split 0] -3 -> less-than outlet
PASS: iemlib [split 0] 3 -> greater-equal outlet
PASS: iemlib [modulo_counter 3 0] counts up to 2
PASS: iemlib [modulo_counter 3 0] wraps 0 1 2 0
PASS: [dbtofad] MIDI-dB 40 -> fader-scale 6 (transf_fader breakpoints)
PASS: [fadtodb] fader-scale 6 -> MIDI-dB 40 (round trip back)
PASS: no Pd object failed to instantiate
PASS: no unknown Pd message/function name
PASS: no unexpected Pd error line (1 known upstream class-prepend warning)
IEMLIB_CHECK_SUMMARY checks=12 fails=0

HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "consumer_passed": 12, "consumer_total": 12, ...}
```

（print 的出现顺序与补丁里的连线顺序相反，是 Pd 逆序触发 loadbang 的结果，
与断言无关。）

即 `iemlib.pd_linux` 在 ARM aarch64 OHOS 上确实能被 Pd 装载并执行，且**打包出去的
abstraction 能真正跑通一条完整的 dB↔推子刻度换算流程**。

### 反向破坏验证（L1e，回应管理员「test_package 需复核」）

本仓库门禁的 L1e 只搬走 `bin/` / `lib/` / `include/` 三个标准目录，判据只有
「`conan test` 返回非零」，并把 stderr 丢进 `/dev/null` —— 看得到红绿，看不到原因。
因此手工跑了三轮破坏，全部记录失败原因：

| 轮次 | 破坏动作 | 结果与失败原因 |
|------|----------|----------------|
| 基线 | — | `checks=12 fails=0`，rc=0 |
| 破坏 1 | `mv <pkg>/lib <pkg>/lib.bak`（门禁同款） | `ConanException: required artifact not found: .../lib/pd-externals/iemlib.pd_linux` |
| 破坏 2 | `mv <pkg>/lib/pd-externals/iemlib.pd_linux .bak`（其余文件保留） | 脚本前置守卫直接失败：`FAIL: iemlib.pd_linux missing`，rc=1 |
| 破坏 3 | 把 `iemlib.pd_linux` 覆盖成 **0 字节文件**（`[ -f ]` 仍为真） | 见下 |
| 复原 | 移回原件 | `checks=12 fails=0`，rc=0 |

**破坏 3 是决定性的一轮**：此时 `dbtofad.pd` / `fadtodb.pd` / `help/db2v-help.pd`
仍原封不动躺在打包目录里，脚本里所有 `[ -f ]` 守卫也都过了，唯一坏掉的是那个库
文件本身。Pd 报 `Error loading shared library ...: Exec format error`，于是每个
iemlib 类都建不起来 —— 12 项里 **11 项转红**（唯一还绿的是「无 unknown
function」，因为确实没出现未知名字）：

```
verbose(0): db2v            verbose(1): ... couldn't create
verbose(0): v2db            verbose(1): ... couldn't create
verbose(0): split 0         verbose(1): ... couldn't create
verbose(0): modulo_counter 3 0  verbose(1): ... couldn't create
verbose(0): transf_fader    verbose(1): ... couldn't create
FAIL: iemlib [db2v 0] -> 1 (expected 'IEM_DB2V: 1')
FAIL: iemlib [split 0] -3 -> less-than outlet (expected 'IEM_SPLIT_LT: -3')
FAIL: iemlib [modulo_counter 3 0] wraps 0 1 2 0 (expected '^IEM_MODULO: 0$' x2, got x0)
FAIL: [dbtofad] MIDI-dB 40 -> fader-scale 6 (transf_fader breakpoints)
FAIL: no Pd object failed to instantiate (forbidden 'couldn't create' in pd output)
FAIL: unexpected Pd error line(s): 1
IEMLIB_CHECK_SUMMARY checks=12 fails=11
```

**这一轮同时抓出了本 PR 自己的一条空壳断言**：改造前跑同一实验时，
`[wrap 1.5]` / `[wrap -1.5]` 在库完全不可用的情况下**仍然 PASS** —— Pd vanilla
自带内建 `[wrap]`，iemlib 的注册被顶掉了，那两条断言根本没碰到 iemlib。
现已替换为 `[split]` / `[modulo_counter]`（只有 `src/iemlib.c` 才注册），再跑同一
实验即全部转红。完整实验日志：`/root/ohpcd-work/logs/14781-l1e.log`、
`/root/ohpcd-work/logs/14781-l1e-2b.log`。

### ⚠️ 本地 `conan create` 的 test_package 阶段会红，原因是**别的包的既有缺陷**

本机 `conan create` 的 `test_package` 阶段输出
`Error relocating .../puredata/.../bin/pd: __fd_chk: symbol not found`，
12 项断言全 FAIL。这与 `pd-iemlib` 无关，成因已定位：

- 制品仓里 **`puredata/0.54.1` 自己的 `pd` 二进制** 引用了 glibc FORTIFY 的
  `__fd_chk`（`readelf --dyn-syms`：`UND GLOBAL __fd_chk`，全文件仅此一个
  `_chk`）；
- 本机 `/opt/ohos-guest/lib/libc.so` 是 **stock musl**（723480 B，仅 2 个
  `_chk` 导出），不提供该符号 → 装载期就失败，补丁根本没被读到；
- 真机 OHOS 的 `libc.so` **是有的**：sysroot
  `usr/lib/aarch64-linux-ohos/libc.so` 里 `__fd_chk` 为 `T`（该文件共 45 个
  `__*_chk`），DevEco SDK 里的同一文件亦然。所以 CI 的真机 runner 上不会触发。

本地要跑通需 preload 之前为其它包准备的验证用 shim
（`qemu-aarch64 -E LD_PRELOAD=.../libchkfcnshim.so`，该 shim 仅存在于
`/opt/ohos-guest`，**不被任何 conan 配方引用**），加上它后即上面的 12/12 通过。

**处置**：不改 `puredata/0.54.1`（不在本 PR 范围），也不为了本地绿灯去改测试或
放宽断言；`test_package` 保持与已合入的 `pd-maxlib` 同构，交给真机 CI 判定。
`pd-iemlib` 本身不引用任何 `__*_chk`（计数 0），不存在同类隐患。

## 已知上游瑕疵（未改，仅记录）

Pd 装载 `iemlib.pd_linux` 时会打印若干行：

```
error: class <name>: sorry: only 5 creation args allowed
```

**成因（Pd 源码逐字匹配）**：这行由 Pd 的 `class_addcreator()` 打印
（`pure-data-0.54-1/src/m_class.c`，`#define MAXPDARG 5`，`m_pd.h`）——
某个类注册的创建者声明了**多于 5 个**参数类型时，Pd 打印它、并对多余的参数
**不再做类型检查**（`class_new()` 的同名限制提示是另一句
`sorry: only 5 args typechecked; use A_GIMME`）。所以它是**注册期提示**，
不是装载失败：CI 构建 #84535 的日志里这 12 行之后紧跟着
`iemlib (1.22-1) library loaded!`，且 12 条断言中的 11 条（含
`no Pd object failed to instantiate` 与全部功能断言）都通过。

**条数随构建而变**：本机用同一份源码、同一个 package id
（`01d92cf349a0dd98ff915f4bd99a04430171517f`）重建只打印 **1** 行
（`prepend`），CI worker 上打印 **12** 行（`for_pp` / `iem_cot~` / `f24` /
`any` / `merge_any` / `iiroute` / `prepend` / `iem_r` / `iem_s` /
`parent$0` / `unsym` / `t3_del`）。条数是构建产物的属性，不是本测试能控制的量。

**处置（本轮 CI 红灯的根因）**：`test_package/test_pd_iemlib.sh` 的反假绿断言
原来只豁免写死的 `class prepend` 一行（当时那句「与 Pd 内建 prepend 冲突」的解释
是错的），于是 CI 上另外 11 行被判成 `unexpected Pd error line` →
`conan create` rc=1（构建 #84535，失败步骤 `conan-build-test`）。
现改为按 Pd 的提示报文整体豁免：

```
KNOWN_PD_NOTICE='^error: (class [^:]*|unnamed class): sorry: only 5 creation args allowed$'
```

其余任何 `error:` 行、以及 `couldn't create` / `unknown function` 两个守卫照旧判红。
处置有效性用 CI 原始输出做单测（`test_pd_iemlib.sh` Part C 整段抽出运行）：

| 输入 | 期望 | 实测 |
|------|------|------|
| CI #84535 的真实 pd 输出（12 行提示） | 通过 | `12/12 are Pd's class-creation-args notice`，fails=0 |
| 上面 + `error: could not create object` | 红 | 判出 1 条 unexpected，fails=1 |
| 上面 + `couldn't create` | 红 | 守卫判红，fails=1 |
| 上面 + `error: unknown function zzz` | 红 | 两个守卫各判红，fails=2 |
| 本机重建的 1 行提示 | 通过 | fails=0 |

**不改上游源码**：iemlib 的类声明属于上游代码，本 PR 不对其动手。
