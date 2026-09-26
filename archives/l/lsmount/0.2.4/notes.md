# lsmount 0.2.4 适配笔记

## 编译环境
- 构建系统: makefile（**裸 Makefile**，无 configure、无 autotools、无 cmake）
- 编译日期: 2026-09-25
- 编译器: clang 15（`/data/service/hnp/bin/clang`，profile host `os=OHOS arch=armv8 compiler=clang/15 libcxx=libc++ os.version=6.0`）
- 构建主机: A 机（HarmonyOS PC，aarch64）
- worktree: `~/qzy/主理-42-lsmount-0.2.4`，分支 `feat/lsmount-0.2.4`，基线 `48d9cee684`
- CONAN_HOME: `~/tmp/ch/home-lsmount`
- 状态: built

## 源码与依赖

| 项 | 值 |
|---|---|
| 源包 | `https://github.com/Llandon/lsmount/archive/refs/tags/v0.2.4.tar.gz` |
| sha256 | `cb3cb9fb675278e513b038df20846638498912e94c38f85d789e9f6ae11fc67d` |
| 大小 | 9424 B，18 个文件（5×`.c` + 6×`.h` + Makefile/README/LICENSE/CHANGELOG.md/doc/share×2） |
| 语言 | C（`-std=gnu99`），R47 语言预检与任务声明一致 |
| 依赖 | `libconfig/1.7.3`（`libconfig.a`，静态）、`ncurses/6.5`（`libncursesw.a`，静态） |
| 许可证 | ISC（LICENSE 全文为 ISC 措辞；`lsmount --help` 亦打印 `License: ISC`） |
| 产物 | 单个可执行文件 `lsmount`（170432 B）+ `res/lsmount.rc.default` + `res/lsmount.txt` + `licenses/LICENSE` |

### W0 依赖发布实证（R35 口径：不用通配 `conan list` 判 binary）

```
conan download libconfig/1.7.3 -r=ohpcd --only-recipe   -> RC0，rev 2015782aeaa9d33b25de8e66e80444ac
conan download ncurses/6.5     -r=ohpcd --only-recipe   -> RC0，rev 69914b9d115a9d31e4b32372c44e49bf
conan install --requires=libconfig/1.7.3 --requires=ncurses/6.5 --build=never \
              --profile:host=ohos-aarch64 --profile:build=default               -> INSTALL_RC=0
  Profile host 实测：os=OHOS / arch=armv8 / compiler=clang / version=15 / libcxx=libc++
  libconfig/1.7.3:...#7029711321b3961583fe1a1f87f244ad - Download (ohpcd) → Package installed
  ncurses/6.5:...#f68a0f13a561a4dda4ad15d3072bcc45     - Download (ohpcd) → Package installed
```
⇒ 两枚依赖的 **OHOS aarch64 二进制制品确认存在**（`--build=never` 下命中远端下载，非本地 Cache）。
日志：`~/tmp/uc2/z42-lsmount/probe/install.log`

### 上游测试清点（R51）

```
源包无测试目录：  ls -d tests test      -> ls: tests: No such file or directory
                                         ls: test: No such file or directory
无测试目标：      make -n check         -> make: *** No rule to make target 'check'.  Stop.
Makefile 全部目标: all debug clean install uninstall manpage   （6 个，无 check/test）
18 个文件清单内无任何测试源文件（*.c 全部为产品代码）
```
⇒ **上游静态用例数 declared = 0**（"确无"而非"未跑"），证据即上述三条命令输出。

## 编译步骤（配方实际执行的动作）

```python
VirtualBuildEnv(self).generate()      # 提供 pkg-config / PKG_CONFIG_PATH
PkgConfigDeps(self).generate()        # 生成可重定位的 libconfig.pc（见坑 #4）
tc = AutotoolsToolchain(self)         # flags 进 env CFLAGS（Makefile 用 += ⇒ env 被保留后追加）
tc.extra_cflags += ["-I<ncurses include>", "-D'gettext(x)=(x)'",
                    "-D'textdomain(x)=((void)0)'", "-D'bindtextdomain(d,p)=((void)0)'"]
make CC="<conf 里的 c 编译器>" \
     LDFLAGS="-L<ncurses lib> -L<libconfig lib> -lncursesw -lconfig -z now" -j1
```
`build()` 不调用 `make install`；staging 全在 `package()` 里用 `copy()` 完成。

