# libratbag 0.18 — OHOS PC 适配笔记

任务: **8355** · 分支: `feat/libratbag-0.18` · 包名: `libratbag` · 版本: `0.18`

## 1. 上游是什么

libratbag 是 Linux 上给游戏鼠标/键盘做配置的库。上游 meson 工程一次构建出：

| 产物 | 说明 | 是否进本包 |
|------|------|-----------|
| `liblur.so` | `liblur`：Logitech Unifying Receiver 访问 | **是**（对外唯一库） |
| `libratbag.so` | 设备抽象层（`ratbag_*` API） | 是（在包内） |
| `ratbagd` | D-Bus 服务，暴露上面两层 | 是（`bin/`） |
| `ratbagctl` | ratbagd 的 CLI 客户端（纯 Python） | 是（`bin/`） |
| `lur-command` | liblur 的调试 CLI | 是（`bin/`） |
| `ratbag-command` | swig 生成的 Python 绑定 CLI | **否**（见 §3） |
| `data/*.device` | 设备配置文件库 | 是（`share/`） |

对外 `package_info` 只声明 `liblur`：`self.cpp_info.libs = ["lur"]`、
`includedirs = ["include"]`、`pkg_config_name = "liblur"`。

## 2. 源码与依赖

- 源码: `https://github.com/libratbag/libratbag/archive/refs/tags/v0.18.tar.gz`
  （sha256 `8a7f8bf00c21ef5ad534e2804ed537f2fc6521a3932dd822c438e561a85a1bcd`）
  - 上游 releases 页**只有** GitHub 自动生成的 Source code 归档，没有手工上传的
    `libratbag-0.18.tar.gz` 资产 —— `/releases/download/v0.18/libratbag-0.18.tar.gz`
    实测 404，所以用 tag archive URL。
  - 解出目录 `libratbag-0.18/`，配方 `strip_root=True` 拉平。
- `subprojects/` 为空、无 git submodule ⇒ `wrap_mode=nodownload` 不会联网。

上游 meson 依赖与提供者：

| 上游写法 | 本仓库提供者 | 说明 |
|----------|--------------|------|
| `dependency('libudev')` | `eudev/3.2.14` | `pkg_config_name` = `libudev`，天然对齐 |
| `dependency('libevdev')` | `libevdev/1.13.7` | |
| `dependency('glib-2.0')` | `glib/2.84.0.1` | 见 §4.3 |
| `dependency('json-glib-1.0')` | `json-glib/1.10.6` | |
| `cc.find_library('unistring')` | `libunistring/1.0` | 不是 pkg-config，见 §4.4 |
| `dependency('libsystemd')` | `systemd/261` | `meson.build:73` 的 `dep_logind`，**无条件**求值（ratbagd 的 sd-bus/sd-event）。见 §4.5 |
| `dependency('systemd')` | 无（`-Dsystemd=false`） | 只在 `meson.build:78` 的 `enable_systemd` 分支求值；本配方关掉的是这个 |
| `dependency('check')` | `check/0.15.2`（test_requires） | 4 个 C 测试程序 |

> 两个 systemd 相关 dependency 要分清：`libsystemd`（`dep_logind`）**无条件**，
> `systemd`（unit 目录查询）才受 `-Dsystemd` 控制。本配方关的是后者
> （`toolchain.project_options["systemd"] = False`，即 meson 的 `-Dsystemd=false`）。

> `systemd/261` **只装 `libsystemd`，不含 `libudev`**（见 `archives/s/systemd/261`）。
> 这是本包最容易踩的一处：只加 systemd 会得到一个找不到 `libudev` 的配置错误。

## 3. 两个 portability 补丁

### 3.1 swig / libpython 可选化

`patches/0001-meson-make-python-bindings-optional.patch`（6725 字节，
`patch -p1 --dry-run` 通过）。

上游 `meson.build` 无条件做两件事：

1. 找 libpython：
   ```meson
   dep_python3 = dependency('', required : false)
   pymod = import('python')
   py3 = pymod.find_installation()
   if meson.version().version_compare('>= 0.53.0')
     dep_python3 = py3.dependency(embed : true)
   endif
   ...
   ```
