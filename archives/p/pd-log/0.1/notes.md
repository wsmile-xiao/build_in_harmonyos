# pd-log 0.1 适配笔记

## 编译环境

- 构建系统：Pd "Makefile template" 1.0.12（纯 make，无 autotools/cmake）
- 编译器：clang 15（OHOS aarch64-linux-ohos，musl）
- 平台：HarmonyOS PC（OHOS，arch=armv8）
- 依赖：puredata/0.54.1（提供 `m_pd.h` 等 Pd API 头文件 + 运行时）
- 补丁数：**0**
- 日期：2026-10-03

## 源码获取

上游官网 `download.puredata.info/log` 只发按平台打包的二进制 tarball
（`log-0.1-linux-aarch64.tar.gz` 等），**不发源码 tarball**。
因此取 Debian pool 里同一份上游 orig tarball：

```
https://deb.debian.org/debian/pool/main/p/pd-log/pd-log_0.1.orig.tar.gz
sha256 39fdba04176db9979f32ac04d36fac6e76ff15e7cc8d7cfa0cde13b853eefde2
```

tarball 根目录是 `log-0.1/`，配方用 `get(..., strip_root=True)` 拍平。

内容（14 个文件，`tar tzf` 共 15 条，其中 1 条是目录项 `log-0.1/`）：
`Makefile`、`README.txt`、`LICENSE.txt`、`log-meta.pd`、
5 个 C 源（`logpost.c` `debug.c` `normal.c` `error.c` `fatal.c`）、
5 个 help patch。

## 编译步骤