> 踩坑记录：`AutotoolsToolchain.cflags` 在 Conan 2.29.1 是**只读 property**（由 `extra_cflags` 参与计算），
> 对它 `extend()` 会**静默丢失**——A 机实测 `conan create` 的编译行只剩 `-O3`，gettext 又变回未声明。
> 必须写 `tc.extra_cflags`。（`autotoolstoolchain.py:229 def cflags` / `:37 self.extra_cflags`）

---

## ★ B 定稿素材：裸 Makefile 烧死系统路径 —— 可覆盖把手逐项实证

上游 `Makefile` 全文 48 行。**被烧死的行（原样行号 + 原文）**：

| 行 | 原文 | 性质 | 有没有把手 |
|---|---|---|---|
| 3 | `CC          = /usr/bin/gcc` | 烧死**宿主编译器** | ✅ 有：simple `=` ⇒ **只有命令行赋值能覆盖**（env 无效，env 会被 makefile 的 `=` 直接顶掉） |
| 4 | `PKG_CONFIG ?= pkg-config` | 宿主工具名 | ✅ 有：`?=` ⇒ env 或命令行都可覆盖 |
| 5 | `CFLAGS     += -std=gnu99 -lconfig -D_GNU_SOURCE -fcommon` | 上游自身 flags | ✅ 有：`+=` ⇒ **env CFLAGS 被保留后追加**（正解）；⚠ 命令行 CFLAGS 反而会把本行全部丢掉 |
| 6 | `CFLAGS     += \`$(PKG_CONFIG) --cflags libconfig\`` | 反引号取依赖 | ✅ 有：靠 PKG_CONFIG_PATH 引导到 Conan 生成的 .pc |
| 7 | `LDLIBS     += \`$(PKG_CONFIG) --libs libconfig\`` | 反引号取依赖 | 同上 |
| 8 | `LDFLAGS     = -ltermcap -z now` | 烧死 **termcap 库名** + 加固位 | ⚠ simple `=` ⇒ env 无效，**只能命令行整体覆盖**；覆盖会连带丢掉 `-z now` ⇒ 必须原样重写回来 |
| 13 | `all: CFLAGS += -O2 -Wall -pedantic -fPIE -D_FORTIFY_SOURCE=1` | target-specific 加固 | 保持原样（env CFLAGS 追加不影响它） |
| 36–39 | `install:` → `cp lsmount /usr/bin/$(BIN)`、`cp share/lsmount.rc.default /etc/lsmountrc`、`cp doc/lsmount.1.gz /usr/share/man/man1/` | **烧死三处系统绝对路径** | ❌ **无把手**：全文 **没有 `PREFIX`、没有 `DESTDIR`、没有 `INSTALL`/`BINDIR`/`MANDIR` 变量**（逐行核实） |
| 41–44 | `uninstall:` 同样烧死 `/usr/bin`、`/etc`、`/usr/share/man` | — | ❌ 无把手 |
| 46–48 | `manpage:` → `a2x -f manpage doc/lsmount.txt` + `gzip -f doc/lsmount.1` | 依赖宿主 asciidoc 工具链 | ❌ 无开关；但 **`manpage` 不是 `all` 的依赖**，只有 `install`（第 36 行 `install: lsmount manpage`）会拖它 |

**结论（本包采用的零补丁路线）**：`PREFIX/DESTDIR/INSTALL` 一律不存在 ⇒ `make install` 在 conan 语境下**根本不可用**（会往活的 `/usr/bin`、`/etc` 写文件），而且它还会连带触发 `a2x`（设备实测 `a2x`/`xmlto` 均 MISSING）。所以**不修 install 目标、也不给它加 DESTDIR**，改成：**只跑 `make`（默认 `all`，天然不碰 manpage），由 `package()` 自己 `copy()` 到 `package_folder/bin`**。整条路径没有任何一行源码为此改动。

**本配方实际用到的命令行/环境赋值（全部为上游已有把手）**：