2. 找 swig 并生成绑定：
   ```meson
   # ratbag-command uses Swig bindings to call libratbag directly
   swig = find_program('swig')
   ...
   custom_target('ratbag-command', ... install: false)
   ```

OHOS 上两者都没有：没有 swig 二进制，Python 只以 worker 上的普通解释器形式
存在（没有 embed 开发库）。补丁：

- `meson_options.txt` 追加
  ```meson
  option('python-bindings',
  	type : 'boolean',
  	value : true,
  	description : 'Build the swig-based Python bindings and ratbag-command (requires swig and libpython, default=yes)')
  ```
  （默认 `true` ⇒ 保持上游默认行为，非 OHOS 平台不受影响）
- `meson.build`：`enable_python_bindings = get_option('python-bindings')`，
  把 libpython 的三段查找与整个 swig 块分别包进 `if enable_python_bindings` /
  `endif`。
- `py3 = pymod.find_installation()` **保持无条件**：meson 自身与 3 个纯 Python
  数据校验测试都需要解释器，OHOS worker 上有 `python3`（这也是仓库里 glib 等
  meson 包能构建的前提）。

配置时用 `-Dpython-bindings=false`。同一思路仓库内有先例：graphviz 的
`--disable-swig`。

### 3.2 OHOS 没有 `program_invocation_short_name`

`shim/progname_shim.h`（配方层注入，**不是补丁**）。

`tools/` 下 4 个命令行工具在打印 usage 时、以及 `ratbagd/ratbagd.c` 在打印错误
前缀时，用了 `program_invocation_short_name`：

| 文件 | 行 | 用法 |
|---|---|---|
| `tools/hidpp10-dump-page.c` | 76 | `printf("Usage: %s [page] [offset] /dev/hidraw0\n", ...)` |
| `tools/hidpp20-dump-page.c` | 92 | 同上 |
| `tools/hidpp20-reset.c` | 68 | `printf("Usage: %s [sector] /dev/hidraw0\n", ...)` |
| `tools/lur-command.c` | 180 | 多行 usage 的最后一个实参 |
| `ratbagd/ratbagd.c` | 79、640 | `log_error()` 的前缀 `"%s error: "`，以及另一处错误输出 |

`ratbagd/ratbagd.c` 是**后来才暴露**的一处：最初只覆盖 `tools/`——那时 CI
就停在 `tools/*.c` 那批目标上，看不到后面的编译单元。`tools/` 修好后编译继续
走到 `ratbagd.p/` 与 `ratbagd.devel.p/`（同一个 `ratbagd.c` 编两遍，两个不同
的 D-Bus 接口),于是同一个符号又各报一遍：

```
../ratbagd/ratbagd.c:79:32: error: use of undeclared identifier 'program_invocation_short_name'
        fprintf(stderr, "%s error: ", program_invocation_short_name);
../ratbagd/ratbagd.c:640:5: error: use of undeclared identifier 'program_invocation_short_name'
2 errors generated.
```

这是 **glibc 扩展**：`<errno.h>` 只在 `_GNU_SOURCE` 下才声明它，而 OHOS 的 musl
头文件根本不提供该声明，于是 `-std=gnu99 -Werror=…` 下直接编译失败：

```
tools/hidpp10-dump-page.c:76:53: error: use of undeclared identifier 'program_invocation_short_name'
```

它由 **C 运行时代码在 `main` 之前自动填好**（保存 `argv[0]` 的 basename），属于
「上游只在乎交互体验、不在乎 POSIX 可移植性」的写法——不是缺陷，只是平台差异。

**修法（配方层 feature detection，不改上游源码）**：musl 的动态加载器提供了
语义完全相同的 `__progname`（同样是 `argv[0]` 的 basename），`shim/
progname_shim.h` 在非 glibc 下把它别名过去：

```c
#ifndef __GLIBC__
extern char *__progname;
#define program_invocation_short_name __progname
#endif
```

