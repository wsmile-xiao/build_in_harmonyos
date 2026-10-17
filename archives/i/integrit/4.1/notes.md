# integrit 4.1 适配笔记

## 编译环境
- 构建系统: autotools（`configure` + `make`，2007 年 autoconf 生成物，含 `hashtbl/` 子工程）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（`aarch64-unknown-linux-ohos`）
- 状态: built

## 编译步骤

```bash
# conanfile.build() 实际执行顺序
_fix_candidates(...)                      # pass 1：修 source 树的 configure /
                                           #   hashtbl/configure（umask 归一，见问题表 #2）；
                                           #   多根候选 + 断言闸 targets_hit/umask077_residue
./configure --prefix=/ --sbindir=/bin \
            CFLAGS="-O3 -pipe -DNDEBUG"    # prefix=/ 是 Conan AutotoolsToolchain 默认值
                                           #   （不是 package_folder），R33 经 extra_cflags 钉死
_fix_candidates(("config.status",), …)     # pass 2：修 configure 生成的 config.status
sh ./config.status                         # 显式解释器重跑（不依赖 +x，见问题表 #9）
make -j1                                   # R9 固定单线程
chmod +x test/test                         # tarball 内无执行位（source 树，见问题表 #10）
make test                                  # 上游 31 断言（见问题表 #3；容忍 #31 环境限制）
# package()：不走 make install（上游零 $(DESTDIR)，见问题表 #4），
#            直接 copy 收 build/source 两树产物 → bin/ + man/man1/ + info/
```