| 赋值 | 落在哪个把手 | 作用 |
|---|---|---|
| `make CC="/data/service/hnp/bin/clang"` | Makefile:3（simple `=`） | 换掉烧死的 `/usr/bin/gcc`；编译器取自 Conan conf `tools.build:compiler_executables:c`（R33，不裸用 shell `$CC`） |
| `make LDFLAGS="-L… -lncursesw -lconfig -z now"` | Makefile:8（simple `=`） | 换掉烧死的 `-ltermcap`（OHOS 无此库），**并把同行的 `-z now` 原样保留**（防加固被覆盖丢失，test_ohos T2c 专门断言这一点） |
| `env CFLAGS="-I<ncurses> -D'gettext(x)=(x)' …"` | Makefile:5/6/13（`+=`） | 注入 ncurses 头文件目录与 NLS 停用宏；用 env 而非命令行，正是为了不顶掉上游 `-std=gnu99 -D_GNU_SOURCE -fcommon -O2 -Wall -pedantic -fPIE -D_FORTIFY_SOURCE=1` |
| `env PKG_CONFIG_PATH=<Conan 生成的 generators>` | Makefile:4（`?=`）+ 6/7 | 让上游自己的 `pkg-config` 调用解析到 Conan 依赖，而不是不可重定位的包内 .pc |
| **不调用** `make install` | —（无 PREFIX/DESTDIR/INSTALL 把手） | 绕开三处烧死路径 + a2x 依赖，改由 `package()` staging |
| `make … -j1` | — | R9 |

## -Werror 处置

**上游 `all`（默认构建路径）不含 `-Werror`**：全文只有第 16 行 `debug: CFLAGS += -g -Og -DDEBUG **-Werror** -Wextra …` 这一处，且它是 **target-specific**（只对 `make debug` 生效）。配方跑的是默认目标 `all`（第 13–14 行），因此：

- **不需要**任何 `-Wno-error` 追加，也没有为此打补丁；
- 交叉编译下新 clang 引入的 warning（实测 8 条，均为 `-Wunused-command-line-argument`、`-Wunknown-warning-option`、`-Wformat-nonliteral` 之类）在 `all` 路径上**不会升级为错误**；
- 若将来有人改用 `make debug`，那 8 条 warning 会被 `-Werror` 打死 —— 已在此记录，属上游 `-Wconversion/-Wpacked` 家族问题，与本适配无关。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `src/lsmount.c:116:19: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *' [-Wint-conversion]`（伴随 4 条 `call to undeclared function 'gettext'`） | OHOS sysroot 的 `libintl.h` 是 **353 字节空壳**：只 `#define __USE_GNU_GETTEXT 1`，**不声明 `gettext`/`textdomain`/`bindtextdomain`**（`grep -rl gettext <sysroot>/usr/include` 无结果）。上游 `src/helper.h:4` 是 `#define _(STRING) gettext(STRING)` ⇒ 隐式声明返回 int ⇒ `-Wint-conversion` 变错误 | 上游**不带任何 `.mo`/`po/` 语言目录**，NLS 对它是死代码 ⇒ 在 env CFLAGS 里把三个入口映射为 identity/no-op（`-D'gettext(x)=(x)'` 等），语义等价于知识条目 **E027** 的 `--disable-nls`，但上游无 configure，故走编译期。**不改源码、不打补丁** |
| 2 | `/bin/sh: syntax error: unexpected '('`（`make` 展开 `$(CFLAGS)` 时把 `-Dgettext(x)=(x)` 直接交给 shell） | make 展开 `$(CFLAGS)` 不做引用，括号被 shell 当语法 | 把**单引号写进 env 值本身**（`-D'gettext(x)=(x)'`），由执行 recipe 行的那层 shell 剥掉；A 机实测展开后命令行形如 `… -D'gettext(x)=(x)' -std=gnu99 …` 且编译通过 |
| 3 | 链接期缺 `-ltermcap`（OHOS 无 termcap 库） | Makefile:8 烧死 `-ltermcap`；`ncurses/6.5` 制品只发布 `libncursesw.a`（**无** `libtermcap` / `libtinfo` / 任何 `.so`） | 命令行覆盖 `LDFLAGS` 为 `-lncursesw`（`llvm-nm --defined-only libncursesw.a` 实证 `T setupterm`、`T tigetnum`，`del_curterm`/`cur_term` 由最终链接成功反证）；同时**原样保留 `-z now`** |
| 4 | `src/options.c:4:10: fatal error: 'libconfig.h' file not found`（用包内自带 .pc 时） | `libconfig/1.7.3` 包内 `lib/pkgconfig/libconfig.pc` **不可重定位**：`prefix=/` ⇒ `Cflags: -I/include`、`Libs: -L/lib -lconfig`，在 conan 依赖目录里指向不存在的路径 | 不用包内 .pc；改用 Conan `PkgConfigDeps` 生成的 .pc + `VirtualBuildEnv` 注入的 `PKG_CONFIG_PATH`。另外为去掉对 pkg-config 的硬依赖，`LDFLAGS` 里显式带上两个依赖的 `-L`/`-l` |
| 5 | **`./lsmount` 运行时 SIGSEGV（rc=139），连 `./lsmount -h` 都崩** | `src/lsmount.c:44-45`（改前）`const struct passwd* pw = getpwuid(getuid()); const char* homedir = pw->pw_dir;` **未判空即解引用**。A 机实测：`getuid()=20020105`、`getpwuid()=NULL`（`/etc/passwd` 里连 root 的 `pw_dir` 字段都是空：`root:x:0:0:::/bin/false`）⇒ 鸿蒙 app uid 不在 passwd 库内 ⇒ 崩溃发生在 `parsecmd()` **之前**，所以所有调用路径（含 `--help`）全崩 | 加 `patches/0001-src-lsmount.c-guard-null-getpwuid.patch`：`pw && pw->pw_dir && *pw->pw_dir` 三级判空 → 回退 `getenv("HOME")` → 再回退 `"/"`。**纯判空，不含任何平台宏**（PF5 口径安全），且在任意 libc 上都是正确性改进（glibc 下 uid 不在 passwd 时同样会崩） |
| 6 | 设备无 `install` 命令（先例 E098/E108） | HarmonyOS 构建主机不提供 coreutils `install` | 本包**不需要**它：不调用 `make install`，staging 由 `package()` 的 `copy()` 完成（见上节）。未引入 `INSTALL=cp -f` 之类的覆盖，因为根本没有可覆盖的 `INSTALL` 变量 |
| 7 | `a2x` / `xmlto` 缺失 ⇒ manpage 无法生成 | 宿主 asciidoc 工具链在设备上 MISSING（`command -v a2x` / `xmlto` 皆空） | **不装宿主工具、不伪造 .1.gz**；`manpage` 只被 `install` 目标拖着，而本配方不调用 `install` ⇒ 天然不触发。改为把上游 manpage **源文件** `doc/lsmount.txt` 原样交付到 `res/`，消费者保留文档 |

