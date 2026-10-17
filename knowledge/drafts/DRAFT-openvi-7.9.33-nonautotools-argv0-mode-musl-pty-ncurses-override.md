# DRAFT-openvi-7.9.33：argv[0] 决定模式且 vi 模式 getopt 串不含 -s + 上游 PAWK 探测链不可靠 + CURSESLIB 覆盖连带抑制 pkg-config 的 -I + musl 无 libutil + ex 批处理（无 tty）仍需 terminfo + HMFS /tmp 只读须让写死路径跟随 $TMPDIR

> Contributor: yanjiaxin | Status: Draft | Updated: 2026-09-12
> Source: PR #9678 feat(openvi): 7.9.33 适配 HarmonyOS PC
> 关联任务：contrib-5587

## 背景

openvi 7.9.33 是 OpenBSD vi/ex（nvi 血统）的独立可移植重打包，**纯手写 GNUmakefile**
（非 autotools）：没有 configure / config.h / codegen，交叉编译靠命令行变量
`CC / INCLDS / CURSESLIB / LINKLIBS` 覆盖即可。产物 `bin/{vi,ex,view,xinstall}` +
man 页 + `libexec/virecover`。

它同时是一个「按 argv[0] 选模式」的多别名 CLI，并且依赖 ncurses 的终端 UI。
这两点加起来，决定了 HarmonyOS PC 上的适配与**验证路径**。

## 坑 0：argv[0] 决定模式；vi 模式 getopt 串不含 `-s`，批处理必须调 `bin/ex`

### 现象

```text
$ bin/vi -e -s out.txt
vi: invalid option -- 's'
Usage: vi [-eFRrSsv] ...
```

### 根因

`common/main.c:68-78` 为三种模式各准备了一条 getopt 串（非 DEBUG 分支）：

| pmode | argv[0] | optstr |
|-------|---------|--------|
| MODE_EX | `ex` | `c:C:FlRrSst:vw:` |
| MODE_VI | `vi` | `c:C:eFlRrSt:w:` |
| MODE_VIEW | `view` | `c:C:eFlrSt:w:` |

只有 **ex 串含 `s`**（silent / 批处理）。`vi -e -s` 里的 `-s` 会被 `openbsd_getopt`
直接拒绝——`-e` 只是切到 ex *行为*，getopt 串仍是 vi 那条。

上游 `install` 用 `ln -fs vi bin/ex`（`GNUmakefile:235` 的 `LNS = $(LN) -fs`，
`bin/ex` 规则在 `GNUmakefile:578-582`）生成别名，argv[0] 为 `ex` 时 `pmode=MODE_EX`。

### 为什么这件事对 CI 重要

ex 批处理模式**不初始化屏幕**：不需要 tty。而 `vi`/`view` 模式要起屏幕
（curses）。CI worker 是无头环境（没有 tty），所以 **ex 模式是唯一可在 CI 上
实跑的路径**——所有冒烟与功能断言都得走 `bin/ex`。

⚠️ 但「不初始化屏幕」≠「不碰终端系统」：ex 模式仍**需要 terminfo 数据库**
（见坑 4）。最初据此写成「ex 不需要 TERM/terminfo」，CI 立刻以
`ex: No terminal database found` 打脸。

### 处理

- `build()` 的层 1 smoke 用 `printf 'a\n...\n.\nwq\n' | bin/ex -s <file>` 做往返；
- `test_package/test.sh` 全部以 `"$EX"`（= `bin/ex`）驱动，只用 `"$VI" -e` 单独验
  「vi 副本可运行」一项；
- `package()` 用 `shutil.copyfile` 把 `bin/vi` 复制成 `bin/{vi,ex,view}`（上游是
  `ln -fs` 软链，但 Conan 打包 symlink 的解析在不同平台上不一致，同内容副本最稳）。

## 坑 1：上游 `PAWK` 依赖 `getconf` + 标准 PATH 双重探测

### 现象

`ex/ex_def.h`、`common/options_def.h` 生成失败 → 所有 `.o` 依赖这两个头 → 编译整体停摆：

```text
make: getconf: not found
# 或
make: awk: not found
```

### 根因

`GNUmakefile:233,237`：

```make
GETCONF     ?= getconf
PAWK         = command -p $(PENV) PATH="$$(command -p $(GETCONF) PATH)" $(AWK)
```

