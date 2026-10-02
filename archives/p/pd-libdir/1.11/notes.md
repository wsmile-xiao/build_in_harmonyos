# pd-libdir 1.11 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 1. 这是什么软件

`pd-libdir` 是 Pure Data（Pd）的 **libdir 加载器库**。它不是一个可链接的库，
而是一个被 Pd 用 `dlopen()` 加载的共享对象 `libdir.pd_linux`：Pd 启动时调用它
导出的 `setup()`，它通过 `sys_register_loader()` 注册一个 loader。此后只要 Pd
在搜索路径里遇到形如 `<lib>/<lib>-meta.pd` 的目录，就把该目录登记为可导入的
Pd library。

- 上游源码只有 **1 个 C 文件** `libdir.c`（194 行）。
- 许可证：`BSD-3-Clause`（上游 `LICENSE.txt` 第 2 行 "Standard Improved BSD License"，
  且 `libdir-meta.pd` 声明 `#X text 10 70 LICENSE BSD;`）。
- 编译期只依赖 Pd 的三个头文件：`m_pd.h` / `s_stuff.h` / `g_canvas.h`。
- **不链接任何库**：Pd 自身的可执行文件以 `-rdynamic` 链接，插件里所有 Pd 符号
  都在 dlopen 时从 Pd 进程映像里解析。
- 源码没有独立 release，权威源是 Debian 官方源码池（见 conandata.yml，R39）。

### 关于 R39 / PF7 源 URL 例外（已按逃生口登记）

PF7 把 `deb.debian.org` 一律判为「Debian 下游重打包源」。本包**必须**用它，理由：

1. **pd-libdir 上游没有任何发布渠道**：该项目随 pd-extended 分发，早已无独立
   release/仓库（`pure-data/pd-lib-builder` 仓库只含模板，不含 libdir 本体）。
   `deb.debian.org/debian/pool/main/p/pd-libdir/pd-libdir_1.11.orig.tar.gz` 是这个
   版本的**权威原始出处**。
2. **它不是「下游重打包」产物**：`.orig.tar.gz` 是 Debian 约定存放的**未经改动的
   上游原始包**。实测该 tarball 顶层只有 `libdir-1.11/`（8 个文件），**不含
   `debian/` 目录**，也无 `+dfsg` 重命名（PF7 对 `+dfsg` 同样命中）。即包内容就是
   上游原样，不含 Debian 的 repack 改动。
3. 仓库内已有 **462** 个配方使用 `deb.debian.org` 作为源（PF7 只扫本 PR 变更文件，
   存量豁免）。

按 PF7 自带的逃生口处理：**在 PR 正文说明本例外 + `--no-preflight` 显式跳过**。

因此本包是**库形态**（`package_type = "library"`），无 `bin/`、无命令行入口，
详见第 5 节（为什么没有 commands.json）。

## 2. 上游测试清点（R51）

上游**没有任何测试**，证据（`tar tzf` 完整 8 个文件）：

```
libdir-1.11/LICENSE.txt        libdir-1.11/TODO.txt
libdir-1.11/Makefile           libdir-1.11/libdir-help.pd
libdir-1.11/Makefile.pdlibbuilder  libdir-1.11/libdir-meta.pd
libdir-1.11/README.txt         libdir-1.11/libdir.c
```

- 无 `tests/` / `test/` 目录，无任何断言代码。
- `Makefile` 与 `Makefile.pdlibbuilder`（pd-lib-builder 0.4.4）都**没有
  `check:` 目标**（`grep '^check'` 无匹配），所以 `make check` 不存在。
- 上游 CI（pd-lib-builder）同样不为该库跑测试。

结论：上游测试用例数 N = 0，无可移植用例；由本次适配新增鸿蒙特有测试
（见第 4 节，22 项断言）。

## 3. 构建：上游 Makefile 的命令行覆盖

上游 Makefile 是手写 Makefile + `Makefile.pdlibbuilder`（pd-lib-builder）。
**未打任何平台相关补丁**：`Makefile` 与 `libdir.c` 保持上游原样，只在 make 命令
行上覆盖 7 个变量（5 处必需 + 2 处可选），见下表。

> ⚠️ **`system=Linux` 是必需项，不是修饰。** 详见第 3.1 节——它来自 CI 首次红灯。