配方把它以 `-include` 前置到每个编译单元（`_progname_shim_args()` →
`MesonToolchain.extra_cflags`），因此 5 个使用点**一个字节都不改**。

为什么不再走补丁（旧 0002 的做法）：`.gitcode/review-memory.md` R8 要求
`patches/` 下的补丁**默认不得引入平台条件编译宏**，libc 差异应在配方层用
feature detection 解决。旧补丁在 5 个文件里各插一段 `#ifdef __OHOS__` +
`#define program_invocation_short_name "<安装名>"`，既是平台宏、又把程序名
硬编码成字面量（丢失了 `argv[0]` basename 的真实语义），AI 检视判为
🟠 High Priority。现改为 shim，与 `archives/k/kbd/2.9.0/shim/progname_shim.h`
同一做法（该包 src 里 10 处用到同一符号，同样用 `-include` 注入）。

为什么是 `__progname` 而不是别的：

- **语义完全等价**：musl 的 `__progname` 同样是动态加载器在 `main` 之前填好的
  `argv[0]` basename，正是 glibc `program_invocation_short_name` 的定义。
- **不赌符号是否导出**：musl 明确导出 `__progname`（LLD/libc 集成测试都用到），
  比「补一个 `extern` 声明去赌 `program_invocation_short_name`」稳。
- **`getprogname()` 不可用**：它是 BSD 扩展，glibc 根本没有，同样不可移植。
- **`#ifndef __GLIBC__` 而非 `__OHOS__`**：判据是 libc 家族（glibc 有原生声明、
  musl 没有），与操作系统无关；glibc 下 shim 自动失效，上游行为零影响。

## 4. 配方侧的六处适配（不改上游源码）

### 4.1 `shared=False` 直接拒绝
上游 liblur 硬编码 `shared_library()`。`validate()` 里显式拒绝静态构建，
让它以一个清楚的错误收场，而不是在 meson 阶段炸出难懂的信息。

### 4.2 meson 机器文件缺 `ar`/`ranlib`/`pkg-config`
`MesonToolchain` 生成的 `conan_meson_native.ini` 的 `[binaries]` 段在 OHOS
worker 上缺这三项，`_inject_meson_tools()` 从 conf 与已知 SDK 路径补注入。

### 4.3 glib 的 `proxy-libintl`
OHOS 上 glib 与子项目 `proxy-libintl` 一起构建，`g_libintl_*` 就在 glib 包里，
但 glib 配方的 `package_info` 没声明 `intl` 系统库 ⇒ `PkgConfigDeps` 生成的
`glib-2.0.pc` 缺 `-lintl` ⇒ 消费者 `undefined reference to 'g_libintl_*'`
（`libratbag-util.c` 用到字符串转换）。`_augment_glib_pkg_config()` 就地增补
生成的 `.pc`，并把 `-lintl` 加进 meson 的 `c_link_args`。

### 4.4 `cc.find_library('unistring')`：只给库、不给头

上游 `meson.build:68` 用的是 `cc.find_library('unistring')` 而不是
`dependency()`，因此 `pkg_config_path` 帮不上忙，而且**它只探库、不探头**。

库那一半由 `_dependency_link_args()` 补：给每个非 check 的 host 依赖加
`-L<libdir> -Wl,-rpath,<libdir>`，让 clang 能找到 `libunistring.so`。
CI 日志里 meson configure 的那行 `Library unistring found: YES` 就是这一步
成功的证据。

头那一半**没有任何机制会补**——`cc.find_library()` 的结果是一个裸库对象，
不携带 include 目录，meson 自然不给 `-I`。直到 CI 走到
`ratbagd/ratbagd-profile.c` 才炸出来：

```
../ratbagd/ratbagd-profile.c:34:10: fatal error: 'unistr.h' file not found
#include <unistr.h>
```

（同一文件 :35 还有 `#include <uniconv.h>`，用到 `u8_check()` 与
`u8_strconv_from_encoding()`，所以两个头都得在。）