作者的原意是「无视用户 PATH、用系统标准 PATH 里的 awk」，于是套了两层
`command -p`：先 `getconf PATH` 拿标准 PATH，再在该 PATH 下找 `awk`。
在 OHOS 上 `getconf` 不一定在、返回的 PATH 也未必含可用 awk——**探测链任一环失败，
make 直接失败**，而失败信息只是 `awk/getconf not found`，不容易定位到「这是个探测链」。

### 处理

命令行覆盖 `PAWK=awk`：两个生成规则只是

```make
$(PAWK) -f "./ex/ex.awk" "./ex/ex_cmd.c" > "./ex/ex_def.h"
```

即 `awk -f 脚本 输入 > 输出`，走 PATH 里的 awk 语义完全等价（`AWK` 变量本身默认就是
`awk`）。**不改源码**，只覆盖探测产物。

## 坑 2：传 `CURSESLIB` 会**连带**抑制上游 pkg-config 对 `CFLAGS` 的注入

### 现象（两种错法，都不报「配置错误」）

- 只传 `-L/-l` 忘了 `-I` → 编译期 `fatal error: 'ncurses.h' file not found`；
- 完全不传 `CURSESLIB` → 宿主 `pkg-config ncurses --cflags` 的 `-I/usr/include/...`
  被注入到 OHOS 交叉编译里 → 用错平台的头（ABI 不符，且可能看起来「编过了」）。

### 根因

`GNUmakefile:108-115` 一个 `ifndef CURSESLIB` **同时门控两行**：

```make
ifndef CURSESLIB
  CFLAGS    += $(shell $(PKGCFG) ncurses --cflags 2> /dev/null \
                     || $(PKGCFG) curses --cflags 2> /dev/null)
  CURSESLIB += $(shell $(PKGCFG) ncurses --libs 2> /dev/null \
                     || $(PKGCFG) curses --libs 2> /dev/null)
endif #!CURSESLIB
```

「把 `CURSESLIB` 当普通库变量覆盖」的直觉在这里是错的：覆盖它等于告诉 Makefile
「curses 已经搞定了」，于是 **CFLAGS 的 `-I` 也一起断供**。这个耦合没有任何注释
提示，只有读 Makefile 才发现。

### 处理

`CURSESLIB` 必须给**整串**（`-I` + `-L` + `-l`），且路径由 Conan 依赖的 `cpp_info`
计算，不硬编码：

```python
nc = self.dependencies["ncurses"]
pf = str(nc.package_folder).replace("\\", "/")
nc_incs = " ".join(f"-I{pf}/{d}" for d in nc.cpp_info.includedirs)   # -I<pf>/include
nc_libs = " ".join(f"-L{pf}/{d}" for d in nc.cpp_info.libdirs)
nc_libs += " " + " ".join(f"-l{lib}" for lib in nc.cpp_info.libs)    # -lformw -lmenuw -lpanelw -lncursesw
```

`INCLDS` 覆盖时**保留上游的 4 个 `-I`**（`include common regex openbsd`）再追加
ncurses 头目录，否则源码里的相对 include 全断。终端库用 Conan `ncurses/6.6` 静态
wide-char（R26：系统同名库不产 `.so`）。

## 坑 3：上游默认 `LINKLIBS` 里的 `-lutil` 在 musl 上不存在

### 现象

```text
ld: error: unable to find library -lutil
```

### 根因

`GNUmakefile:173`：`LINKLIBS ?= -lutil $(CURSESLIB)`。
openvi 的 ex 脚本功能用 `openpty(3)`（`ex/ex_script.c:59` 在 Linux 上
`#include <pty.h>`，`:187` 调用 `openpty`）。**glibc 把 openpty 放在 libutil，
musl 直接把它放进 libc**（连 `<pty.h>` 也是 musl 自带）。OHOS musl 上既没有
libutil、也不需要它——保留 `-lutil` 必然链接失败。

### 处理

`LINKLIBS` 覆盖成与 `CURSESLIB` 同一串（即不带 `-lutil` 的 ncurses 静态库串）。
注意上游的 `LINKLIBS` 定义是 `-lutil $(CURSESLIB)`，只覆盖 `CURSESLIB` 不够，
必须整个覆盖 `LINKLIBS`。

