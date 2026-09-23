# debfoster 2.8 — OHOS 适配笔记

> 设备：HarmonyOS PC (aarch64)，clang 15.0.4，Conan 2.29.1，GNU Make 4.4.1
> 状态：见 `manifest.yaml` 的 `status` 字段

## 1. 源码与构建系统

- 源码：`debfoster_2.8.orig.tar.xz`（142780 B，
  sha256 `c5d044a89642603987e216d406d8f9aa74c60240be4b4992f45bd9b743a9a522`），
  取自 Debian 归档 `pool/main/d/debfoster/`，与 `debfoster_2.8-1.dsc` 里
  `Checksums-Sha256` 声明的值逐字符一致。
- 上游仓库是 `https://salsa.debian.org/debian/debfoster`（DSA 维护），
  2.8 由 Marc Haber 于 2024-11-18 上传，changelog 记「overhaul autotools build
  system」——正是这次 overhaul 引入了下文第 2 节的发行包缺陷。
- 构建系统：autotools（`configure` + 递归 `make`），四个子目录
  `src/ etc/ doc/ po/`，产物是单个可执行文件 `debfoster`（`sbin_PROGRAMS`）。
- 语言：10 个 `.c` + 10 个 `.h`，纯 C；`lang-preflight` 判 `detected=c`，
  与任务卡 `cpp` 同属 C/C++ 兼容族，继续主流程。

## 2. 发行 tarball 缺 autotools 辅助文件

`Makefile.am` 里有：

```make
dist-hook:
	rm -f $(distdir)/autom4te.cache
	rm -f $(distdir)/config.guess*
	rm -f $(distdir)/config.sub*
	rm -f $(distdir)/aclocal.m4
	rm -f $(distdir)/missing
	rm -f $(distdir)/install-sh
	rm -f $(distdir)/depcomp
```

`debfoster_2.8.orig.tar.xz` 是 `make dist` 产物，所以 tarball 里**有**生成好的
`configure`（283677 B）和各目录 `Makefile.in`，但**没有**上列六个文件。
Debian 侧靠 `dh_autoreconf` 重建；本设备与 CI worker 都没有 autotools 工具链，
而且 `configure.ac` 用了 `AX_CFLAGS_WARN_ALL`（来自 autoconf-archive，树里没有），
`AM_GNU_GETTEXT_VERSION([0.22.5])` 还需要 autopoint，重生成不可行。

实测两种失败形态（任务源码副本，`$HOME/tmp/debfoster-2.8/explore/`）：

```text
$ ./configure
configure: error: cannot find required auxiliary files: missing install-sh config.guess config.sub
```

补齐 `config.guess`/`config.sub`/`install-sh`/`missing` 后：

```text
$ ./configure && make -j1
CDPATH="${ZSH_VERSION+.}:" && cd . && /bin/sh '.../missing' aclocal-1.16 -I m4
.../missing[85]: aclocal-1.16: inaccessible or not found
WARNING: 'aclocal-1.16' is missing on your system.
make: *** [Makefile:375: aclocal.m4] Error 127
```

第二条是 automake 的 maintainer 规则被触发：`aclocal.m4` 不存在，而
`$(ACLOCAL_M4): $(am__aclocal_m4_deps)` 的依赖 `configure.ac` 与 `m4/*.m4`
在解压后比 `Makefile.in` 新，make 于是去跑 `$(ACLOCAL)`。

处置：

1. `generated/` 随配方交付六个文件（sha256 与来源见 `generated/PROVENANCE.md`），
   `source()` 逐个复制回源码树——不使用 `generated/*` 通配，因为同一目录里还有
   说明文件 `PROVENANCE.md`，复制进源码树没有意义。