### 3.1 坑一：`uname` 不是 Linux 时整个平台分支被跳过（CI 首次红灯的根因）

pd-lib-builder 用 `uname` **全串精确匹配**判定平台（`Linux` / `GNU` / `GNU/kFreeBSD`
/ `Darwin` / `MSYS` / `MINGW`），**没有 OHOS 分支**。而 OHOS CI worker 的
`uname` 就是 **HarmonyOS**，于是：

- `Makefile.pdlibbuilder:469` 的 `ifeq` 全部不命中 → `system` 为空；
- 依赖 `ifeq ($(system), Linux)` 的 `extension = pd_linux` / `-fPIC` / `-shared` /
  `-rdynamic` / `-lc -lm` **一个都没设**；
- 结果产物名退化成 `libdir.`（空扩展名），链接命令也没有 `-shared`，CI 报：
  ```
  ++++ info: linking objects in libdir. for lib libdir
  ld.lld: error: undefined symbol: main
  ld.lld: error: undefined symbol: sys_getversion      ← 以及其余 14 个 Pd 符号
  clang-15: error: linker command failed with exit code 1
  ```

**这个坑在本地完全复现不出来**：WSL2 开发机的 `uname` 就是 `Linux`，会自动走 Linux
分支，一切正常。只有真机 worker 才暴露——即 W0b 说的「环境语义不可迁移」。

修复：make 命令行加 `system=Linux`（命令行变量优先级高于 Makefile 里的 `:=` 赋值）。
实测（伪造 `uname` 返回 HarmonyOS）修复前后对比：

```
修复前: linking objects in libdir.          clang  -Wl,-soname,...  -o libdir.  libdir.o
修复后: linking objects in libdir.pd_linux  clang -rdynamic -shared -fPIC ...  -o libdir.pd_linux libdir.o -lc -lm
```

### 3.2 覆盖清单

| 覆盖项 | 为什么 | 证据 |
|---|---|---|
| `system=Linux` | **必需**。CI worker 的 `uname` 是 HarmonyOS，pd-lib-builder 无该分支 → `extension` 为空、丢 `-shared`，链接报 `undefined symbol: main`（见 3.1） | `Makefile.pdlibbuilder:469` `ifeq ($(findstring $(uname), Linux GNU GNU/kFreeBSD), $(uname))` |
| `CC="<OHOS clang>"` | R33：编译器只能来自 Conan profile 的 `tools.build:compiler_executables`，绝不用裸 `${CC}`；pd-lib-builder 默认是 `gcc` | `Makefile.pdlibbuilder:580` `CC = gcc` |
| `arch.c.flags=`（清空） | pd-lib-builder 用 `uname -m` 推导架构 flag。若构建机是 x86_64 → 注入 `-march=core2 -mfpmath=sse -msse -msse2 -msse3`，**aarch64 OHOS clang 直接报错**。OHOS worker 是 aarch64 故不命中，但换 x86 构建机就会踩 | `Makefile.pdlibbuilder:438` `machine := $(shell uname -m)`；`:457` `arch.c.flags = -march=core2 -mfpmath=sse -msse -msse2 -msse3` |
| `PDINCLUDEDIR="<puredata pkg>/include/pd"` | 默认探测 `/usr/include/pd`（worker 上不存在）。Pd 头文件来自本仓 `puredata/0.54.1` 制品 | `Makefile.pdlibbuilder:607` `PDINCLUDEDIR ?= $(pdincludepath)` |
| `PDLIBDIR=/lib` + `DESTDIR=<pkg>` | 安装路径 = `$(DESTDIR)$(PDLIBDIR)/$(lib.name)` = `lib/libdir/`，与 Pd 查找 externals 的目录一致。注意 `PDLIBDIR` 是**直接字符串拼接**（无 `/` 时会拼成 `/tmp/outlib`），必须写成 `/lib` | `Makefile.pdlibbuilder:617` `installpath := $(DESTDIR)$(PDLIBDIR)/$(lib.name)` |

另有 2 个非必需但正确的设置：`lib.version=1.11`（让 `-DVERSION='"1.11"'` 进
二进制，`setup()` 会打印它）和 `LDFLAGS="-Wl,-soname,libdir.pd_linux"`（补 DT_SONAME）。