Linux 上没人发现，是因为 `libunistring-dev` 把这两个头装进 `/usr/include`
——编译器的默认搜索路径；OHOS 上它们是 Conan 包 `<pkg>/include` 下的文件。
修法与 4.7 的 eudev 完全同构：`_project_include_args()`（原
`_udev_include_args()`，现在同时覆盖 `eudev` 与 `libunistring`）把这些包的
`includedirs` 转成项目级 `-I`，经 `MesonToolchain.extra_cflags` 注入。

### 4.5 `b_ndebug`：Conan 的 MesonToolchain 会强塞 `-DNDEBUG`，上游硬拒

上游 `src/libratbag-private.h:37` 写死：

```c
#ifdef NDEBUG
#error "libratbag relies on assert(). Do not define NDEBUG"
#endif
```

而 Conan 的 `MesonToolchain` 在 `buildtype != debug` 时**硬编码**
`self.b_ndebug = "true"`（`conan/tools/meson/meson_toolchain.py`），于是写入
native file 的 `[built-in options]` 里有 `b_ndebug = true`，每条编译行都带
`-DNDEBUG` ⇒ **全部 .c 编译失败**（CI #b71432 实测，每个 `FAILED:` 都是这
一条 error）。

meson 自己的 `b_ndebug` **默认就是 `false`**（从不在 release 里定义 NDEBUG，
这是它为了向后兼容刻意保留的、被广泛吐槽的行为），上游的 `#error` 正是按
这个前提写的。配方在 `MesonToolchain(self)` 之后显式 `toolchain.b_ndebug =
"false"`，恢复上游默认语义。

顺带：断言被关掉的话 §5 那几个 check 程序就变成空壳，「测试通过」也就没什么
意义了——保持断言开启同时保住了测试的有效性。

### 4.6 已发布的 `systemd/261` 包**不含** `libsystemd.pc` ⇒ 由消费者合成

`meson.build:73` 的 `dep_logind = dependency('libsystemd', version : '>=227')`
是**无条件**求值的（`ratbagd` 用它做 sd-bus/sd-event/sd_notify）。但 ohpcd 上
已发布的 `systemd/261` 二进制包里 `lib/pkgconfig/` 是**空目录**：

```
systemd/261#a7f1686780c95492f9732fd12b0c6ede
  └─ .../p/  include/systemd/sd-*.h  libsystemd.so{,.0,.0.44.0}  lib/pkgconfig/   ← 空
```

（`conan download` 后实测，只有 `include/`、`lib/`、`licenses/`。）

**为什么缺**：systemd 配方的 `build()` 只构建 `libsystemd` 目标、刻意不走
`meson.install()`（全量 install 会触发 1281 个目标而超时），而 meson 的
`pkg.generate()` 产物只有当对应目标被构建时才落到 `<build>/libsystemd.pc`；
配方 `package()` 里那段

```python
pc_src = os.path.join(self.build_folder, "libsystemd.pc")
if os.path.isfile(pc_src):   # ← 没生成就静默跳过
```

因此悄悄没装上。这不是本包能改的（改它属于"动别人的包"），所以由消费者兜底。

**再加一层**：PkgConfigDeps 是按**包名**生成 `.pc` 的，`systemd` 包生成的是
`systemd.pc`，与上游要的 `libsystemd` 名字也对不上——所以两个坑叠在一起，
CI 报的是

```
libratbag/0.18: WARN: libsystemd.pc not found in the systemd package
../meson.build:73:14: ERROR: Dependency "libsystemd" not found (tried pkg-config and cmake)
```

**做法**：`_alias_dependency_pc()` 写一份 `libsystemd.pc` 进
`generators_folder`（meson 的 `pkg_config_path` 首位）。包里有真 `.pc` 就复制
并把 `prefix=` 改写成真实包目录（systemd 那份是 `--prefix=/` + DESTDIR 装的，
直接复制会让 `-I${includedir}` 落到根目录）；没有就按包内真实布局
（`include/systemd/sd-*.h` + `lib/libsystemd.so`）合成最小一份：