## 坑 4：ex 批处理虽无 tty，但入口是 curses 的 `main()`，仍必须找到 terminfo

### 现象

编译、链接全部通过后，冒烟步骤在运行期失败：

```text
$ printf 'a\nX\n.\nwq\n' | bin/ex -s smoke.txt
ex: No terminal database found
```

### 根因

「ex 批处理不初始化屏幕」容易顺势推成「ex 不需要终端信息」——错。openvi 的
**程序入口不是 `common/main.c` 的 `editor()`，而是 `cl/cl_main.c:main()`**
（`cl/cl_main.c:69`）。`main()` 在调用 `editor()` 之前，无条件走：

```c
clp = cl_init(gp);          /* cl_main.c:82 */
term_init(ttype);           /* cl_main.c:93 → setupterm() */
...
rval = editor(gp, argc, argv);  /* cl_main.c:117 */
```

`term_init()`（`cl_main.c:222-245`）直接 `setupterm(ttype, STDOUT_FILENO, &err)`，
`err == -1` 即 `openbsd_errx(1, "No terminal database found")`。也就是说：
**只要 invoke bin/vi（含 ex/view 别名），不管哪种模式，都必须能定位到 terminfo
数据库**。「批处理」省掉的是屏幕/`isatty`，省不掉 `setupterm`。

### 处理

数据库不用自造——Conan `ncurses/6.6` 包**自带** `share/terminfo`（该包
`package()` 把它列为**必备产物**，缺失即报错），并在 `package_info()` 里用
`runenv_info` 定义了 `TERMINFO` / `TERMINFO_DIRS`：

```python
terminfo = os.path.join(self.package_folder, "share", "terminfo")
self.runenv_info.define_path("TERMINFO", terminfo)
self.runenv_info.define_path("TERMINFO_DIRS", terminfo)
```

于是：

- **`test_package`**：`self.run(..., env="conanrun")`，runenv 自动带 `TERMINFO`，
  开箱即用；另在配方里按依赖包目录再显式注入一层（防传递 runenv 行为变化）。
- **`build()` 的层 1 冒烟**：`conanbuild` 环境**不含**依赖的 `runenv_info`，
  必须自己指过去——按 ncurses 依赖的 `package_folder` 拼
  `$pf/share/terminfo`，并 `export TERM=vt100`（`TERM` 为空会走 `term_init` 的
  unknown 回退：fprintf + `sleep(5)` + `setenv("TERM","vt100")` 再试一次，
  能用但白等 5 秒且污染 stderr）。

### 一句话

> 「无 tty」与「无 terminfo」是两件事。凡入口 main() 走 curses 初始化的编辑器
> （nvi/vi 家族、OpenVi 的 `cl/` 实现），**批处理模式仍需 terminfo**；
> CI 上要在 build 阶段跑它，必须显式给 `TERMINFO`（Conan ncurses 已随包发）。

## 坑 5：HMFS 的 `/tmp` 只读，而 openvi 把备份临时文件与恢复目录**写死**

### 现象

编译、链接、terminfo 都过了，运行期仍失败：

```text
$ printf 'a\nX\n.\nwq\n' | bin/ex -s out.txt
Error: Unable to create temporary file: Read-only file system
```

### 根因

openvi 沿用 4.4BSD 的写死路径，**完全不看 `$TMPDIR`**：

| 位置 | 写死值 | 用途 |
|------|--------|------|
| `common/exf.c:141` | `tname[] = "/tmp/vi.XXXXXX"` | 编辑期备份文件（mkstemp） |
| `ex/ex_filter.c:53` | `tname[] = "/tmp/vi.XXXXXX"` | `!cmd`/`%!` 过滤器的临时文件 |
| `include/pathnames.h` | `_PATH_PRESERVE "/var/tmp/vi.recover"` | 崩溃恢复目录，经 `common/options.c:335` 的 `recdir` 选项生效 |

HarmonyOS 的 HMFS 把 `/tmp` 挂成**只读**（不是「不存在」也不是「无权限」），
于是 `mkstemp("/tmp/vi.XXXXXX")` 在运行期返回 `EROFS`。这类错误的隐蔽之处在
**它只在运行期炸**：编译、链接、`--help` 全部正常。

### 处理