2. `build()` 在 `apply_conandata_patches()` 之后把所有 autotools 输入与产物
   （`*.m4 *.am *.in *.ac`、`configure`、`config.guess`、`config.sub`、
   `install-sh`、`missing`、`depcomp`、`aclocal.m4`、`config.h.in`，任意深度）
   `os.utime` 到同一个时间戳 `978307200`（2001-01-01）。GNU make 认为 mtime
   相等即「已是最新」，maintainer 规则不再触发，随包发布的 `configure`
   及其补丁完整保留。同型做法见仓库内 `archives/b/boolstuff/0.1.16/conanfile.py`
   的 `_pin_autotools_timestamps()`。
3. `aclocal.m4` 只作为「让上述前置条件存在」的占位文件交付（内容与理由写在该
   文件头部）。补丁链时间戳被钉平后它不会被读取：`aclocal.m4` 只是 autoconf
   的输入，而 `configure` 是随包发布的现成产物，不会被重新生成。可用三处旁证：
   `make` 全程无 `aclocal`/`automake`/`autoconf` 调用行；构建日志里
   `checking build system type... aarch64-unknown-linux-ohos` 只有补丁后的
   `config.guess` 能给出；`configure` 内 `umask 022` 的补丁在
   `config.status` 中同样生效（若 configure 被重生成，补丁会丢失并立刻
   复现第 3 节的 Permission denied）。

## 3. `config.guess` 不认 HarmonyOS

设备 `uname -s` 返回 `HarmonyOS`，而 2024-07-27 版 `config.guess` 只处理
`Linux|GNU|GNU/*`：

```text
./config.guess: unable to guess system type
UNAME_SYSTEM  = "HarmonyOS"
config.guess timestamp = 2024-07-27
configure: error: cannot guess build type; you must specify one
```

`generated/config.guess` 在

```text
# Note: order is significant - the case branches are not exclusive.
```

之前插入与仓库其他包同型的 `*:HarmonyOS:*:*` 分支，直接输出
`${MACHINE}-unknown-linux-ohos`（不依赖 `$CC` 探测，`$dummy.c` 写不进
hmdfs 工作目录的场景也可用）。实测：

```text
$ sh ./config.guess
aarch64-unknown-linux-ohos
$ sh ./config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
```

2024-05-27 版 `config.sub` 已原生接受 `ohos` 这一 OS 组件，因此逐字节原样交付，
不做补丁。

配方不改写 `configure_args`：本仓库 CI 用同一份 profile 传给 `-pr:h` / `-pr:b`，
`cross_building()` 为 False，`AutotoolsToolchain` 不注入 `--build`/`--host`，
`configure` 自己调用上面打补丁的 `config.guess`；实测日志：

```text
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking target system type... aarch64-unknown-linux-ohos
```

## 4. `config.status` 的临时目录在 hmdfs 上不可写

`configure` 内嵌的 `config.status` 用

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` && test -d "$tmp"
```

建临时目录。hmdfs 会把 mode 里的 other 位规范化掉，落到磁盘是 `2700`：

```text
$ (umask 077 && mkdir d700); ls -ld d700
drwx--S--- 2 20001006 file_manager 3440 ... d700
$ echo x > d700/f
bash: d700/f: Permission denied
```

而进程的真实 uid 并不是目录属主（`id -u` = 20020084，目录属主 uid = 20001006），
所以随后的