```
prefix=<包目录>
libdir=${prefix}/lib
includedir=${prefix}/include
Version: 261            # 取自 dependency.ref.version，满足上游 >=227
Libs: -L${libdir} -lsystemd
Cflags: -I${includedir} -I${includedir}/systemd
```

上游以 `#include <systemd/sd-bus.h>` 引用，故 `-I${includedir}` 是必需的；
`-I${includedir}/systemd` 与 systemd 自己那份 `.pc` 的 `subdirs` 行为一致。
思路同 `archives/a/accountsservice/26.27.3` 的 `_prepare_systemd_stub()`
（那边 OHOS 无 systemd 只能造桩，这边指向真包）。

### 4.7 `libudev.h` 找不到：上游只在部分目标上声明 `dep_udev`

CI #b71457 实测：

```
Run-time dependency libudev found: YES 3.2.14          ← meson 确实解析到了 eudev
...
FAILED: [code=1] libhidpp.a.p/src_hidpp-generic.c.o
/data/service/hnp/bin/clang -Ilibhidpp.a.p -I. -I.. … -c ../src/hidpp-generic.c
In file included from ../src/libratbag-util.h:34:
../src/libratbag-util.h:34:10: fatal error: 'libudev.h' file not found
```

**注意编译行里一个 eudev 的 `-I` 都没有**——meson 明明找到了 `libudev 3.2.14`，
却没把它的 include 目录传下去。原因是上游 `meson.build` 只给部分目标声明了
`dep_udev`：

| 目标 | `dependencies:` | 有 udev？ |
| --- | --- | --- |
| `libutil.a` | `[ dep_udev ]`（:87） | ✅ |
| `libhidpp.a` | `[ dep_lm ]`（:108） | ❌ |
| `libasus.a` | `[ ]`（:120） | ❌ |
| `liblur.so` | `[ dep_libutil, dep_libhidpp, dep_libasus ]`（:138） | ❌（传递也算没有） |
| 三个 `hidpp*-dump-page` | `[ dep_libhidpp ]`（:251/:260/:269） | ❌ |

而 `#include <libudev.h>` 在 `src/libratbag-util.h:34`——**公共头**，凡包含它的
`.c` 都需要这个头。meson 的注入规则是「只给在 `dependencies:` 里显式声明了该
dependency 的目标加它的 `-I`/`-L`」，`dep_udev` 不在这些目标里 ⇒ 编译行无 `-I`。

**为什么 Linux 上没人发现**：发行版的 `libudev-dev` 把 `libudev.h` 装进
`/usr/include`，那是编译器的**默认搜索路径**，`-I` 可有可无。OHOS 上的 eudev
是 Conan 包，头在 `<包目录>/include`，不在任何默认路径上，于是必然失败。

**做法**：上游自己在 `meson.build:45` 就用
`add_project_arguments(cflags, language: 'c')` 做项目级注入；这里等价地走项目级
`c_args`——`_project_include_args()`（原名 `_udev_include_args()`，4.4 的
libunistring 也并进了同一个方法）把 eudev 的 `includedirs`（`cpp_info.includedirs
= ["include"]`）逐个转成绝对 `-I`，经
`MesonToolchain.extra_cflags` 写进 native file 的 `[built-in options]`
`c_args`，一次覆盖全部目标。**不改上游 meson.build、不加补丁**。

另一种写法是打补丁给 `libhidpp` / `libasus` / `liblur` / 三个 dump-page 逐个补
`dep_udev`，改动面大且与上游漂移；项目级 `-I` 与上游 `add_project_arguments`
的语义完全一致，更小更稳。

## 5. 上游测试与验证结果

### 5.1 上游测试注册（顶层 `meson.build`）

`test()` 注册 **10 个**程序：