### 3.3 为什么不需要 patch 改平台宏

因为 `system=Linux` 已在命令行接管平台判定，`Makefile` 与 `libdir.c` 一行都不用改，
`__OHOS__` 这类宏在本包中完全没出现。

### 3.4 唯一补丁：把 `libdir-help.pd` 装进包

上游 tarball 里有 `libdir-help.pd`，但 Makefile 的 `datafiles` 没列它，
`make install` 会漏装。而 `libdir-meta.pd`（本库存在的意义）恰恰是让 Pd 的
Help Browser 收录这个 library 的标记文件，help patch 却不在包里，装出来的
library 不自洽。补丁 `0001-ship-help-patch.patch` 只往 `datafiles` 加一行，
**不含平台宏、不改源码**。

## 4. 依赖与头文件（W0 + 一个真实坑）

### 4.1 W0 依赖发布检查

```bash
conan download "puredata/0.54.1" -r=ohpcd --only-recipe   # → 存在
conan install --requires=puredata/0.54.1 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=never
# → Package installed（OHOS aarch64 预编译 binary 已发布，无需源码构建）
```

`pd-libdir` 的唯一依赖就是 `puredata`，已发布，无 `dependency_missing`。

### 4.2 坑：`puredata` 是 application，导不出头文件路径

`puredata/0.54.1` 的 `package_info()` 里写着
`self.cpp_info.includedirs = []` / `libdirs = []`（它是 CLI 应用，不是库）。
所以光 `self.requires("puredata/0.54.1")` **拿不到 `-I<...>/include/pd`**，
必须自己从依赖的 package folder 里解析。

配方做法（`_pd_include_dir()`）：在 `<puredata pkg>/include/pd` 与
`<puredata pkg>/include` 里探测 `m_pd.h` 是否存在，取第一个命中的；找不到就
抛 `ConanInvalidConfiguration`（而不是让 clang 报一个难懂的错）。

顺带说明为什么**没有**改 `puredata` 的配方去补 `includedirs`：那属于另一个
软件，按 W2/JC6「一个 PR 只含一个软件」必须单独提 PR。

### 4.3 为什么 `package_info()` 把 Pd 头文件路径转出

`package_info()` 里：

```python
self.cpp_info.includedirs = [self._pd_include_dir()]   # 绝对路径
self.cpp_info.defines = ["PD"]
self.cpp_info.libs = []
self.cpp_info.libdirs = ["lib", "lib/libdir"]
```

- `defines = ["PD"]`：与 `puredata` 自带 `pd.pc` 的 `Cflags: -DPD` 保持一致。
- `includedirs` 是**依赖包目录里的绝对路径**：因为依赖自己声明不导出 include 路径。
  仓库内同类先例：`archives/c/cloog/0.21.1/conanfile.py` 用同样方式转出 GMP 头文件。
- `libs = []`：产物是 Pd 用 `dlopen()` 加载的插件，没有可链接的库。
  `cpp_info.libdirs` 同时给出 `lib` 和 `lib/libdir`，方便消费方按名字取到插件。

## 5. 为什么没有 commands.json（R38 判定）

R38 要求「产物含可执行文件」时提供软件级 `commands.json`。本包的产物是
`libdir/libdir.pd_linux`：ELF `ET_DYN` 共享对象，**没有 `main()`**，不能作为
命令调用；唯一的使用方式是 `pd -lib libdir`（`pd` 属于 `puredata` 包，那里
已经声明了 commands.json）。给它伪造一个不存在的命令会让 hicmd 元数据失真，
所以按「库类型不需要」处理：`package_type = "library"`、`bindirs = []`、
无 `bin/` 安装，CI L0k 判定为 library 包（不需要 commands.json）。

## 6. 测试：22 项断言，驱动真实插件代码

上游无测试可移植，本次新增鸿蒙特有消费者测试
`test_package/pd_libdir_test.c`（22 项断言，`assertion_count=22`）。

关键点：**Pd 的 API 没有可链接的库**，`puredata` 包里也没有 `libpd.so`
（Pd 是可执行文件，靠 `-rdynamic` 导出符号）。因此测试用与 Pd 完全相同的方式
驱动插件——自己提供被导入的 Pd 符号：