产物：`bin/integrit`（经 `--sbindir` 归位）、`man/man1/{integrit,i-ls,i-viewdb}.1`、`info/integrit.info`。
链接面：`clang -L. -Lhashtbl -o integrit … -lhashtbl -lintegrit` —— 只链**自身**静态库，
`readelf -d` NEEDED **仅 `libc.so`**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台判据命中 1 处内联 `__asm__("roll %%cl,%0")`（`gnupg/bithelp.h:54`，x86 ROL 指令） | GnuPG 1.0.6 的 RMD160 辅助头带 x86 快路径，**但整段包在 `#if defined(__GNUC__) && defined(__i386__)` 内**，`#else` 是纯 C 宏 `#define rol(x,n) (((x)<<(n))\|((x)>>(32-(n))))` | **判定为 `#ifdef` 备用路径，非真实构建面，不改码**。五重编译探针实证（aarch64/clang 15.0.4）：①`clang -E` 展开后 `roll %%cl` 出现 **0 次**、展开体为纯 C 移位表达式；②探针程序编译 rc=0、运行 rc=0（`rol(0x12345678,7)=0x1a2b3c09` 正确）；③唯一 include 该头的真实 TU `gnupg/rmd160.c` 编译 **rc=0**；④`clang -S` 产物 `roll` **0 次**；⑤端到端 `make -j1` rc=0。**复发条件**：`gnupg/rmd160.c` 或 `gnupg/bithelp.h` 的构建面发生变化、或目标架构切换到 i386/x86_64（`__i386__` 定义）时，本判定失效须重核（bcp #7 同格式） |
| 2 | `./configure` rc=0 但 `config.h` 未生成，日志逐字 `./config.status[929]: can't create ./confstatXXXXXX/in: Permission denied`、`mv: bad './confstatXXXXXX/out': Permission denied` | autoconf 2.59 生成器用 `(umask 077 && mktemp -d -q "./confstatXXXXXX")` 建临时目录；HMDFS 按共享属主落盘成 **2700**，other 无 w ⇒ 后续 `subs.sed`/`out`/`in` 全部写不进（E114 / DRAFT-E678 同族） | `build()` 内 `_fix_candidates()`（配合 `_fix_one()`，原名 `_fix_config_tmp_mechanism` 已改）对**生成物**做四处正则归一：`umask 077 && mktemp -d -q "./confstatXXXXXX"` → `umask 022 && mkdir -p ./conftmp`；fallback `tmp=./confstat$$-$RANDOM` → `tmp=./conftmp`；`umask 077 && mkdir $tmp` → `umask 022 && mkdir -p $tmp`；残余 `umask 077` → `umask 022`。作用对象=主 `configure`、`hashtbl/configure`、`config.status`（configure 之后幂等补一遍）。**只改 conan cache 内的生成物，不进 git ⇒ `patches: []` 无源补丁**（与 coinor-symphony 同一处置） |
| 3 | `make test` **31 断言 = 30 PASS + 1 FAIL**；末位断言 #31（`test/test:75`）`test $status = 2`「check error exit status」实得 `1` | 测试场景 `touch $modfile && chmod 000 $modfile` 期望文件不可读 ⇒ integrit 返回 `INTEGRIT_EXIT_FAILURE`(2)。**HMDFS 把 `chmod 000` 改写为 `-rw-rw----` 且文件仍可读**（设备探针：6/6 可写路径 `chmod 000` 全部失效、`cat` 全部成功）⇒ integrit 读到空文件、校验和变化 ⇒ 返回 `INTEGRIT_EXIT_CHANGES`(1)。**属设备权限语义限制，非代码/配方缺陷**（§一.10 / §一.27 同族） | 如实记录 `31 = 30 PASS + 1 FAIL`，#31 单列非 PASS 技术原因 + 原始证据（`w0-5-maketest.md` 含 chmod 探针原文与期望 2/实得 1 逐字）。`build()` 内 `make test` 打印**真实** `INTEGRIT_MAKE_TEST_RC=$rc` 而不吞掉，仅不让该已知环境限制打断构建。**test_package 侧用「配置文件缺失」路径（`-C does-not-exist` ⇒ rc=2）独立验证 `EXIT_FAILURE(2)` 契约本身在本设备可测**，与 #31 的 chmod 路径互补 |
| 4 | **`package()` 里 `make install` 往根目录写：`install: //info: Permission denied`、`creating directory //man/man1`（双斜杠）—— install-DESTDIR 传播缺失族·环内第 1 红** | 三重叠加：① Conan `AutotoolsToolchain` 的 `prefix` **默认是 `"/"`**（构造函数 `prefix="/"`），`Autotools.install()` 又**无条件**补 `DESTDIR=<package_folder>`；② **上游三份 `Makefile.in` 的 `DESTDIR` 计数全部 = 0**（`Makefile.in` / `doc/Makefile.in` / `utils/Makefile.in` 逐份 grep 实测），**完全不支持 DESTDIR**；③ `doc/Makefile.in` 的 `install-man`/`install-info` 直接 `$(INSTALL) -d $(MANDIR)/man1`，`MANDIR=@mandir@=${prefix}/man` = `/man`、**无 `$(DESTDIR)` 前缀** ⇒ 安装目标就是根目录。顶层 `install` 先 `cd doc && $(MAKE) $@`（命令行 DESTDIR 会经 MAKEOVERRIDES 传给子 make，**但规则不使用它**），doc 一炸即停 —— 修好 doc 后顶层 `$(SBINDIR)`（Makefile.in:146/148）会以同一方式往 `/bin` 写，**是同一个坑不是两个** | **⚠️ 原判断已被证伪（记录以免复读）**：原文「依赖 Conan 默认把 `--prefix` 指向 `self.folders.package` 即可正确落包」**错** —— Conan 的 prefix 是 `/`；W0 手工预检传了绝对 `--prefix=<路径>` 才能过，**掩盖了 Conan 的 `/`+DESTDIR 语义**（与 #11 并列的「预演盲区」**参数面**）。**采用修法 C（copy 收产物，否决 patch 与绕 DESTDIR 两案）**：三份 Makefile.in 全零 DESTDIR ⇒ 补丁面铺满三文件每个 install 规则 + PF5 面 + 新失败面；`Autotools.install()` 无条件插 DESTDIR 也绕不开。`package()` 改为直接 `copy` 产物，交付面按**地面真相**（W0 三件 install 取证日志：`makeinstall.log`/`sb-install.log`/`ns-install.log`，均 `--prefix=<绝对>` 形态）枚举：`bin/integrit` + `man/man1/{i-ls,i-viewdb,integrit}.1` + `info/integrit.info`，**上游不发货任何 lib/ 与 include/**（`libintegrit.a`/`libhashtbl.a` 是私有构建产物）。**两目录分属**：man 三件是 `config.status: creating doc/*.1` → **build 树**；`integrit.info` 是 tarball 自带 + `INFO_FILES=integrit.info` 走 `$(srcdir)/` → **source 树**（只从 build 收会漏它）。**三自查全 PASS**：①copy 包树 == W0 取证全集（**diff 空、逐字节同集**）②`package_info` 收敛 `bindirs=["bin"]` + 清空 `libdirs`/`includedirs`/`libs`，与包树逐项对齐（G4 的 package_info↔包树判据）③二进制 `integrit version 4.1` rc=0、67968B **未 strip**（`.codesign` 有效）；**L5 复算 = pass（bin/ has content）**；`--sbindir=/bin` 已无 install 语义依赖、按裁决保留（configure 期无害）。**连带收益**：copy 取 make 原产物 ⇒ 天然绕开 `$(STRIP)` ⇒ #7/E703 的签名问题在本路径**自动满足**（一案解两题）。**复发条件**：上游 Makefile 零 `$(DESTDIR)` + Conan `prefix="/"` 的组合 ⇒ 一律 `copy` 收产物，不要试图 patch 或绕 DESTDIR |
| 5 | 上游把二进制装进 **`$(sbindir)` = `sbin/`**，与 Conan/CIC 消费约定及产物门禁（G4 查 `bin/lib/include`、L5 查 `bin/` 或 `lib/`）不一致，会导致 L5 `No bin/ or lib/ content found` warn | `Makefile.in:29 SBINDIR = @sbindir@`、`:148 $(INSTALL) … $(SBINDIR)/$(PROG)`；autoconf 默认 `sbindir=${exec_prefix}/sbin` | 用**一个 configure 开关** `--sbindir=/bin` 归位（`configure --help` 实测支持 `--sbindir=DIR`；值必须是**根起绝对路径**——配合 Conan `prefix=/` + 安装期 `DESTDIR=<package_folder>` 语义，写相对值或未展开占位会被 configure 以 `expected an absolute directory name` 拒绝）。不改源码、不做安装后文件搬运，`package_info()` 的 `bindirs=["bin"]` 与产物路径自然一致 |
| 6 | `make test` 首次执行报 `make: ./test/test: Permission denied`（Error 127） | 上游 tarball 内 `test/test` 即为 `-rw-r--r--`（**无执行位**），解包后无法直接执行（`test/make-config`、`test/make-filetree` 有执行位，唯独 `test/test` 没有） | 构建/测试前 `chmod +x test/test`（**生成物面操作，不进 git**；`Makefile` 的 `test ::` 目标直接调 `$(srcdir)/test/test`） |
| 7 | **任务卡预期「无 root/net/TTY 要求」与实测差异** | 任务卡按用例语义判"不碰 root/net/TTY"，该判断本身正确（31 条断言确实无一需要 root、网络或终端）；但用例 #31 依赖**文件权限位语义**，属任务卡未覆盖的第三个维度 | **以实测为准如实披露**：31 条断言无 root/net/TTY 依赖，但**触碰权限面**且该面在 HMDFS 上不可用 ⇒ #31 单列。不硬套任务卡措辞、不因任务卡说"无要求"就把 #31 记为 PASS |
| 8 | **安装后的 `bin/integrit` 执行报 `Operation not permitted`（test_package 必挂）** | 上游 install 规则是 `$(INSTALL) $(STRIP) -m 755 …`，configure 判定有 strip 后 `STRIP = -s`。hnp clang 给每个 ELF 链接一个 `.codesign` section，**strip 重写布局后所存签名与实际内容失配** ⇒ 加载器校验失败 EPERM。实测三组对照：make 产物 67968B **可跑**；install-strip 后 51032B **EPERM**；把未 strip 的 `cp` 一份 **可跑**。注意 `readelf -S` 两者**都有** `.codesign`（strip 后是 [24]）——**不是 section 被删，是签名失效**，据此容易误判成"签名还在为何不能跑" | **最终采用 `package()` 直接 `copy` 收 make 原始产物**（见问题表 #4：上游三份 Makefile.in 全零 `$(DESTDIR)`，`make install` 会往根目录写）——copy 取的正是未经过 `$(STRIP)` 的原始产物，**签名天然有效**，本条 EPERM 与 #4 的 DESTDIR 问题由同一修法一并解决。备选（若某包必须走 install）：`autotools.install(args=["STRIP="])` ⇒ Conan 自动补 `DESTDIR=`，实际执行 `make DESTDIR=<pkg> STRIP= install`；make 命令行变量优先级最高，覆盖 Makefile 的 `STRIP = -s`。实测产物 67968B、`bin/integrit -V` → `integrit version 4.1` rc=0，man/info 仍完整安装。**复发条件**：任何上游 install 含 `$(STRIP)` 且产物在 OHOS 上报 EPERM 的包，同法处置；若不能禁 strip，退路是对可执行文件 `LD_LIBRARY_PATH= binary-sign-tool sign -selfSign` 自签（**禁止对 `.so` 重签**，见 device-facts §附录） |
| 9 | **`build()` 内手写 `self.run(..., cwd=self.source_folder)` 执行 configure 产物报 Error 127，G2 FAIL（采信轮 R2/R3 两轮）** | **Conan `basic_layout` 的 source/build 目录分离**：`source()` 解压落盘 `/p/<h>/s`，随后 `Copying sources to build folder` 把源码拷进 `/p/b/<h>/b`，`autotools.configure()` / `autotools.make()` **都在 build_folder 执行**（日志 `L83 Calling source() in …/s`、`L92 Building your package in …/b`、`L98 RUN: "…/b/configure"` 三点互证）。手写 `cwd=self.source_folder` 于是去**没有 configure 运行产物**的原始源码树找文件 ⇒ 必然找不到。**判读陷阱（勿再走弯路）**：R2 报 `inaccessible or not found`（toybox 对 `./xxx` 的措辞）曾被误诊为「HMDFS 可执行位不持久」；改用 `sh ./config.status` 显式解释执行后**仍 127、措辞变 `No such file or directory`** —— 执行位因素被彻底排除，**报错措辞不能当根因，先核 cwd 与目标文件是否真在该目录** | **方案①（采用）：删除该 `config.status` 幂等重跑行** —— 证据已证 configure 一次成功（`config.status: creating Makefile` / `creating config.h` / `utils/Makefile` / `doc/Makefile` 全部完成），该行是探索期 configure 半途失败的补救遗留，保留反而构成**掩蔽面**（AC_OUTPUT 真失败时 configure 自身 rc≠0 才是该响的信号，二次重跑会把失败洗成假绿）。**同时把其余两处同族 `cwd` 一并改对**：`_fix_config_tmp_mechanism(...)` 原修 `s/configure` 而实际运行 `b/configure`（修错目录=修了没生效），`chmod +x test/test`、`make test` 原 `cwd=source_folder` ⇒ `make` 在无 Makefile 的 s 目录必失败、**却被 `; exit 0` 吞成假绿** —— 三处全部改为 `self.build_folder`。**复发条件**：`build()` 内任何手写 `self.run(..., cwd=…)`，cwd 必须是 `self.build_folder`（`autotools.*` 的工作目录），不要用 `self.source_folder`；优先用 `autotools.*` helper 而非手写 run |
| 10 | **`make test` 在 conan build 内会因 `test/test` 无执行位而整段没跑**
| 11 | **本地预演全绿但 conan 内必挂（两轮采信轮学费）**
| 12 | **修对了 cwd 却把 HMDFS fix 的 root 改错：一次动作同时修好一族、修坏一族（R4）** | **决定性语义（Conan `Autotools.configure()` 源码）**：`script_folder = conanfile.source_folder`、`cmd = "<source_folder>/configure"`、`conanfile.run(cmd)` **不带 cwd ⇒ 执行目录 = `build_folder`**（out-of-source）。本包日志定位：`source_folder = …/b`（`RUN: "…/b/configure"`）、`build_folder = …/b/build-release`（`WARN: Build folder …`）。⇒ **两类文件分属两目录**：源码类（`configure`、`hashtbl/configure`、`test/test`）在 **source**；生成物类（`config.status`、`Makefile`、`make test` 的 cwd）在 **build**。R2/R3 `fix(source_folder)` 正好命中真正运行的 `b/configure` ⇒ AC_OUTPUT 成功；R4 我把 cwd 三处改对时**顺手把 fix 的 root 改成 `build_folder`** ⇒ `b/build-release/configure` 不存在 ⇒ 三目标全 `isfile=False` 被 `continue` **静默跳过** ⇒ 未修的 configure 走 `confstat` ⇒ Makefile 没落地 ⇒ `make: no makefile found`。`chmod +x test/test` 同批被我改到 `build_folder` 也错（`test/` 是 pristine 源码树） | **修法（A，已实现）**：①**多根候选** `_fix_candidates()` 遍历 `source`/`build`/`build-parent` 三根，layout 无关；②**反静默断言闸**：每个文件恒打 `[hmdfs-fix] <tag>: fixed conftmp=N umask077_residue=M sub_hits=H`，阶段末打 `ASSERT targets_hit=K umask077_residue=0 OK`，**K=0 或 M≠0 直接 `raise`** —— 「静默 no-op」是本轮根因，修复必须自带"不再静默"的证明；③**两次 fix**：`pre-configure` 修源码侧 generator → configure → `post-configure` 修生成的 `config.status` → `sh ./config.status`（显式解释器不依赖 +x）cwd=**build**；④源码类 cwd 一律 `source_folder`、生成物类一律 `build_folder`。**复发条件**：任何 autotools 配方里同时出现「手写 `self.run(cwd=…)`」「HMDFS fix 作用于多文件」时，必须先确认该文件属于哪一侧（源码 vs 生成物），不要一刀切同一个 folder | | 预演在 `$TASK_DIR/w0/src/integrit-4.1` **单目录**跑完整 `build()` 序列，configure 与 `config.status`/`Makefile` 落同一目录 ⇒ `./config.status` 永远找得到；而 conan 是 **s/b 分离**（见 #9）。**单目录预演对 `source_folder`/`build_folder`/`package_folder` 三者混用是结构性盲区**，且本地实证 `sh ./config.status` rc=0 还**强化了错误判断** | **预演必须复刻 Conan 目录拓扑**：把源码分别放两个目录（模拟 `s` 与 `b`），configure 在 `b` 跑，再用配方里**完全相同的 `cwd=` 语义**执行每一步；凡手写 `self.run(..., cwd=)` 一律先 `pwd; ls -la <目标>` 自证文件真在该目录 | | 上游 tarball 内 `test/test` 即 `-rw-r--r--`（无 x 位），而 `test/make-config`、`test/make-filetree` 都是 755。`Makefile` 的 `test ::` 规则直接 `$(srcdir)/test/test` ⇒ `Permission denied`；若 `make test` 外面套了容忍退出码（本配方为已知 #31 环境限制而容忍），该失败会被**静默吞掉 ⇒ 假绿**：日志里一条上游断言都不会出现 | 在 `make test` **之前**显式 `self.run("chmod +x test/test", cwd=self.source_folder)`（生成物面操作，不进 git）。判据：容忍上游测试退出码的同时，必须能从日志看到断言痕迹（如 `TEST FAILED` 或 `everything's fine`），**只有容忍没有痕迹 = 假绿** |