| # | 程序 | 定义位置 | 口径 |
|---|------|----------|------|
| 1 | `data-parse-test` | `test/data-parse-test.py` | 遍历 `data/` 下全部 `.device`，校验能被解析 |
| 2 | `duplicate-test` | `test/duplicate-check.py` | 校验 `.device` 的 VID/PID 组合无重复 |
| 3 | `receiver-id-test` | `test/receiver-check.py` | 校验 liblur 登记的接收器 VID/PID 与 `data/` 一致 |
| 4 | `test-context` | `test/test-context.c` | check，**6** 个用例 |
| 5 | `test-device` | `test/test-device.c` | check，**23** 个用例 |
| 6 | `test-util` | `test/test-util.c` | check，**2** 个用例 |
| 7 | `test-iconv-helper` | `test/test-iconv-helper.c` | check，**4** 个用例 |
| 8 | `ratbagctl-test` | `test/ratbagctl-test.py` | 拉起 ratbagd + 系统 D-Bus |
| 9 | `python-black-check` | `test/python-black-check.sh` | 需要 pip 安装的 black |
| 10 | `python-ruff-check` | `test/python-ruff-check.sh` | 需要 pip 安装的 ruff |

前 3 个无条件注册；第 4–7 个在 `if enable_tests` 块内（配方 `-Dtests=true`）。
第 4–7 共 **35** 个 `tcase_add_test` 用例。

> **rule4 口径核对**：上游默认分支 `master` 与钉版 tag `v0.18` 的 `test/`
> 逐文件一致 —— 4 个 C 文件的 `tcase_add_test` 计数同为 35，测试程序同为 10
> 个（已用 `raw.githubusercontent.com/.../master/` 逐文件复核），无版本差，
> 声明的 10 / 35 不存在少报。

### 5.2 为什么 4 个 C 程序不需要插鼠标

`test-device.c` 的夹具走 `ratbag_test_device_new()`：这是上游专为测试写的
**纯内存设备**（`src/driver-test.c` / `libratbag-test.c`），所有 profile /
分辨率 / 按键 / LED 读写都发生在这块内存上。`test-context.c` 同理。因此这 4
个程序在没有任何 hidraw 节点的 CI 机器上照样全绿。

### 5.3 三个必然失败的程序（如实声明）

| 程序 | 失败根因 |
|------|----------|
| `ratbagctl-test` | 先起 `ratbagd`，再经**系统 D-Bus** 与它通信。OHOS 沙箱拒绝 AF_UNIX bind（`Operation not permitted`，见 `archives/d/dbus/1.14.10.2/manifest.yaml`），且已发布的 dbus 包只含客户端库、不含 `dbus-daemon` |
| `python-black-check` | 需要 pip 安装的 `black`；OHOS worker 没有 pip 网络访问，也没有该二进制 |
| `python-ruff-check` | 同上，需要 `ruff` |

这三个**仍然被构建、被执行**（不是 SKIP）。配方 `_assert_suite_results()`
读 `meson-logs/testlog.txt` 的汇总块做硬断言：

- `Timeout == 0`、`Unexpected Pass == 0`；
- `Fail` 的**数量与身份**必须恰好等于上面这三个程序 —— 少一个（比如某个
  测试因为环境变化被静默跳过）或多一个（真实回归）都抛异常；
- `Ok` 必须 ≥ 7，且 7 个必须通过的程序名逐个出现在 Ok 列表里。

这就是「不以退出码为准」的原因：`meson test` 在 SKIP 与「用例根本没注册」
时同样返回 0，只看退出码会把「测试消失了」误判成通过。

### 5.4 适配后实测口径

| 口径 | 上游 | 本平台 | 通过率 |
|------|------|--------|--------|
| 测试程序 | 10 | 7 | **70.0%** |
| check 用例 | 35 | 35 | **100%** |

两个口径都在规则要求的 50% 以上。

### 5.5 test_package（消费者视角，rule12 鸿蒙特有测试）

`test_package/test_lur.c` —— 全部**无需硬件**，21 条 CHECK 断言：