```bash
PD_PREFIX=<puredata 包目录>
CC=<OHOS clang>

# 1) 编译 5 个 externals（.pd_linux）
make -j1 CC="$CC" PD_PATH="$PD_PREFIX" STRIP=:

# 2) 安装到包目录（objectsdir 由模板自动追加库名 → lib/pd-externals/log）
make install DESTDIR=<package_folder> CC="$CC" \
     PD_PATH="$PD_PREFIX" objectsdir=/lib/pd-externals STRIP=:
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 找不到 `m_pd.h` | 模板把 `PD_PATH` 硬编码成 `/usr`（Linux 分支里 `PD_PATH = /usr`） | make 命令行传 `PD_PATH=<puredata 包目录>`；GNU make 里命令行变量覆盖 makefile 赋值，派生出的 `PD_INCLUDE = $(PD_PATH)/include/pd` 自动跟着变 |
| 2 | 模板只按 `uname -s` 分支，不列 OHOS | `UNAME := $(shell uname -s)` 只分 Darwin/Android/Linux/GNU/CYGWIN/MINGW | 取 Linux 分支（`.pd_linux` 正是 Pd 在 OHOS 上加载 externals 用的后缀），不设 `PLATFORM`、不引入任何平台宏。**但必须显式传 `UNAME=Linux`**——鸿蒙内核向 `uname -s` 报的是自己的内核名，该分支不会自动命中，见问题 #6 |
| 3 | `install` 阶段的 `strip` 会破坏 OHOS ELF | 模板 install 规则跑 `$(STRIP) --strip-unneeded`；OHOS clang wrapper 写入的 ELF code signature 经 strip 后失效 | 传 `STRIP=:` 短路掉 strip（abduco / jamnntpd / tty-clock 同一处置）。strip 只是体积优化，不影响功能 |
| 4 | `objectsdir` 多了一层 `log/log` | 模板 install 规则自己会拼 `$(objectsdir)/$(LIBRARY_NAME)` | 传 `objectsdir=/lib/pd-externals`，让它自己补 `/log`；与 pd-creb 0.10.0 的 `PDLIBDIR=/lib/pd-externals` 同构 |
| 5 | `CC` 可能静默回落到宿主 gcc | make 的内置默认 `CC = cc`；R33 禁止依赖未定义 shell 变量 | 从 `tools.build:compiler_executables` conf 取 C 驱动，先 `os.path.isfile` + `X_OK` 校验再回退 PATH 发现，最后显式作为 make 命令行变量传下去 |
| 6 | **真机 CI 链接失败：`undefined symbol: main / class_new / gensym / logpost …`（构建 #70269 / #70276）** | 模板把 `EXTENSION` / `-fPIC` / `-shared` / `-Wl,-soname` / rpath 全放在 `ifeq ($(UNAME),Linux)` 分支里，而 `UNAME := $(shell uname -s)`；鸿蒙内核向 `uname -s` 报的是自己的内核名（非 `Linux`），于是该分支整体被跳过，`EXTENSION` 留空 → 目标变成 `logpost.`，`ALL_LDFLAGS` 里没有 `-shared`，于是把 `logpost.o` 当可执行文件链接，`main` 和全部 Pd 符号一起报 undefined  | make 命令行传 `UNAME=Linux`。命令行变量覆盖 makefile 赋值（含 `:=`），分支被确定性选中。**该分支对 OHOS 本来就是对的**：OHOS 的 `pd` 二进制字符串表里有 `.pd_linux`，且 puredata 包自身就带 `lib/pd/extra/*/*.pd_linux`。
| 7 | **真机 CI test_package 阶段 dlopen 失败：`Error relocating logpost.pd_linux: gensym: symbol not found`，5 个 externals 全部同样报错（构建 #73602）** | 编译/链接/打包全对，挂在测试程序身上：externals 的 17 个 Pd API 函数（`gensym`/`class_new`/`logpost`…）走 `R_AARCH64_JUMP_SLOT`，数据符号 `s_` 走 `R_AARCH64_GLOB_DAT`，正常应由 **Pd 宿主进程**在 dlopen 时提供。**OHOS musl 加载器没有惰性绑定**——`RTLD_LAZY` 不推迟任何重定位，全部在 `dlopen()` 时刻立即解析；测试二进制若不导出这些符号，加载必然失败（glibc 才会推迟 PLT 槽位，所以本地 WSL 跑同一测试是绿的，掩盖了差异） | 测试二进制扮演 Pd 宿主：`pdlog_dlopen_test.c` 定义 externals 导入的全部 18 个符号（17 函数 + `s_`），编译命令加 `-rdynamic` 把它们发布进进程全局符号表——与 `pd` 本尊链接方式一致（pd 就是用 `-rdynamic` 导出 API 的）。同时 `dlopen` 改用 `RTLD_NOW`：本地 glibc 路径从此与真机 musl 同样做全量解析，不再因惰性绑定而「假绿」 |


### 真机失败的本地复现（重要）

问题 #6 在 WSL 上默认**复现不出来**（WSL 的 `uname -s` 就是 `Linux`），
必须显式模拟鸿蒙内核名才能看到同样的报错：

```bash
# 复现失败（与 CI 签名逐字一致：Makefile:252: logpost. Error 1 + undefined symbol 串）
make -j1 UNAME=HarmonyOS PD_PATH=<puredata 包目录> STRIP=:

# 验证修复
make -j1 UNAME=Linux    PD_PATH=<puredata 包目录> STRIP=:   # 5 个 .pd_linux 全部产出
```

这也说明「本地 `uname -s` 恰好是 Linux」会掩盖 recipe 的真实缺陷——
凡是靠 `uname`/`config.guess` 分支适配的项目，都要在本机显式模拟一次目标内核名。

## 编译警告（不影响产物，均为上游代码问题）

- `-O6` 不被 clang 支持，自动降级为 `-O3`
- `normal.c` / `error.c` / `fatal.c` / `debug.c`：`%lx` 与 `t_gpointer *` 类型不匹配（`-Wformat`）
- 4 个 `*_new()` 的 `t_symbol *s` 形参未使用（`-Wunused-parameter`）

以上都是上游既有写法，**没有为此打补丁**：改动它们只会偏离上游，而
`logpost(3)` 是 Pd 运行时 API，签名由 Pd 头文件保证。

## 关键平台事实：externals 靠 dlopen 绑定 Pd，不链接 libpd

`readelf --dyn-syms` / `readelf -r` 显示，每个 external 除唯一导出
`<name>_setup` 外，还导入 **17 个 Pd API 函数 + 1 个数据符号 `s_`**
（`logpost` 只是其中之一，早期笔记只列它是不完整的）：

```
logpost.pd_linux  .dynsym:  logpost_setup (GLOBAL DEFAULT, defined)
                            17 × GLOBAL UND 函数（atom_getfloatarg … resizebytes）
                            s_ (GLOBAL UND)                ← t_symbol 对象，取地址作默认 tag
logpost.pd_linux  .rela.dyn:  R_AARCH64_GLOB_DAT  s_        ← 数据重定位，任何 libc 加载期必解析
logpost.pd_linux  .rela.plt:  21 × R_AARCH64_JUMP_SLOT     ← 其中 17 个强绑定的 Pd 函数
readelf -d:        NEEDED libc.so（唯一依赖，没有 libpd）；RUNPATH $ORIGIN
```

`logpost(3)` 由 Pd 进程在运行时提供（puredata 0.54.1 的 `m_pd.h:579`
声明 `EXTERN void logpost(const void *object, int level, const char *fmt, ...)`），
因此：

- 链接期不需要 `-lpd`，`.pd_linux` 只有 `NEEDED libc.so` 一个依赖；
- **测试不能假设 `RTLD_LAZY` 会兜底**。glibc 确实会推迟 PLT 槽位解析，
  但 **OHOS musl 加载器没有惰性绑定**：`dlopen(RTLD_LAZY)` 与
  `dlopen(RTLD_NOW)` 一样在加载时刻全量解析，缺一个宿主符号就报
  `Error relocating <lib>: <sym>: symbol not found`（真机构建 #73602
  实测，之前「RTLD_LAZY 是预期行为」的结论只在 glibc 上成立）。
  因此测试二进制必须像 `pd` 本尊一样（pd 用 `-rdynamic` 链接）导出
  这 18 个符号，并用 `RTLD_NOW` 让本地 glibc 路径做与真机相同的全量解析。

RUNPATH 是字面量 `$ORIGIN`（模板用 `\$$ORIGIN` 转义），符合 Pd externals 的
加载约定。

## 交付物

```
lib/pd-externals/log/
├── logpost.pd_linux   debug.pd_linux   normal.pd_linux
├── error.pd_linux     fatal.pd_linux
├── log-meta.pd        （声明 VERSION 0.1）
├── {logpost,debug,normal,error,fatal}-help.pd
├── README.txt
└── LICENSE.txt
licenses/LICENSE.txt
```

`package_info()` 刻意不声明 `libs`/`libdirs`/`includedirs`：Pd externals 是运行时
插件，没有可链接的库；消费者用 `pd -path <pd-log 前缀>/lib/pd-externals`
把本包目录交给 Pd 即可。

## 上游测试清点

上游 0.1 **没有任何自动化测试**：`UNITTESTS` 为空、无 `check` 目标、tarball 里
的 `.pd` 只有 meta 与 5 个 help patch（逐项核对 tarball 文件清单，见
`test_package/MANIFEST.yml` 的 `upstream_zero_evidence`）。Debian 的
`debian/rules` 用 `dh $@ --buildsystem=pd_lib_builder`，同样没注册测试。

因此补全的集成测试分两层，共 33 条断言：

1. `test_package/test.sh`（18 条）：5 个 externals、5 个 help patches、
   `log-meta.pd`（并断言其 `VERSION 0.1`）、`README.txt`、两处 `LICENSE.txt`
   都落在 `lib/pd-externals/log`；原生测试程序已编译。
2. `test_package/pdlog_dlopen_test.c`（15 条）：为 aarch64 OHOS 目标编译，
   **在目标上运行**，对每个对象校验 ELF64 + `e_machine == EM_AARCH64(183)`，
   再 `dlopen(RTLD_NOW)` 并 `dlsym("<name>_setup")`。测试二进制自身以
   `-rdynamic` 链接并定义 externals 导入的全部 18 个 Pd 符号（桩宿主，
   与 `pd` 本尊的链接契约一致），因此 OHOS musl 的急切重定位也能全部解析。

第 2 层就是鸿蒙特有测试：宿主 x86_64 产物、缺架构的产物、或者用文本占位的
空壳包都会在这里红。

### 已知覆盖缺口（不掩盖）

dlopen 测试只解析 `<name>_setup` 就 `dlclose`，**没有真正调用** setup，因此没有
验证 `[logpost]` 的实际打印行为。仓库里的 `pd-maxlib/1.6.0` 做到了那一步——它用
puredata 包里的真实 `pd` 二进制跑一个 `.pd` patch 并断言输出。本包没有采用，原因是
**在本机无法复现、无法验证**：WSL 的 qemu binfmt 用的是 glibc 的 aarch64 loader，而
OHOS 的 `pd` 链接的是 musl（`INTERP = /lib/ld-musl-aarch64.so.1`，`NEEDED libc.so`），
在本机启动即报 `Error relocating .../bin/pd: __fd_chk: symbol not found`。已核实这不是
产物缺陷：OHOS sysroot 的 `libc.so` **确实导出 `__fd_chk`**，真机 loader 能满足该重定位。

即「真机上可跑」不等于「本地可验证」。按 W0b「历史命令在 CI 环境里逐字可执行吗」
的同一条纪律，不把无法在提交前复现的断言塞进 test_package，避免拿不可验证的覆盖度
去换 CI 稳定性。后续若要在真机侧补端到端用例，入口是
`pd -nogui -nosound -path <pd-log 前缀>/lib/pd-externals -open test.pd`。

## 注意事项

- externals 装在**本包自己的** `<pd-log 前缀>/lib/pd-externals/log/` 下，
  Pd 靠 `-path` 参数找到它们（与 pd-maxlib 1.6.0 的用法一致）：
  `pd -path <pd-log 前缀>/lib/pd-externals`，然后 `[logpost]`/`[fatal]` 等
  对象即可用。它们**不会**自动落到 puredata 包的 `lib/pd-externals/` 下。
  所以包内路径必须是 `lib/pd-externals/log/`，不能改成 `lib/`。
- `LICENSE.txt` 被模板安装到 externals 目录（Pd 需要），配方额外在
  `licenses/` 放一份，符合 Conan 惯例。
- 本包没有可执行文件（Pd externals 是 dlopen 插件），因此不需要
  `commands.json`（R38）。