## 源码修改

**无（`patches: []`）**。所有适配动作均在 `conanfile.py` 的 `generate()`/`build()` 内完成，
作用对象是 Conan 缓存中的生成物（`configure`/`config.status`/`hashtbl/configure`）与
configure 开关，**不改动任何进入 git 的上游源文件**。

## 依赖版本

**运行期/构建期外部依赖：无（空集）**。

- `requirements()` 为空；`readelf -d bin/integrit` NEEDED 仅 `libc.so`。
- 捆绑内置：RMD160（`gnupg/rmd160.c`，GnuPG 1.0.6 改编）、哈希表（`hashtbl/` 子工程）、
  CDB 数据库（`cdb*.c`）—— 全部随源码构建为 `libhashtbl.a` / `libintegrit.a`。
- 可选依赖 **libgc（Boehm GC）** 仅在 `./configure --with-leakfind=DIR`（开发者查泄漏开关）下
  才被 `AC_CHECK_LIB(gc, …)` 探测，且全部 `#include "leakfind.h"` 都在 `#ifdef ELC_FIND_LEAKS`
  内；本适配**不启用该开关**，故不构成依赖。
- 编译工具链：clang 15.0.4 / make 4.4.1（Conan `tool_requires` 面无额外需求）。

## 验证结果

```bash
# 上游测试（沙箱 HOME，源码树自建 4×4 文件树）
$ grep -c 'TEST FAILED' test/test
31
$ make test
30 PASS / 1 FAIL（fail-fast，末位 #31）
# 证据: $TASK_DIR/w0/w0-5-maketest.md（含 chmod 000 探针原文、期望 2 实得 1 逐字）

# 消费者测试（test_package/test.sh，调用已安装二进制）
$ sh test.sh
test_package: ALL 9 CONSUMER ASSERTIONS PASSED   # rc=0（设备实测）

# 产物与链接面
$ ./bin/integrit -V
integrit version 4.1
$ readelf -d bin/integrit | grep NEEDED
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]
```

## 注意事项

- **#31 复发条件**：任何以 `chmod 000` 制造"不可读"语义的上游用例，在 HMDFS 上都会以
  「期望 `EXIT_FAILURE`(2)、实得 `EXIT_CHANGES`(1)」形态失败；不要按代码缺陷排查。
- `gnupg/bithelp.h` 的 x86 asm 判定失效条件见问题表 #1「复发条件」。
- 上游无 `make check` 目标，测试入口是 **`make test`**（`MANIFEST.yml` 已声明）。