1. 从 `readelf --dyn-syms libdir.pd_linux` 读出插件共 **16 个 GLOBAL UND**：其中
   **15 个是 Pd 符号**（下面列出的）+ 1 个 libc 的 `snprintf`。shim 只需提供那 15 个 Pd 符号：
   `sys_getversion` `sys_register_loader` `logpost` `gensym` `class_new`
   `pd_new` `pd_typedmess` `namelist_append` `sys_isabsolutepath`
   `sys_trytoopenone` `sys_close` `sys_searchpath` + `canvas_open`
   `open_via_path` `canvas_getenv`（后三个属旧版/画布路径，必须不被调用）。
2. 消费者程序用 `-rdynamic` 编译（导出自己的动态符号表），`dlopen(RTLD_NOW)`
   真实打包产物，调用其**真实代码**：`setup()` → 注册的 loader → meta 文件查找
   → `pd_typedmess("pd", "add-to-path", "+<dir>")`。
3. `canvas_open` / `open_via_path` / `canvas_getenv` 一旦被调用直接 `exit(1)`，
   顺带钉住插件的调用图。

写这个 shim 时踩到两个真实语义坑（都在测试代码里按 Pd 真实行为修正）：

- **`gensym` 必须做驻留（intern）**。Pd 每个不同的名字返回一个固定的
  `t_symbol`；插件先把 `gensym("+<dir>")` 存进 atom，**之后**才求值
  `gensym("pd")` / `gensym("add-to-path")`。若 shim 复用同一个槽位，会把已存的
  atom 覆盖掉，测试就会读到错误的 selector。第一次跑就是这里挂了。
- **`sys_trytoopenone` 的 `dirresult` 是「找到的文件的目录」，不是传入的搜索
  条目**。对照 Pd `src/s_path.c:265` 的真实实现：先把 `dir + "/" + name + ext`
  拼进 `dirresult`，成功后在最后一个 `/` 处截断，`*nameresult` 指向 basename。
  这一步很关键——libdir 把 `dirresult`（而不是它拿到的搜索目录）登记进 Pd 全局
  路径；shim 若原样回显 `dir`，插件就会登记错目录。

测试覆盖面（22 项）：打包数据文件齐备（5）→ dlopen/dlsym（3）→ `setup()`
注册 loader 与版本横幅（4）→ 真实 meta 文件查找 + `add-to-path` 编码（5）→
缺 meta 文件被拒且不污染全局路径（2）→ 相对路径被 `sys_isabsolutepath()` 拦掉（2）
+ fixture 创建（1）。

## 7. 环境与验证

- 交叉工具链：OHOS clang 15，target aarch64-linux-ohos，profile
  `ohos-aarch64-wsl`（host/build 同 profile，与 CI 一致）。
- W3：`conan create archives/p/pd-libdir/1.11 --name=pd-libdir --version=1.11
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing` → 成功，
  test_package **22/22 checks passed**。
- 产物：
  ```
  lib/libdir/libdir.pd_linux     ELF 64-bit aarch64, DT_SONAME=libdir.pd_linux
  lib/libdir/libdir-meta.pd       library marker（Pd 识别入口）
  lib/libdir/libdir-help.pd       help patch（补丁新增）
  lib/libdir/README.txt  lib/libdir/TODO.txt  licenses/LICENSE.txt
  ```
- 运行期依赖：仅 libc（`-lc -lm`），无 `DT_NEEDED` 指向第三方库。

## 8. 遗留 / 后续建议

- 本地曾尝试用 `puredata` 包里的 `bin/pd` 真实加载插件做端到端验证，但该
  `pd` 二进制在当前环境报 `__fd_chk: symbol not found`（`pd` 所链接的 OHOS
  musl 与本机 `/opt/ohos-guest` 的 musl 版本不匹配），属于**环境侧**限制，
  与本包产物无关。故改用「消费者程序 + 最小 Pd 运行时 shim」驱动真实插件代码，
  这也是 CI 上可稳定复现的路径。
- 若后续要真正端到端跑 `pd -lib libdir`，建议先补一个
  「puredata 制品在干净 OHOS 运行环境可直接启动」的验证包，再在那个环境里跑。
- `libdir-help.pd` 之外，`TODO.txt` 仍随包安装（上游 datafiles 行为，未改）。
---

**编译结束**: 2026-10-01 15:56
**最终状态**: built