打一枚最小补丁 `patches/0001-honor-tmpdir.patch`（3 个文件，各 1 处），
让写死路径**跟随 `$TMPDIR`，无 `$TMPDIR` 时回退原值**——默认行为不变：

```c
/* common/exf.c、ex/ex_filter.c */
char *oname, *tmpdir, tname[PATH_MAX];
if ((tmpdir = getenv("TMPDIR")) == NULL || *tmpdir == '\0')
        tmpdir = "/tmp";
(void)snprintf(tname, sizeof(tname), "%s/vi.XXXXXX", tmpdir);

/* common/options.c 的 recdir */
(void)snprintf(b1, sizeof(b1), "recdir=%s",
    (s = getenv("TMPDIR")) == NULL ? _PATH_PRESERVE : s);
```

三处都已有 `<limits.h>` / `<stdio.h>` / `bsd_stdlib.h`（= stdlib.h 的 BSD 别名，
声明 `getenv`），`options.c` 的 `char *s, b1[1024];` 也已在作用域内，**无需补 include**。

配方侧：`apply_conandata_patches(self)` 放 `build()` 开头（同 repo `zopfli 1.0.3`
先例），并在 build() 的层 1 冒烟里 `export TMPDIR="<build_folder>"`；
`test_package` 走 `TMPDIR="<work>" /data/service/hnp/bin/bash test.sh`。

### 一句话

> 「写死 `/tmp`」在 HMFS 上等价于「写死一个只读目录」。凡在运行期创建临时文件的
> 老 Unix 程序，适配时**先 grep `/tmp`**（`grep -rn '"/tmp' src/`），能覆盖 `$TMPDIR`
> 就打 $TMPDIR 补丁而不是去 chmod/挂载——后两者都改不了 HMFS 的只读属性。

## 验证

```sh
# 层 1（build() 内 smoke，ex 批处理往返，无 tty）
export TERM=vt100 TMPDIR=<可写目录> TERMINFO=<ncurses-pf>/share/terminfo   # 见坑 4/5
printf 'a\nOPENVI_BUILD_SMOKE_OK\n.\nwq\n' | bin/ex -s smoke.txt
grep -qx OPENVI_BUILD_SMOKE_OK smoke.txt

# 层 2（test_package/test.sh，8 项断言，全走 bin/ex）
"$EX" -s created.txt      # 新建+写入
"$EX" -s sub.txt          # %s 替换 / 1,2d 范围删除 / $a 追加
"$EX" -s -R ro.txt        # 只读拒写（cmp -s 验证未修改）
"$XI" -m 0640 xi.src xi.dst   # BSD setmode 权限位
"$VI" -e                  # vi 副本可运行
```

覆盖路径：行编辑缓冲、BSD regex 兼容层（`%s`）、文件读写、`-R` 只读、BSD
setmode/parsemode（`xinstall -m`）、argv[0] 别名、$TMPDIR 临时文件路径。

## 关系

- **同族先例**：`neatvi`（同 repo，vi/ex 编辑器）同样用 ex 批处理在无头 CI 里实跑，
  并同样遇到 HMFS `/tmp` 只读。差别在于 **neatvi 自己认 `$TMPDIR`，只需环境变量
  重定向；openvi 写死 `/tmp`，必须打补丁**——同一个 HMFS 约束，两种解法，
  取决于上游是否可配置。
- **musl 差异**：本坑 3 与 `knowledge/musl-compat.md` 一脉相承——「glibc 有的
  libutil，musl 并到 libc」是同一类「按 glibc 直觉写链接参数会在 musl 上失败」。
- **覆盖即关闭探测**：坑 2 是「Makefile 里一个变量同时门控 CFLAGS 与 LIBS 探测」
  的通用陷阱，凡 `ifndef <LIBVAR>` 同时包住 `--cflags` 与 `--libs` 的手写
  Makefile 都可能复现，覆盖时必须两边都给。
- **构建期全绿 ≠ 适配完成**：坑 4 与坑 5 都是「编译链接通过后，运行期才暴露」的
  问题（terminfo 缺失、`/tmp` 只读）。手写 Makefile 工程没有 `make check`，
  必须在 `build()` 里自建一次**真运行**的 smoke，否则 CI 会在 test_package
  才第一次运行二进制，定位成本翻倍。