## 已知上游缺陷（本次**未**修，如实登记）

`lsmount -x / --set-colors <任意值>` 在本机必崩：`src/options.c:109-131` 的 `case 'x'` 用
`char* const tokens[] = {NULL}` 调 `getsubopt()`，按 POSIX 语义此时返回 `-1` 且 `*value = NULL`，
紧接着 `colors[i] = colortoesc(value)` 把 NULL 传进 `colortoesc()`，其首行即
`if(!strcmp(cstr, "black"))` ⇒ 空指针解引用。

```
实测（A 机，修复 getpwuid 之后）：
  ./lsmount -x "1,2,3"                                       -> rc=139 SIGSEGV
  ./lsmount -x "red,green,blue,yellow,magenta,cyan"          -> rc=139，输出 "Signal 11 (core dumped)"
  ./lsmount -x "notacolor"                                   -> rc=139
```
判定：**与 HarmonyOS 无关的上游输入校验缺陷**（`-x` 对任何入参都崩，非平台特有分支），
超出"把包装到鸿蒙上"的适配范围 ⇒ **不改**，也**不纳入测试用例**（不拿必崩路径当断言，也不为凑绿删除断言）。
建议主代理在 PR 正文「已知问题」处登记，或另开 upstream/Issue。

## 源码修改

只有一个补丁，且只改一处判空（与路径烧死问题无关）：

- `patches/0001-src-lsmount.c-guard-null-getpwuid.patch`（`-p1` 应用，`src/lsmount.c` 第 43 行起 +7/-1 行）
  已在 A 机验证：`patch -p1 --dry-run` RC0、`patch -p1` RC0，且打完补丁的树与我手工验证过的那棵树 `diff` **完全一致**。

## 依赖版本

| 依赖 | 版本 | 形态 | 备注 |
|---|---|---|---|
| libconfig | 1.7.3 | `libconfig.a`（静态） | `config_init/config_read_file/config_lookup_*` |
| ncurses | 6.5 | `libncursesw.a`（静态，唯一发布件） | `setupterm/tigetnum/del_curterm/cur_term` |