- `enum lur_device_type` 的数值 ABI：`UNKNOWN 0x00 / KEYBOARD 0x01 / MOUSE 0x02
  / NUMPAD 0x03 / PRESENTER 0x04 / TRACKBALL 0x08 / TOUCHPAD 0x09`，逐个对照
  **安装后**的 `<liblur.h>`（这些数值是 HID++ 设备类型特性在协议上报告的值，
  消费者 switch-case 依赖它们）；
- `lur_is_receiver()`：两款 Unifying Receiver PID（`0xc52b`、`0xc532`）判真；
  同厂非接收器 PID（`0xc534`）与他厂 PID 判假；`0x0000/0x0000` 判假；
- `lur_receiver_new_from_hidraw()` 的错误契约：负 fd 返回文档规定的 `-EINVAL`
  且**出参保持未被修改**（头文件明确 "otherwise unmodified"）；
- 同一函数对**合法但非 hidraw** 的描述符（`/dev/null`，`O_RDWR` 打开成功）
  同样返回 `-EINVAL` —— 证明 `HIDIOCGRAWINFO` 探测真的被执行了，而不是把 fd
  照单全收。

这三条覆盖了不插接收器时**唯一可达**的 API 面，同时把「错误的 fd 被当成接收器
接受」这种最危险的失败模式钉住。

### 5.6 运行期：json-glib 的 soname 载不进 OHOS（空 strerror）

编译全绿之后，CI 卡在 test_package 的 `test()`：

```
libratbag/0.18 (test package): RUN: /data/service/hnp/bin/bash -c 'export LD_LIBRARY_PATH="…"; "./test_lur"'
Error loading shared library libjson-glib-1.0.so.0: (needed by ./test_lur)
ERROR: libratbag/0.18 (test package): Error in test() method, line 86
	ConanException: Error 127 while executing
```

**判据是「冒号后为空」**：`Error loading shared library <name>: (needed by …)`
里 `strerror` 是空的，说明库**被找到了、却载不进去**——不是「找不到」
（那种会打印 `No such file or directory`）。json-glib 的 lib 目录明明就在
`LD_LIBRARY_PATH` 里（`libdirs` 日志第 4 项），且它的**库内符号齐全**。

根因在**已发布的 json-glib/1.10.6 二进制包**：`lib/libjson-glib-1.0.so.0`
是一条指向 `libjson-glib-1.0.so.0.1000.6` 的**符号链接**，而目标文件带着一段
**旧工具链产出的 `.codesign` 段**，当前 OHOS 运行环境不认这段签名，内核因此
拒绝映射它，musl 把它报成上面那行空 strerror。

（同一现象在仓内有两位先例：`archives/g/gxr/0.15.1` 的备注表第 10 行
「已发布的 `json-glib/1.10.6` 虽带旧 `.codesign`，从 Conan 缓存加载时签名不被
当前执行环境接受」；以及 `knowledge/drafts/DRAFT-trimmed-build-vs-full-build-
test-runnability.md` 里 gusb/0.4.9 的「库未装载」判定链。对照：eudev /
libevdev 的 soname 同样是符号链接却载得进——它们的 `.so` **完全没有**
`.codesign` 段，缺签名可以，签名失效不行。）

**做法**（`test_package/conanfile.py::_stage_json_glib_soname()`，形状照抄 gxr）：

1. `realpath()` 解开符号链接拿到真文件，并校验它没跑出 json-glib 包目录；
2. `shutil.copyfile()` 进 `test_package` 的构建目录（**Conan 缓存保持只读**，
   不就地改别人的包）→ `chmod 755`；
3. `llvm-objcopy --remove-section .codesign` 去掉旧签名 →
   `binary-sign-tool sign -inFile X -outFile X -selfSign 1` 重新自签；
4. 把该目录**前置**到 `test()` 构造的 `LD_LIBRARY_PATH` 最前面。

`liblur.so` 与 `test_lur` 的 DT_NEEDED 都是裸 soname `libjson-glib-1.0.so.0`，
前置目录后两者都命中新签的副本。其余依赖（glib 已由配方签名、eudev /
libevdev / libunistring 无签名段）无需处理——**只针对性物化载不进的这一个**，
而不是把全部 soname 都抄一遍。
