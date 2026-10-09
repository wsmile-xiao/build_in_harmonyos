# draft-pd-syslog-0.1-pdlibtemplate-uname-strip-cross

> Status: **Draft**（待审核 promote）| severity: `3` | category: `build|cross-compile` | Updated: 2026-10-04
> 对应: `knowledge/drafts/DRAFT-pd-syslog-0.1-pdlibtemplate-uname-strip-cross.kv`

---

**匹配关键词**：pd library template, MakefileTemplate, UNAME, uname -s, HarmonyOS, EXTENSION, pd_linux, PD_INCLUDE, PD_PATH, STRIP, strip --strip-unneeded, Unable to recognise the format, objectsdir, pd-externals, syslog.pd_linux, m_pd.h

## 症状

`pd-syslog/0.1` 用上游自带的 Pd library template Makefile（模板版本 1.0.14）构建。它在 **link 阶段**和 **install 阶段**各有一处「构建机 == 目标机」的硬假设，交叉编译到 OHOS aarch64 时同时失效：

① link 阶段（平台分支未命中，链接退化）

```text
<OHOS clang> -o "syslog." "syslog.o"
ld.lld: error: undefined symbol: main
ld.lld: error: undefined symbol: gensym
ld.lld: error: undefined symbol: class_new
... （9 个 Pd 符号 + libc 的 openlog/syslog/closelog）
```

注意产物名是 `syslog.`（`EXTENSION` 为空）且链接行**没有** `-shared`。

② install 阶段（宿主 strip 读不了目标架构 ELF）

```text
<OHOS clang> -rdynamic -shared -fPIC -o "syslog.pd_linux" "syslog.o"
install -p -m 755 -d <pkg>/lib/pd-externals/syslog
strip --strip-unneeded -R .note -R .comment <pkg>/lib/pd-externals/syslog/syslog.pd_linux
strip: Unable to recognise the format of the input file `<pkg>/lib/pd-externals/syslog/syslog.pd_linux'
make: *** [Makefile:...: libdir_install] Error 1
```

②的致命之处：**所有产物此时已经就位**，报错发生在最后一步，很容易被误判成「编过了、只是 install 有问题」。

## 根因

① 模板用 `UNAME := $(shell uname -s)` 拿平台，再按**全串**匹配一串 `ifeq ($(UNAME),<平台>)`（`Linux` / `Darwin` / `Android` / `CYGWIN` / `MINGW` / `GNU` / `GNU/kFreeBSD`），**没有 OHOS / HarmonyOS 分支**。HarmonyOS 不命中任何分支，于是同一块里赋值的所有东西全丢：

| 变量 | Linux 块里的值 | 缺失后果 |
|---|---|---|
| `EXTENSION` | `pd_linux` | 目标名退化成 `syslog.`，Pd 找不到该插件 |
| `PD_PATH` | `/usr` | `PD_INCLUDE = $(PD_PATH)/include/pd` 变成 `/include/pd` |
| `OPT_CFLAGS` | `-O6 -funroll-loops …` | 无优化 |
| `ALL_CFLAGS += -fPIC` | `-fPIC` | 位置无关代码缺失 |
| `ALL_LDFLAGS += -rdynamic -shared -fPIC …` | 同左 | **按可执行文件链接** ⇒ `undefined symbol: main` |
| `ALL_LIBS += -lc` | `-lc` | 未显式链 libc |

② 模板在 `libdir_install` 末尾无条件执行 `$(STRIP)`，而 `STRIP = strip --strip-unneeded -R .note -R .comment` 用的是**宿主 binutils 的 strip**。交叉编译产物是 aarch64 ELF，宿主 strip 是否能读取决于发行版 binutils 的 BFD target 配置，**不能假设**（本机 Ubuntu binutils 就不能）。

## 处置

**不打任何平台补丁**——make 命令行变量赋值优先级高于文件内任何 `=`（含 `:=`），六个覆盖项足够：

```bash
make all UNAME=Linux \
         CC="<profile 的 tools.build:compiler_executables.c>" \
         PD_INCLUDE="<puredata 包>/include/pd" \
         prefix="<package_folder>" \
         LDFLAGS="-Wl,-soname,syslog.pd_linux -Wl,-s" \
         STRIP=: -j1
make install <同一组变量>
```

| 覆盖项 | 为什么必需 / 要点 |
|---|---|
| `UNAME=Linux` | 命中 Linux 块，才有 `EXTENSION=pd_linux`、`-fPIC -shared -rdynamic`、`-lc`。**无条件传**，不要靠 `uname` 判断 |
| `CC` | 取 profile 的 `tools.build:compiler_executables.c`（R33），不用裸 `${CC}`；模板默认是 `gcc` |
| `PD_INCLUDE` | 直接覆盖，**而不是** `PD_PATH`。模板 `ALL_CFLAGS = -I"$(PD_INCLUDE)"`，而 `PD_INCLUDE` 默认由 `PD_PATH=/usr` 推导，只对系统级 Pd 安装成立。直接给 `PD_INCLUDE` 可免去反推依赖包布局（依赖包可能把头文件放 `include/pd` 或 `include`） |
| `prefix=<package_folder>` | R49 私有 prefix。模板 `libdir = $(prefix)/lib`、`objectsdir = $(pkglibdir)` ⇒ 落 `lib/pd-externals/syslog/`，正好是上游默认布局（`/usr/local/lib/pd-externals/syslog`）也是 Pd 找 extra library 的位置。**用 prefix 而不是 DESTDIR**：install 目标是 `$(DESTDIR)$(objectsdir)/$(LIBRARY_NAME)`，两者同时给会重复拼路径 |
| `LDFLAGS=-Wl,-soname,…` | 上游链接行无 DT_SONAME，本地 SONAME 质量门禁 L5a 判红 |
| `LDFLAGS` 里的 `-Wl,-s` | 顶替 ② 的 strip：**链接期**用同一个 clang 剥，WSL 与 CI worker 行为一致（实测产物 `stripped`，6.4 KB，`.dynsym` 仍保留 `syslog_setup`） |
| `STRIP=:` | 禁掉 install 阶段的宿主 strip |

## 预防

- **凡是「按 `uname -s` 全串选平台」的构建脚本，交叉编译到 OHOS 前一律先查有没有 OHOS 分支**，没有就用命令行变量强制走目标平台分支。已中招的先例：pd-libdir/1.11 的 `Makefile.pdlibbuilder`（`system=Linux`，MR #14157 / CI #66208）。
- ⚠️ **这类分支失败在 WSL2 上不可复现**：WSL2 的 `uname -s` 就是 `Linux`，会自动命中 Linux 块，所以本地 `conan create` 全绿**不能证明** worker 上也是绿的。要本地复现需在 `PATH` 前置一个返回 `HarmonyOS` 的假 `uname` 脚本。
- **凡是构建脚本在 install/post-install 阶段调用宿主 `strip`/`objcopy`/`nm` 的，交叉编译时都要覆盖掉**，改由链接期 `-Wl,-s` 或工具链自带的 `llvm-strip` 完成；不要硬编码本地 SDK 路径（CI worker 上不存在该路径）。
- 宿主工具能否处理目标架构，别假设：`file` 一下目标产物，再实际跑一次宿主 `strip` 验证。
- `make install` 报错时先确认失败发生在哪一步——产物已就位而最后一步失败，很容易被当成编译问题去改代码。