两枚均静态吸收 ⇒ 交付的 ELF 除 libc 外无运行时依赖，不涉及 RPATH/`.so` 签名面。

## 验证结果

见下节「测试账本」与门禁日志（本文件随门禁推进补记 rc 与日志路径）。

```bash
# 手工验证（写配方前，A 机机动短单槽内）
sh ~/tmp/uc2/gate.sh 2500      -> GATE_PASS（MemAvailable=14499MB PSI_full=avg10=40.7 编译器进程=0）
sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 -- bash …/manual_build.sh
                               -> MAKE_RC=0，产物 ELF64 AArch64 / ET_DYN / GNU_RELRO / BIND_NOW
```

## 交付物

| 文件 | 说明 |
|---|---|
| `bin/lsmount` | 可执行文件（170432 B，手工验证阶段实测尺寸；ELF64 AArch64 PIE） |
| `res/lsmount.rc.default` | 上游默认配置（原 `install` 要放进 `/etc/lsmountrc` 的那份） |
| `res/lsmount.txt` | 上游 manpage 源文本（无法渲染成 `.1.gz` 的诚实替代） |
| `licenses/LICENSE` | ISC |

## 注意事项

1. **版本串口径**：任务版本 `0.2.4` = 上游 tag `v0.2.4` 去掉 `v`，与目录 `archives/l/lsmount/0.2.4/`、`conanfile.version`、分支 `feat/lsmount-0.2.4` 四处一致，未做"归一化"。
2. **源码 URL 口径变更（需主代理确认）**：主代理给的 `deb.debian.org/.../lsmount_0.2.4.orig.tar.gz` 会被 framework v12.20 的 **PF7 源URL闸**判为「Debian 下游重打包源」直接拦（`scripts/ohc/preflight.py:_PF7_DEBIAN_HOSTS` 含 `deb.debian.org`）。已改用上项目官方 GitHub tag 归档，**两条 URL 内容逐字节等价**（同为 9424 B、同一 sha256、18/18 文件逐个 sha256 相同），未引入任何镜像前缀。仓内 `archives/a/a52dec/0.7.4/conandata.yml` 仍写 deb.debian.org，属 PF7 上线（v12.20）前的存量——**存量不等于新 PR 可用**（PF7 只扫本 PR 变更文件）。
3. `L2` smoke 门禁用 `--version` 再回退 `--help`：上游**没有** `--version`（`-v` 是 `--print-vertical`），`--version` 退出码 1，但 `--help` 退出码 0 且正文含 `Version: v0.2.4` ⇒ 走回退分支通过，已在 T1c 里把该版本串作为断言固定住。
4. 不要 `make install`，也不要给 install 目标"顺手加 DESTDIR"——那会把上游语义改掉且引入不必要的补丁；本包的 staging 面只有 4 个文件。
5. 本目录内 `.ci-result.json` / `.build-cache/` 属本地门禁产物，**禁止入库**（他包先例：入 PR ⇒ CI `JC5 未登记隐藏文件` blocking）。`.ci-result.json` 已在 `.gitignore:238` 登记，`git check-ignore` 实测命中。

## 知识沉淀（对应 manifest.yaml `knowledge_gained` 六条）

本次沉淀的六条机制记录在 `manifest.yaml` 的 `knowledge_gained`，正文即本笔记：

1. `simple =` vs `+=` 的覆盖语义差异（CC/LDFLAGS 只能命令行、CFLAGS/LDLIBS 只能 env）→ 本文「★ B 定稿素材」表
2. `make install` 烧死系统路径且拖 a2x ⇒ 不调用它、由 `package()` staging → 同上（行 36–39 / 46–48）
3. OHOS `libintl.h` 空壳 ⇒ 编译期停用 NLS → 「遇到的问题」#1
4. `ncurses/6.5` 只发布 `libncursesw.a` ⇒ `-ltermcap` 改 `-lncursesw` 且保住 `-z now` → #3
5. `libconfig` 包内 `.pc` 不可重定位 ⇒ 用 `PkgConfigDeps` → #4
6. 上游 `getpwuid()` 未判空在鸿蒙必崩 → #5
7. （工具坑，与 packaging 无关但同场记录）**`AutotoolsToolchain.cflags` 在 Conan 2.29.1 是只读 property**，`extend()` 静默丢失，必须用 `extra_cflags` → 「编译步骤」下的踩坑记录