```text
./config.status[783]: can't create ./confDpDWRo/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

直接让 `configure` 以 rc=1 结束。补丁 `0001-configure-umask-hmdfs.patch` 把
`umask 077` 改成 `umask 022`（`mktemp` 与 `mkdir` 回退分支各一处）。注意
`config.status` 是 `configure` 在运行时**内嵌生成**的，改包内的 `config.status`
没有意义——必须改 `configure` 自身；本包 `config.status` 也不在发行 tarball 内。
同型先例：`archives/a/adns/1.6.2/patches/0002-fix-config-status-hmdfs-umask.patch`、
`archives/a/alsa-lib/1.2.16.1/patches/0006-config-status-hmdfs-umask.patch`。

### 4.1 该补丁的安全折衷（显式留痕）

上游用 `umask 077` 的意图是让 `./confXXXXXX` 只对属主可读写（0700）。本补丁把它放宽到
`umask 022` 后，该临时目录在 hmdfs 上落盘为 **`drwxr-s--x`（2751）**：属主 `rwx`、
**同组 `file_manager` `r-x`（可遍历可读目录项）**、other 仅 `--x`（可遍历、**不可读**）。
目录内生成的 `subs1.awk` / `subs.awk` / `defines.awk` 落盘 **0660**（`-rw-rw----`），
即**同组用户可读且可写**。

> **取值条件必须连带声明（目录与文件两类 mode 由不同条件决定）**：**目录** mode 由创建该
> 目录时的 umask 决定；**文件** mode 由创建该文件时进程当时的 umask 决定，而补丁里的
> `umask 022` 写在 `( … )` 子 shell 内，**不改变**之后写 `subs1.awk` 的父 shell 的 umask。
> 真实构建的 ambient umask 是设备默认的 `0002`（同一 build folder 内由 configure/make
> 生成的文件亦全为 `0660`：`config.log`/`Makefile`/`src/*.o`），故这三个片段实测为
> `0660`。在**显式 `umask 022`** 下建文件才会得到 `0640`，那是另一次实验条件，
> **不是**本构建路径的取值，两者不可写进同一处。

真实产物捕获（`ac_tmp` 默认在 config.status 退出时被 trap 清理，用 `config.status --debug`
让其保留；该选项在 config.status 的选项表内，`configure --debug` 实测 rc=1
`unrecognized option: '--debug'`）：

```text
$ umask                                  # 真实构建的 ambient umask
0002
$ ./config.status --debug                # 在 configure 已运行过的 scratch 目录内重跑
rc=0
$ for f in conf??????; do case "$f" in config.*) continue;; esac
>   stat -c '%a %A %n' "$f" "$f"/subs1.awk "$f"/subs.awk "$f"/defines.awk; done
2751 drwxr-s--x conf6ZHlOo
660 -rw-rw---- conf6ZHlOo/subs1.awk
660 -rw-rw---- conf6ZHlOo/subs.awk
660 -rw-rw---- conf6ZHlOo/defines.awk
$ ls -d conf?????? | grep -v 'config\.'   # 另一目录走同一流程但不加 --debug
（无输出：退出 trap 已清理）
$ stat -c '%a %A %n' .../build-release/{config.log,Makefile,src/AVLTree.o}
660 -rw-rw---- .../build-release/config.log
660 -rw-rw---- .../build-release/Makefile
660 -rw-rw---- .../build-release/src/AVLTree.o
```

文件 mode 随 ambient umask 变化（同一目录内实测，用于说明上表只适用于目录）：

```text
$ for u in 077 022 002; do (umask $u; echo x > f_echo_$u); done
$ stat -c '%a %A %n' f_echo_077 f_echo_022 f_echo_002
600 -rw------- f_echo_077
640 -rw-r----- f_echo_022
660 -rw-rw---- f_echo_002
```

hmdfs 上的目录 mode 完全由创建时的 umask 决定（实测，`mkdir` 与 `mktemp -d` 结果相同）：

| umask | 目录 mode | 属主/组/other | 本进程可写 |
| --- | --- | --- | --- |
| `077`（上游） | `2700` `drwx--S---` | `rwx` / `---` / `---` | **否**（Permission denied） |
| `022`（本补丁） | `2751` `drwxr-s--x` | `rwx` / `r-x` / `--x` | 是 |
| `002`（设备默认） | `2771` `drwxrws--x` | `rwx` / `rws` / `--x` | 是 |

因此这是一次**有意的安全语义降级**：从「仅属主可读写」放宽为「属主读写 + 同组可读写」
（目录 `2751` 同组可读可遍历、其内片段 `0660` 同组可读可写），
为在 hmdfs 上取得构建可行性而接受。

**为什么不用「创建后 `chmod 700`」恢复 0700 语义**——实测该做法在本平台上**双向无效**：

```text
$ mkdir base2771; (umask 077; mkdir base2700)
$ for d in base2771 base2700; do
>   for m in 700 2771; do
>     echo "$d before=$(stat -c %a $d)"; chmod $m $d; echo "  chmod $m rc=$? after=$(stat -c %a $d)"
>   done; done
base2771 before=2771  chmod 700 rc=0 after=2771
base2771 before=2771  chmod 2771 rc=0 after=2771
base2700 before=2700  chmod 700 rc=0 after=2700
base2700 before=2700  chmod 2771 rc=0 after=2700
```

`chmod` 对目录**恒返回 0 且 mode 完全不变**（`700` 与 `2771` 两个方向都试过）。
所以「先建目录再 `chmod 700`」的正确结论是**完全不生效**：它恢复不了 0700 语义，
同时也**不会**重新引入本节开头的不可写问题——只是因为该调用什么也没做，构建可行性
仍然完全依赖补丁里 `umask 022` 这一次性改动。**可控的变量只有 umask 本身**
（`mktemp -d` 与 `mkdir` 行为一致，都只遵循当时的 umask），这正是补丁改 umask
而非改创建命令的原因。

**实际暴露面**：能读到这些片段的是**同组 `file_manager`**（片段 `0660`，同组同时可写），
不是 other；隔离来自**组边界**而非目录私有性——实测该构建路径整条链对同组均可读可遍历：

```text
2771  /storage/Users/currentUser
2751  /storage/Users/currentUser/.conan2
2751  /storage/Users/currentUser/.conan2/p
2751  /storage/Users/currentUser/.conan2/p/b
2771  .../p/b/debfo567d371d4110f/{,b,b/build-release}
```

（更上层 `/storage`、`/storage/Users` 为 `711`，other 只能遍历不可列举。）
临时目录位于一次性 build folder 内，内容为 `configure` 的变量值（`S["…"]="…"` 赋值，
无凭据或密钥），并在该次 `config.status` 进程退出时由其自身的退出 trap
`{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; }` 清理（`config.status` 第 583-589 行）。
该 trap 的开关是脚本内的 shell 变量 `debug`（`$debug || { trap … }`），而
`config.status --debug` 会把 `debug` 置为 `:` 从而**不挂**该 trap——此时 `ac_tmp` 会留在
工作目录（本节上方捕获正是这样取得的）；`configure` 自身没有 `--debug`（实测 rc=1），
所以该例外只在**直接运行 config.status** 时出现，`conan create` 的正常路径（由 configure
代跑 config.status、不带 `--debug`）总是清理。
如需进一步收敛，可选的等价做法是改走知识库 E114 的 `bypass-mktemp` 路径（预先建好可写目录
并把 `ac_tmp` 指向它），但那需要额外改写 `configure` 的内部变量，改动面更大、失效风险更高，
本包未采用。


## 5. 依赖 flags 必须靠 `AutotoolsDeps`

`AutotoolsToolchain` 只产出编译器与它自己的 flags（实测 configure 命令行与
`CFLAGS` 里只有 `-DNDEBUG -Wall -O3`），requirements 的 `-I`/`-L` 由
`AutotoolsDeps` 注入。只调前者时 `configure` 的
`AC_CHECK_LIB(gc, GC_malloc)` 仍会成功（该宏只链接不编译头文件），错误推迟到
`make`：

```text
/storage/.../b/src/error.c:3:10: fatal error: 'gc/gc.h' file not found
make[2]: *** [Makefile:425: error.o] Error 1
```

`generate()` 因此必须两个都生成（同型先例：`archives/g/guile/2.2.7.1/conanfile.py`、
仓库内共 177 个 autotools 配方使用 `AutotoolsDeps`）。这是模板
`templates/conanfile-autotools.py.tmpl` 未示范的一点：该模板的 `requirements()`
是空的 `pass`，所以照抄模板不会暴露。

## 6. `make install` 依赖 coreutils 的 `install`

`etc/Makefile.am`：

```make
install-data-local:
	install -d $(DESTDIR)$(localstatedir)/lib/debfoster
```

`configure` 探测到的 `INSTALL` 是 `.../ginstall -c`（`$(INSTALL)`），但这一行写的是
裸命令 `install`，OHOS 上没有：

```text
install -d .../prefix/var/lib/debfoster
make[2]: install: No such file or directory
make[2]: *** [Makefile:500: install-data-local] Error 127
```

补丁 `0003-etc-makefile-install-d.patch` 改用 autoconf 提供的 `MKDIR_P`，
同时改 `Makefile.am`（源模板）与 `etc/Makefile.in`（现成生成物，本包无法重生成）。

## 7. `src/keepers.c` 缺少 `<fcntl.h>`

```text
keepers.c:22:31: error: use of undeclared identifier 'O_RDONLY'
keepers.c:28:30: error: use of undeclared identifier 'O_RDWR'
keepers.c:28:37: error: use of undeclared identifier 'O_CREAT'
```

`keepers.c` 只包含 `<sys/file.h>`；glibc 的该头会间接引入 `<fcntl.h>`，OHOS 的
musl 不会。补丁 `0002-keepers-include-fcntl.patch` 显式补上这一行。这是可移植性
缺陷而非平台特判，不涉及 `__OHOS__` 条件编译（R8）。

## 8. 上游测试

上游没有测试套件：四个 `Makefile.am` 里没有 `TESTS`，tarball 里没有
`tests/`/`test/`/`check/`/`spec/` 目录，也没有 `test_*.c`。`make check` 目标存在、
配方也真实调用了它，但**递归到的每一层都无事可做**——各层输出形态并不完全相同，
引用日志时不能笼统写成「四个子目录都打印 Nothing to be done」：

```text
RUN: make check -j1
Making check in src
make[1]: Entering directory '.../src'
make[1]: Leaving directory '.../src'            # src：进入后直接离开，无任何输出
Making check in etc
make[1]: Entering directory '.../etc'
make[1]: Nothing to be done for 'check'.        # etc/doc/po：各一行，全日志合计 3 次
...
make[1]: Entering directory '.../build-release'
make[1]: Nothing to be done for 'check-am'.     # 顶层：字符串是 check-am，1 次
```

计数复核（在采信轮的完整日志 `reports/conan-create.log` 上实跑；该日志按规则 19 不入库，逐字摘录见 `reports/evidence-excerpts.md` §1）：

```sh
grep -c "Nothing to be done for 'check'" reports/conan-create.log   # 3
grep -c 'check-am'                       reports/conan-create.log   # 1
```

配方仍在 `build()` 里调用 `make check -j1`，让这一事实在每轮构建日志中可核
（而不是只在文档里口头声明）。用例数按第 7.3 节口径记 `TOTAL=0`：
既不是 PASS 也不是 SKIP，属「未发现可运行的上游测试入口」。

### 上游 `configure` 的一条良性报错

构建日志里还有一行看起来像错误、但 `configure` 仍以 rc=0 结束的输出：

```text
.../b/configure: line 4638: AX_CFLAGS_WARN_ALL: command not found
```

`configure.ac` 的

```m4
if test "x$GCC" = xyes; then
   AM_CFLAGS=-Wall
   AX_CFLAGS_WARN_ALL
fi
```

把 `AX_CFLAGS_WARN_ALL`（autoconf-archive 的宏）写成独立一行，而**随包发布的
`configure` 里该宏没有被展开**——它以裸 shell 命令的形式留在 `configure` 第 4638 行，
运行时因此报 `command not found`。这说明上游生成该 `configure` 时并没有 autoconf-archive：
这正是本包无法自行重生成 `configure` 的同一前提（见第 2 节）。

影响面：只是少追加一组额外告警开关（`AM_CFLAGS` 里的 `-Wall` 已生效，实测编译行为
`-DNDEBUG -Wall -O3`），不影响产物、不影响 `configure` 的返回码。**不要为消除这条
信息去打补丁**：补丁会改动 `configure` 的字节，而它同时承载 `umask 022` 的修补，
只会把一条良性信息换成一次真实的重生成风险。

等价的能力验证由 `test_package/test.sh` 的 36 项 CLI 行为断言承担：它用运行时
生成的 dpkg status 夹具驱动真实 `bin/debfoster`，比对 golden stdout 与退出码，
覆盖版本、用法面、错误码契约、六种查询模式与交互式 keeper 文件改写。
统计见 `manifest.yaml` 的 `test_results`。

## 9. 依赖 `gc/8.2.12` 的固有 stderr 告警

`src/error.c` 用 `GC_malloc` / `GC_malloc_atomic` / `GC_strdup` 实现 `xmalloc`
系列，`configure.ac` 用 `AC_CHECK_LIB(gc, GC_malloc)` 检测，因此
`gc/8.2.12` 是硬依赖（W0 实测：`conan install --requires=gc/8.2.12 --build=never`
在 ohpcd 上直接命中 binary，`gc/8.2.12: Already installed!`）。

该包静态链接后每次运行都会向 stderr 输出一行：

```text
GC Warning: Failed to find PT_GNU_RELRO segment inside PT_LOAD region
```

对该静态归档在 OHOS 上的探测（`$HOME/tmp/debfoster-2.8/explore/gcprobe/`）
证明它与本包无关且无法用链接选项消除：默认、`-Wl,-z,relro,-z,now`、
`-Wl,-z,norelro`、`-Wl,-z,noseparate-code`、`-Wl,--no-rosegment`、`-no-pie`
六种链接形态下，最小探针程序 `GC_INIT(); GC_MALLOC(64);` 全部打印同一行告警，
且全部正常返回（`gc probe ok 0x...`）。告警来自 `libgc.a` 自身对所在
PT_LOAD 段的检查，属于该发行包的既知现象（仓库内 `archives/p/poke/5.0/notes.md`
第 5 条、`archives/g/guile/*/notes.md` 等同样记为良性并 adopted）。因此
`test_package/test.sh` 只比对 stdout，不把 stderr 纳入任何断言；
`debfoster --version`、六种查询模式、交互模式的 exit code 均为 0，功能不受影响。

## 10. 包装布局

- `configure` 由 Conan 传入 `--prefix=/`（包内绝对路径在安装期被 relocatable 化）
  与 `--bindir=${prefix}/bin --sbindir=${prefix}/bin`：`sbin_PROGRAMS` 因此落在
  包内 `bin/`，与 `cpp_info.bindirs = ["bin"]`、VirtualRunEnv、W3 的 L2 探针
  以及 OHOS 无独立 `sbin/` 的惯例一致。
- `--localstatedir` / `--sysconfdir` 未改写，仍是 `${prefix}/var` 与
  `${prefix}/etc`，`DEFS` 里固化成

  ```text
  -DVAR=\"/<prefix>/var\" -DETC=\"/<prefix>/etc\" -DLOCALADIR=\"/<prefix>/share/locale\"
  ```

  因此默认 keeper 文件与 dpkg 状态路径是包前缀下的绝对路径。这是上游默认行为，
  真实使用时应通过 `-c` / `-k` / `-o` 指定系统路径（`test_package/test.sh`
  第 6 节即验证了两种路径都按契约工作）。Do not 假装它能自动找到 `/var/lib/dpkg/status`。
- `package()` 除 `bin/debfoster`、`etc/debfoster.conf`、`share/man/man8/debfoster.8`
  外，把 `COPYING` 与 `doc/LICENSE.AVLTree`、`doc/LICENSE.symbol` 收进
  `licenses/`：本包代码是 GPL-2（`COPYING` 是清单文件，正文在
  `doc/LICENSE.debfoster`），内嵌 AVL 树是 LGPL-2，`src/symbol.*` 是 LGPL-2.1。
  `doc/LICENSE.debfoster` 是 GPL-2 正文，`COPYING` 也已收，故不重复收录全文之外
  的文件；`.gmo`/`.po` 由 `po/` 子目录的 install 规则安装到
  `share/locale/<lang>/LC_MESSAGES/`。
