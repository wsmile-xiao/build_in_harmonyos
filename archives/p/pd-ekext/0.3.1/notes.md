# pd-ekext 0.3.1 适配笔记

## 这是什么

`ekext` 是 Ed Kelly 2005–2023 年间为 Pure Data 写的一组外部对象（externals），
面向音乐信息检索与复音控制：`bmt~`（beat mark tracker）、`ihisto`（包络直方图）、
`phasorbars~`（相位条）、`markovChains`（马尔可夫链）、`maskxor`、`mvcf~`、
`lcmgcd`、`list_sum`、`isoWrap~` 等，共 **43 个类**。

Pd 不静态链接外部对象：补丁里第一次出现 `[cup]` 时，Pd 用 `dlopen()` 打开
`lib/pd-externals/ekext/cup.pd_linux`，取出 setup 符号跑一遍完成类注册，
之后这个 `.pd_linux` 就常驻在 Pd 进程里。所以本包交付的是 **43 个共享对象**，
没有可执行文件、没有可链接库（见下）。

## 源码来源：为什么不用 GitHub tag 归档

上游仓库 `github.com/pd-externals/ekext` 把 `pd-lib-builder/` 放在 git
**submodule** 里，而 GitHub 的 tag 归档（`codeload.github.com/.../tar.gz/refs/tags/v0.3.1`）
从不包含 submodule 内容。该归档确实是 HTTP 200、5014398 字节、
sha256 `1cfc8dbd906f7b37a8d2c804629125247fcec102a582ba7caa84371e89324670`，
但解出来 `pd-lib-builder/` 是个空目录，构建第一行
`include $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder` 就断。

Debian 的 multimedia-team Pd 打包把那个 submodule 替换成了发布版 pd-lib-builder，
所以 `https://deb.debian.org/debian/pool/main/p/pd-ekext/pd-ekext_0.3.1.orig.tar.xz`
（HTTP 200，2695112 字节，sha256 `57abb9cb…cab833`）是这一版唯一自洽的 tarball，
符合 R39。两条独立佐证：

* tarball 顶层文件集与上游 tag 一致（43 个 `.c` + `Makefile` + 37 个 help/meta 补丁），
  而 `pd-lib-builder/Makefile.pdlibbuilder` 头部写着 `version = 0.7.0 / dated 2019-12-21`，
  即发布版而非本地魔改；
* 平台任务 #9369 自己记录的 `src = 57abb9cb…cb833` 就是这个 tarball 的 sha256 首尾。

## 源码改动

只有一个补丁 `patches/0001-fix-license-datafile-name.patch`：上游 `Makefile` 的
`datafiles` 列了 `LICENSE.txt`，而 tarball 里的文件叫 `LICENSE`。`pd-lib-builder`
的 `install-datafiles` 目标会逐个 `install -m 644 '<file>'`，于是
`make install` 在最后一个条目上以 `install: cannot stat 'LICENSE.txt'` 失败。
补丁把该条目改成 `LICENSE`。这是纯打包修复，不碰任何编译输入。

**零源码 C 改动**：43 个 `.c` 在 OHOS aarch64 clang 下原样编译通过（`-Wall -Wextra
-Wshadow -Winline -Wstrict-aliasing -O3 -ffast-math`，无 error）。

## 构建参数（为什么是这六个）

配方把六个 make 变量放在命令行上覆盖，一个补丁都不打：

| 变量 | 值 | 原因 |
|---|---|---|
| `system` | `Linux` | pd-lib-builder 用 `$(CC) -dumpmachine` 判平台。OHOS clang 报 `aarch64-unknown-linux-ohos`，其中的 `linux` 本来就会命中 Linux 分支（→ `pd_linux`、`-fPIC -shared -rdynamic`），显式写死是不让这个选择依赖构建主机 |
| `CC` | `tools.build:compiler_executables.c` | R33：不许依赖未定义的 shell `${CC}`；同时也让上面的 `-dumpmachine` 拿到 OHOS clang |
| `arch.c.flags=` | 清空 | pd-lib-builder 对 `target.arch=aarch64` 的猜测是 `-mcpu=cortex-a53`，上游自己注释着 “ARMv8 64 bit, not tested yet”。清空后由 OHOS clang 用自己的 aarch64 默认目标 |
| `PDINCLUDEDIR` | `<puredata 包>/include/pd` | pd-lib-builder 默认探测 `/usr/include/pd`；`m_pd.h` 在 puredata/0.54.1 包的 `include/pd/` 下 |
| `PDLIBDIR` | `/lib/pd-externals` | 安装根。**必须带前导斜杠**：pd-lib-builder 是字符串拼接 `installpath := $(DESTDIR)$(PDLIBDIR)/$(lib.name)`，不是路径 join |
| `DESTDIR` | `<package_folder>` | 产物落到 `<pkg>/lib/pd-externals/ekext/`，即 Pd 搜索额外库的默认位置（`pkglibdir = $(libdir)/pd-externals`） |

`make -j1`：43 次独立编译，每次一个类，串行让 CI 日志稳定可读（R9）。

## Pd 头文件为什么不走 requires 的 includedirs

`puredata/0.54.1` 是 **application** 包：它装了 `bin/pd`、数据目录和 API 头文件，
但 `package_info()` 里 `cpp_info.includedirs = []`（它不是库）。
所以配方在 `_pd_include_dir()` 里从依赖的 `package_folder` 解析 `include/pd`，
再在 `package_info()` 里把这个目录再导出一次。这样任何依赖 pd-ekext 的消费者
（包括 test_package）都能直接编 Pd 代码，而不必再手工 require puredata。
这条与 `pd-libdir` 的做法一致。