## 对话记录

### 2026-09-25 编译全过程（A 机，子代理 主理-42）

**实际执行序列**（模式 B 路线：先检索、再手工探路、最后 conan 化并以 conan-verify 判绿）：

1. `SKILL.md` 1046 行通读 → 列出门禁顺序
2. `preflight_check.sh lsmount/0.2.4` → RC0（当时无 conanfile，判"无依赖可查"）
3. `recipe-search lsmount` → 无相似配方；`-b make` top1 critnib/1.1（读其骨架的 deps/patches 处理）
4. W0 依赖实证：`conan download --only-recipe` ×2 + `conan install --build=never`（host profile 实测 `os=OHOS`，两包均 `Download (ohpcd)`）
5. 源包双源核对：deb.debian.org `.orig` 与 GitHub tag 归档 **sha256/size/18 文件逐个 sha256 全等** → 取 PF7 允许的官方 GitHub URL
6. Makefile 逐行取证（烧死路径 / 把手类型 / `-Werror` 只在 debug 目标）+ 宿主工具探测（a2x/xmlto/install/cc MISSING）
7. 手工探路编译 ×3 轮：先撞 `-Wint-conversion`（gettext）→ 再撞 shell 括号引用 → 再撞 `libconfig.h` 找不到；最终 `MAKE_RC=0`，产物 ELF64 AArch64 PIE+RELRO+BIND_NOW
8. **运行即 SIGSEGV(139)** → 探针定位为 `getpwuid(getuid())` 返回 NULL（实测 uid=20020105）→ 加 0001 补丁 → 重编后 `-h`/默认/`--debug` 全部 rc=0 并正确渲染 139 条鸿蒙挂载
9. 写配方 10 个文件 → `test_package` 28 断言 + `test_ohos` 12 断言先对**手工二进制**验证全绿，再进 conan
10. `conan-verify` 第 1 轮 **G2 FAIL**：`tc.cflags.extend()` 静默丢失（编译行只剩 `-O3`）→ 改 `tc.extra_cflags` → 第 2 轮 **G0–G4 + L2/L4/L5 PASS，RC=0**
11. `finish lsmount 0.2.4 built`：conan-verify 复绿 → **W3 本地 CI 模拟通过**（`.ci-result.json` exit_code=0）→ `graph validate` 通过（doc↔kv 540 对）→ W2 原子性通过（仅 10 个配方文件）；`finalize-archive` 报 `packaging/README/test-report` 缺失，已补齐
12. 发现并修掉 `test.sh` 把临时件写进 `test_package/`（Conan 直接用该目录当 test build folder，隐藏文件会被 JC5 拦）→ 改 `$TMPDIR` + `trap` 清理

**关键修复**：
- [NLS] OHOS `libintl.h` 空壳 → 编译期 identity/no-op（等价 E027 `--disable-nls`）→ ✅
- [链接] `-ltermcap` 不存在 → `-lncursesw` + 保留 `-z now` → ✅
- [空指针] `getpwuid()` NULL → 0001 补丁回退 `$HOME` → ✅
- [工具] `AutotoolsToolchain.cflags` 只读 → `extra_cflags` → ✅
- [卫生] test 临时件污染 archives → `$TMPDIR` + trap → ✅

**未解决 / 交回主代理的事项**：
- `lsmount -x/--set-colors` 任意入参必崩（`colortoesc(NULL)` → `strcmp`），是与平台无关的上游缺陷，本次未改、未纳入测试
- `finish` 的 `finalize-archive` 仍期望 `packaging/*-ohos-aarch64.tar.gz` 与 `*-debug.tar.gz`；这与 PF2 制品闸 / JC3（源码仓禁提交压缩包）直接冲突，故只按 aiohappyeyeballs 等先例留 `packaging/.packaged` 标记，不产 tar 包
- `[10/10]` 提示的 `.staging-verified` **故意不创建**：`junk_check.sh:180` 的 `JC5_ALLOWED` 白名单里没有它（有 `.packaged`），造出来会直接触发 JC5 blocking
---

**编译结束**: 2026-09-25 19:37
**最终状态**: built