## 为什么每个对象都不导出 `setup`

Pd 的 `src/s_loader.c: sys_do_load_lib()` 会把类名 mangle 成 C 符号再找入口：

* 字母数字和 `_` 原样保留；
* **结尾的 `~` 变成 `_tilde`**；
* 其它字符 hex 成 `0x??`，此时整个名字改成 `setup_` 前缀而不是 `_setup` 后缀。

先 `dlsym(<mangled>_setup)`，找不到才退回 `dlsym("setup")`。
所以 `bmt~.pd_linux` 导出的是 `bmt_tilde_setup`，`isoWrap~.pd_linux` 导出的是
`isoWrap_tilde_setup`。`pd-lib-builder` 的 `lib.setup.sources`（能同时导出纯 `setup`）
在这套 Makefile 里没有定义——ekext 走的是「一个类一个共享对象」这条路。
test_package 里复刻了这段 mangle，这样断言验的才是 Pd 真会调的符号。

## 测试怎么做（以及为什么不用 pd 二进制）

`puredata/0.54.1` 的 `bin/pd` 在本机 OHOS 运行环境里直接报
`Error relocating .../bin/pd: __fd_chk: symbol not found`（musl 版本不匹配），
而且它还要一个跑起来的 Pd 事件循环。构建门禁不该依赖这两件事。

所以 test_package 内嵌一份**最小 Pd 运行时 shim**，只提供这 43 个对象
`nm -u` 实测 import 的 38 个 Pd 符号，然后按 Pd 的加载路径驱动它们：

1. **43 个对象逐个**：`dlopen(RTLD_NOW|RTLD_LOCAL)` → `dlsym(<mangled>_setup)` →
   调 setup() → 断言注册出的类名与对象名一致、实例大小非零、至少注册了一个方法。
   `RTLD_NOW` 证明每个对象 import 的 Pd 符号都能从加载方映像解析；
   `RTLD_LOCAL` 比 Pd 自己用的 `RTLD_GLOBAL` 更严——它证明对象不依赖别的外部对象
   导出的全局符号（43 个全部通过，说明 ekext 的每个对象自包含）。
   另外断言文件本身是 64-bit little-endian aarch64 `ET_DYN`。
2. **四个对象深驱动**：用 Pd 会调的创建函数把对象真正实例化（按 setup 报上来的
   实例大小分配），再驱动它们真实的方法，断言出口上的精确数值：
   * `[positive]`：float 3 → 3，float −5 → 1，float −1 → 1，float 2.5 → 2.5，bang 重复 2.5
   * `[cup]`：float 10 静默设计数；bang → 10，再 bang → 11；`setbang 5` → 5，下一个 bang → 6
   * `[doubledelta]`：float 10 → 二阶差分 10、差分 10；float 13 → 二阶差分 −7、差分 3；bang 重复
   * `[list_sum]`：`all 1 2 3 4` → 长度 4、总和 10；`all 10 20` → 长度 2、总和 30；
     `clear` 不出声，之后 `all 5 6` → 长度 2、总和 11（证明 clear 真把内部数组清了）
3. 打包内容：`ekext-meta.pd`、help 补丁、`README.txt`、BSD `LICENSE` 都在位。

合计 **269 条断言**，全部实跑，无 echo/print 占位。

写这个 shim 时踩到的三个 ABI 坑，都记在 `manifest.yaml` 的 `knowledge_gained` 里：
`class_addfloat` 是 `class_doaddfloat` 的宏、`t_floatarg` 是 `float` 不是 `double`、
以及上面那条入口符号 mangle。

## 编译告警（上游自带，未处理）

干净构建（`conan remove pd-ekext/0.3.1 -c` 后重跑）日志里 **0 error、88 行 warning**，
全部来自上游源码本身，不是本次适配引入的，也没有为了消掉它们去改上游代码：

* 30 处 `unused parameter 's'` / 12 处 `'f'` 等 —— Pd 消息回调固定签名里的未用参数；
* 16 处 `performing pointer subtraction with a null pointer` —— 来自
  `m_pd.h` 自己的 `CLASS_MAINSIGNALIN` 宏（`(char *)(&((type *)0)->field) - (char *)0`），
  是 Pd 头文件的写法，不是 ekext 的代码；
* 2 处 `phasorbars~.c:184/200 equality comparison result unused`（上游写了 `==` 而非 `=`）；
* `copyarray.c` 两个未使用的 static 函数、`logpost(NULL, 4, version)` 的
  `-Wformat-security`。

这些都不影响产物：`-Werror` 未开，`pd-lib-builder` 默认的 warn.flags 就是
`-Wall -Wextra -Wshadow -Winline -Wstrict-aliasing`，我们没有额外加严。

## 已知范围外的事

* `sound/HeadDown.wav` 没有被打包。上游 `Makefile` 没把它列进 `datafiles`，
  43 个 `.c` 里也没有任何一处引用它，所以没有功能缺口；如需随包分发要单独加
  `datadirs`，属于超出适配范围的改动。
* `ekext-meta.pd` 里 `VERSION` 写的是 `0.1.3`，`README.txt` 里写的是 `ekext 0.2.8`，
  而包版本是 0.3.1（上游 tag 就是这样）。没有改：这两个字符串只是 Pd 库标记里的
  展示文本，改了反而与上游 tarball 不一致。
* DSP 类（`~` 结尾）的 perform 没有被本测试驱动：那需要真正的 Pd DSP 图和
  signal vector。shim 里 `dsp_add()` 是空实现，`clock_*` 也不触发回调，
  避免在测试中间重入。