# sntop 1.4.3 适配笔记

- 构建系统：autotools 形态（`configure` + `Makefile.in`），其中 `configure` 是
  **autoconf 2.13 的生成物**，上游不发布 `configure.ac`
- 编译日期：2026-09-25
- 编译器：clang 15.0.4（profile `ci/conan/profiles/ohos-aarch64` 指定的
  `tools.build:compiler_executables`）
- 状态：built（`conan-verify` 通过，未 upload）
- 依赖：ncurses/6.5（recipe + binary 均已发布，实测见下）

## 路径 B 声明（3+2）

- **适配路径**：路径 B（新增知识库条目 1 条）。SCT 预匹配的 M12 / M15-SIGALRM 两个
  候选面均被本包一手实测否证（见 `reports/knowledge-candidate-ledger.md` 一、二节），
  本包真正新增的是该台账第四节 M-A 那条机制：**autoconf 2.13 生成的 `configure` 把
  命令行上的 `VAR=value` 当成 host 三元组解析并拒绝（`invalid host type` →
  `can only configure for one host and one target at a time` 并以 error 退出、
  不产出 Makefile），同名变量的环境变量通道反而有效**。
- **使用知识库**：按文件名 + 行号引用三条既有条目——
  ① `knowledge/drafts/E568-draft-5818.md:55`（同名 `.kv:20`）（GNU make "命令行
  `VAR=value` 不是追加、是接管"的变量优先级定律）：本配方 `make INCLUDE=<ncurses>/include`
  正是**借用**这一定律，只接管 `INCLUDE = .` 这个单值变量、不动 `CFLAGS`，因而不丢上游旗标；
  ② `archives/a/alpine/2.26/conanfile.py` 与
  `archives/a/alpine/2.26/patches/0001-configure-ncursesw.patch`
  （"ncurses 归档只出 `libncursesw.a`"这一事实的同族先例）：本包按同一事实
  但用**不同解法**处置，取舍与判据见下"方案取舍"节；
  ③ `archives/n/ncurses/6.5/`（宽字符静态库 + `--enable-overwrite` 头文件布局）。
  另：`knowledge/drafts/libgetline-1.0-ohos-autotools-configure-args.kv:35` 与
  `knowledge/drafts/cvsgraph-1.7.0-autotools-no-canonical-host.kv:49` 两处附带告诫
  （"`VAR=value` 放进 configure_args 可能被吞 / 只适用 2.6x+ 生成物"）与本包实测同向，
  但都无错误签名、无替代写法，按 hit 四条件第 2、3 条**不作 hit 引用**，
  仅登记在 `reports/knowledge-candidate-ledger.md` 第三节供查重复核。
  台账第四节 M-B（上游 `Makefile.in` 不引用 `@CFLAGS@`/`@LDFLAGS@` 面）经主理裁定
  按"对不上行号就降 hit"处理，**不占本 PR 知识位**，只作 hit 邻接引用
  （`E568-draft-5818.kv:20` / 同名 `.md:55`、`libfec-…-missing-cflags.kv:20`、
  `DRAFT-PKG-VER-host-os-linux-substring-match-enables-werror.{kv:27,md:50}`）。
- **知识库扩展**：新增 1 条 —— 本 PR 携带成对草稿
  `knowledge/drafts/DRAFT-sntop-1.4.3-autoconf213-configure-rejects-host-args-env-var-channel.kv`
  与同名 `.md`：autoconf 2.13 世代的 `configure` 拒绝命令行 `VAR=value`，
  老 autotools 包传旗标必须改走环境变量通道，且"先读 configure 头部判世代、再定通道"
  是解法的一部分。它与通用池件
  `DRAFT-PKG-VER-custom-configure-only-cli-args-no-env.{kv,md}` 是**同一失效面的相反
  方向**（那一条是"只认命令行、忽略环境变量"），用 `similar_to` 互相指认。
- **关联 Issue**：#3410（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3410）

## 症状与根因（按出现顺序）

### 症状 1：`make` 首错 `fatal error: 'ncurses.h' file not found`

```
/data/service/hnp/bin/clang -I. -Wall -Wstrict-prototypes -O2  -DSTDC_HEADERS=1 \
  -DHAVE_SYS_WAIT_H=1 -DRETSIGTYPE=void -DHAVE_GETOPT_LONG=1  -DCONF_SFILE=\"...\" -c sntop.c
sntop.c:38:10: fatal error: 'ncurses.h' file not found
make: *** [Makefile:49: sntop.o] Error 1
```

（一手日志：`reports/p2-make.log`，同 `~/tmp/uc2/z45-sntop/p2-make.log`）

**根因**：上游 `Makefile.in` 第 39 行把 CFLAGS **整行重写**且**不引用 `@CFLAGS@`**：

```make
CFLAGS = -Wall -Wstrict-prototypes -O2 @DEFS@ -DCONF_SFILE=\"$(SNTOPRC)\"
```

`@DEFS@` 与 `@LIBS@` 这两个占位符存在、会被 config.status 替换（实测
`config.status` 里确有 `s%@CFLAGS@%...%g` 这条替换规则），但 Makefile.in 里
**没有任何地方使用 `@CFLAGS@` 或 `@LDFLAGS@`**。于是 configure 阶段从环境变量
读到的 `CFLAGS`/`CPPFLAGS`/`LDFLAGS` 只作用于 configure 自身的探测，
**一条也进不了真正的编译/链接命令**。

**最小复现**：

```sh
export CC=clang CPPFLAGS="-I<sncurses>/include" LDFLAGS="-L<ncurses>/lib"
bash ./configure --prefix=/tmp/x && make        # → 上面那条 file not found
grep -n '^CFLAGS =' Makefile                    # → 行内没有 -I，也没有 @CFLAGS@
```

### 症状 2：`sntop.c:457:10: error: incompatible integer to pointer conversion`

```
sntop.c:456:6: warning: call to undeclared function 'time'; ISO C99 and later do not support implicit function declarations
sntop.c:457:12: warning: call to undeclared function 'ctime'; ...
sntop.c:457:10: error: incompatible integer to pointer conversion assigning to 'char *' from 'int' [-Wint-conversion]
```

（一手日志：`reports/p4-make.log`）

**根因**：`end_html()` 用了 `time()` / `ctime()`，而 `sntop.c` 的 include 列表里
只有 `<sys/time.h>`，没有 `<time.h>`。`time_t` 由 `<sys/time.h>` 提供，但这两个
函数的**声明**在 `<time.h>`。上游当年在 glibc 上能过，是因为 glibc 的
`<sys/time.h>` 会连带拉进 `<time.h>`；musl/OHOS 的头文件划分不连拉，
于是成为隐式声明，`ctime()` 的返回值被当成 `int` 赋给 `char *`，clang 以
`-Wint-conversion` 直接判错。这是上游的的可移植性缺陷，与鸿蒙无关。

### 症状 3（良性假阴，不需修）：`checking for printw in -lncurses... no`

归档的 ncurses 只交付宽字符静态库 `libncursesw.a`，**不提供 `libncurses.a`**
（实拍：`ls <ncurses>/lib` → `libformw.a libmenuw.a libncursesw.a libpanelw.a`）。
上游 `configure` 的 `AC_CHECK_LIB(ncurses, printw)` 因此恒为 `no`。

之所以判定它**良性**而非必须修：

1. 该检查为 `no` 时只少一个 `HAVE_LIBNCURSES` 宏，而 `sntop.c` / `sntop.h`
   中没有任何地方读取 `HAVE_LIBNCURSES`（全量 grep 无命中），头文件是无条件
   `#include <ncurses.h>`；
2. `LIBS` 的最终值来自环境变量（检查失败后 configure 会 `LIBS="$ac_save_LIBS"`
   原样还原），因此只要 `LIBS` 里带 `-lncursesw`，链接就用得上真库；
3. 该检查失败**不会**让 configure 退出非零，实测 `CONFIGURE_RC=0`。

### 症状 4：上游 `make install` 不支持 DESTDIR，且目录不存在就 `false`

`Makefile.in` 的 install 规则形如：

```make
	@if [ -d $(INSTDIR) ]; \
		then cp sntop $(INSTDIR); chmod 755 $(INSTDIR)/sntop; \
		else echo "sntop: $(INSTDIR) does not exist"; false; \
	fi
```

没有 `$(DESTDIR)`，且 `$(INSTDIR)` / `$(ETCDIR)` 不存在时该目标**直接失败**。
另外 `ETCDIR` 存在时会往里面写一份样例配置 —— 如果 `--sysconfdir` 指向共享前缀，
构建就会污染 worker 的用户目录（R49/E524 那一类事故）。

## 已试过的失败方案

| # | 方案 | 结果与证据 |
|---|---|---|
| 1 | 按同族先例 `alpine/2.26` 的做法，把旗标当 configure 命令行参数传（`tc.configure_args` 里追加 `LDFLAGS=...`、`LIBS=...`） | **失败**：autoconf 2.13 把 `VAR=value` 位置参数当成 host 三元组。实拍 `configure: warning: CC=/data/service/hnp/bin/clang: invalid host type` → `configure: warning: CFLAGS=-DM12_CMD_MARKER: invalid host type` → `configure: error: can only configure for one host and one target at a time`，`rc=1` 且**没有产出 Makefile**（`reports/p1-arm-cmdline.log`） |
| 2 | 只设 `CPPFLAGS`/`LDFLAGS` 环境变量、交给 configure 把旗标带进 Makefile | **失败**（= 症状 1）：configure 确实收到了（`config.log` 内标记命中 9 次、`config.status` 里有 `s%@CFLAGS@%-DM12_ENV_MARKER%g`），但 Makefile.in 不使用该占位符，`make` 仍看不到 `-I`（`reports/p2-make.log`） |
| 3 | 给 `configure` 传 `--with-ncurses` / `--enable-ncurses` 之类开关 | **不存在该开关**：`configure --help` 与源码 case 分支里只有目录类选项（`--prefix/--bindir/--sysconfdir/--mandir/...`），没有库路径类选项 |
| 4 | 在 ncurses 的 lib 目录里补一个 `libncurses.a` 别名让 `AC_CHECK_LIB` 变绿（acedb / asterisk-flite 先例） | **不采用**：本包不需要那个宏（见症状 3 的 3 点判定），而为让一条无害检查变绿去改**依赖包**的产物目录，会污染共享缓存且超出本包 PR 边界。改为在 `LIBS` 里显式写 `-lncursesw` |
| 5 | 用 `make install DESTDIR=<staging>` 做暂存 | **不支持**：Makefile.in 全文无 `DESTDIR`（症状 4） |
| 6 | 把 `--sysconfdir` 直接指向运行期共享前缀，好让 `CONF_SFILE` 烧对 | **不采用**：install 规则会把样例配置真写进那个目录，构建成副作用于用户目录（R49）。改为 `--sysconfdir` 留在私有 pkgroot，只把 `SNTOPRC` 这一个 make 变量指到运行期路径 |

## 最终方案

1. **补丁 `patches/0001-sntop.c.patch`**：给 `sntop.c` 补 `#include <time.h>`
   （锚在 `<sys/time.h>` 之后）。纯 POSIX 可移植性修复，
   `platform_only: false`、`guard: 'none'` —— **不引入任何平台宏**（R8/PF5）。
   补丁由 `ohc-run.py refresh-patch --auto` 从 `.orig`/`.work` 差异生成，
   净变更 `+1/-0`，单文件 `sntop.c`。
2. **旗标走环境变量，不走 configure 命令行**（针对 2.13 世代的行为）：
   `generate()` 里用 `Environment()` define `CC` / `CPPFLAGS=-I<inc>` /
   `LDFLAGS=-L<lib>` / `LIBS=-L<lib> -lncursesw`，编译器路径取自
   `tools.build:compiler_executables`（R33，不裸用 shell 变量）。
3. **编译旗标经 `-I$(INCLUDE)` 钩子进真正的编译命令**：上游两条编译规则本来就写
   `$(CC) -I$(INCLUDE) $(CFLAGS) -c ...`，只是把 `INCLUDE` 硬赋成 `.`。
   make 的命令行变量优先级高于 Makefile 内赋值，于是
   `make INCLUDE=<ncurses>/include` 把 `-I` 送进去，**不改一行上游代码**。
4. **链接库路径随 `LIBS` 进 `@LIBS@`**：该占位符在 Makefile.in 里存在
   （`LIBS = @LIBS@`），所以 `-L` 写在 `LIBS` 里就能到位。
5. **`CONF_SFILE` 用 make 变量 `SNTOPRC` 在编译期定**：上游把它写成
   `-DCONF_SFILE=\"$(SNTOPRC)\"`，而 `SNTOPRC = $(ETCDIR)/sntoprc`。
   命令行覆盖 `SNTOPRC` 即让它指向运行期用户级前缀
   （`DEFAULT_PREFIX` 可覆盖，缺省取 `~` 下的 `usr/local/etc/sntoprc`），
   同时 `--sysconfdir`/`ETCDIR` 仍留在私有 pkgroot，install 不写用户目录。
   缓存包目录路径随 package id 变化，不能烧进二进制，故选用户级前缀；
   程序仍优先读 `~/.sntoprc`，`CONF_SFILE` 只是回落路径。
6. **install 到私有 pkgroot 再由 `package()` 搬进包目录**：先
   `os.makedirs` 出 `bin` / `etc` / `share/man/man1` 三个目录（否则上游
   `false`），两次 make 传**同一组** make 变量，避免 install 触发重编译时
   把 `CONF_SFILE` 换成暂存路径。
7. `package_type = "application"`、`package_info()` 只暴露 `bindirs`，
   并按 R38 在软件级目录补 `commands.json`。
8. **`export_sources` 用方法形态而非类属性**（过 G1 结构闸所需，主理已追认）：
   第 1 棒写的是类属性 `exports_sources = "patches/*"`，首轮 `conan-verify` 唯一红项
   即"`conanfile.py` 缺少: `export_sources()` 方法"；仓内惯例是方法形态
   （`def export_sources` 5109 份 vs 类属性 778 份），且原配方已 import 了
   `export_conandata_patches` 却未使用 ⇒ 改为方法形态调用它。**纯结构闸形式修复，
   未动任何构建逻辑**（详见本文件"第 2 棒门禁复验 → G1 首轮红与本棒修复"）。

## 验证结果（五维账本）

| 维度 | 数量 | 依据 |
|---|---|---|
| 上游测试（静态清点） | **0** | `make -n check` → `make: *** No rule to make target 'check'.  Stop.`；`Makefile.in` 目标全集仅 `all/proper/sntop/sntop.o/clean/install`；树内无 `tests/` 与任何测试夹具（`reports/p9-upstream-tests.txt`） |
| 消费者测试可执行断言 | **17** | `test_package/src/test_sntop.c` 的 `CHECK()` 计数（打印 `checks=17 failed=0`） |
| 实测通过 | **17** | 本机（鸿蒙 B 机）`conan create` 的 test_package 真跑输出：`reports/conan-create.log` 尾部 17 行 `PASS[01]`…`PASS[17]` 与 `checks=17 failed=0`（第 103-120 行）；W3 侧同源读数 `reports/w3-local-ci.log` 的 `L1_RESULT=pass: test_package executed` |
| 跳过 | **0** | 无 SKIP 行；SKIP 分支仅在本机 `ping(1)` 返回 127（命令不存在）时才走，本机 `ping` 可用 |
| 失败 | **0** | 同上 |

分母未缩减：未使用任何 `--disable-*` / 关测试 / 跳过测试的手段。
上游无可执行测试这一结论带一手清点证据，申报数 0 与实测一致（17 条全部来自
本次补写的消费者测试，申报值 ≤ 实测值）。

### 探索阶段的构建证据（鸿蒙 B 机真机）

```
CONFIGURE_RC=0  MAKE_RC=0  INSTALL_RC=0
产物 ELF 头: 7f 45 4c 46 02 01 01 ... e_machine=0xb7 (AArch64)
$ sntop --version      → "sntop v1.4.3 - a top-like console network status monitor"   rc=0
$ sntop --help         → Usage + 选项表                                                rc=0
$ sntop -d -o -w -p -f conf -e out.html → rc=0，HTML 内 firsthost=UP / secondhost=DOWN，
                         "<B>2</B> hosts polled: <B>1</B> up, <B>1</B> down"
```

（`reports/p5-build-evidence.txt`）

## 未执行 / 未覆盖的检查（如实披露）

1. **curses 界面路径未在 CI 环境下执行**。原因：消费者测试跑在 `conan test`
   里，没有控制终端。已探明该路径在设备上有能力跑通 —— 用 `pty.openpty()`
   分配伪终端后 `sntop -o -c` 确实输出了 curses 序屏转义序列
   （`\x1b[?1049h ... \x1b[?1049l`，141 字节，`reports/p6-tty-probe.txt`），
   但因 CI 侧无 tty，配方不把它列为通过项。消费者测试因此选择
   `-d`（守护）分支：源码里全部 curses 调用都被 `!(flags & DAEMON)` 包住，
   这条路径能真跑完整的"解析配置 → 探测 → 判定 → 渲染"链路。
2. **默认 `fping` 探测路径未覆盖**。本机 `fping` 缺位，不加 `-p` 时程序以
   退出码 6 报 `sntop: error, execution of (f)ping failed`
   （`reports/p7-consumer-trial.txt`）。fping 是外部运行时程序、不是本包的
   构建依赖，未在本 PR 内顺带适配。
3. **`-a` / `-l` 报警脚本执行路径未覆盖**（`exec_alarm()` → `execve(command,...)`）。
   该分支需要一个可执行脚本参数与状态翻转事件才触发，构造成本高，未纳入断言。
4. **`-w` 的 HTML 报表只在守护模式下验证**。curses 模式下的同一函数
   （`start_html/add_html/end_html`）随界面路径一并未执行。
5. **`getopt_long` 备用实现（`getopt_long.c`）未参与编译**。本机探测结果
   `HAVE_GETOPT_LONG=1`，`LIBOBJS` 为空，上游规则里的
   `if [ "${DOWENEEDGETOPT}" = getopt_long.o ]` 分支未走到。
6. **手工页只验证被安装，未验证渲染**。`make install` 会用
   `gzip -9` 压出 `share/man/man1/sntop.1.gz`（实拍已生成）。
7. **L2 烟雾测试只覆盖 `--version` 一条，不覆盖界面与探测面**。本轮 W3 实拍
   为 `L2_RESULT=pass: sntop --version OK`（`reports/w3-local-ci.log:295`），
   并非框架里常见的 `skip`（包内 bin 静态链 ncursesw，裸跑不需要 runenv）。
   即便如此它仍**不作为可执行性主证据**——主证据是上面 17 条 test_package
   真跑断言。

## 适用边界

- 本方案绑定"上游 `configure` 是 autoconf 2.13 生成物且**不发布** `configure.ac`"
  这一形态：不能 `autoreconf`，也不能用 `VAR=value` 命令行传参。
  一旦上游改发 `configure.ac` 或升到 ≥2.5x，第 2 条应回退成常规写法。
- 第 3 条（借 `-I$(INCLUDE)` 钩子）只对"Makefile.in 里存在
  `-I$(INCLUDE)` 且 `INCLUDE` 是普通 make 变量"的上游有效。
  若上游把 `INCLUDE` 写成 `override` 或去掉该 `-I`，此路失效，
  只能改为给 `Makefile.in` 补 `@CFLAGS@` 占位符的补丁。
- 第 5 条（`SNTOPRC` 指用户级前缀）的前提是本包 `CONF_SFILE` 只是回落路径、
  程序优先读 `~/.sntoprc`；若上游改变查找顺序，需重新评估。
- 症状 3 的"良性假阴"判定**只对 sntop 成立**，依据是"`HAVE_LIBNCURSES` 宏
  不被源码读取 + `LIBS` 由环境提供"。换一个读取该宏的软件，同样的
  `AC_CHECK_LIB(ncurses,...)` 失败就不是良性的，必须像 `alpine/2.26` 那样
  打补丁把探测库名改成 `ncursesw`。

## 方案取舍：为什么本包不照抄 alpine 的补丁

`archives/a/alpine/2.26/patches/0001-configure-ncursesw.patch` 面对同一个事实
（ncurses 归档只出 `libncursesw.a`），解法是**把 configure 里的探测库名改成
`-lncursesw`**。本包不照抄，因为：

- alpine 的 `configure` 在探测失败时会让后续构建拿不到 terminfo，补丁是**必需**的；
- sntop 的对应检查失败**不产生任何后果**（见症状 3 的三点判定），
  补上去只是把一条无害的 `no` 变成 `yes`，代价是多一个动上游 `configure`
  的补丁（该文件 44 KB、由 autoconf 生成、上游不再发布 `configure.ac`，
  每次升版都要重打并重新对位）。

故选"不改 configure，只在 `LIBS` 里写实际库名"。两条路都可行时挑动的文件更少的那条，
并把判据留在这里供后来者复核。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | 配方（application，in-source 构建） |
| `conandata.yml` | 源码 URL + sha256 + 补丁声明 |
| `patches/0001-sntop.c.patch` | `sntop.c` 补包含 `<time.h>`（`+1/-0`） |
| `test_package/` | 消费者测试：`conanfile.py` + `src/test_sntop.c` + `MANIFEST.yml` |
| `manifest.yaml` | 编译元数据与五维账本 |
| `notes.md` | 本文件 |
| `reports/` | 一手门禁与探针日志 |
---

## 第 2 棒门禁复验（2026-09-25 19:16-19:21，鸿蒙 B 机）

第 1 棒撞轮次上限时停在 `conan-verify` 途中，`reports/` 里只有知识候选台账。
第 2 棒把门禁跑到绿并落盘，读数如下。

### W0 依赖发布态（一手，非通配 list）

配方 `requirements()` 取 `ncurses/6.5`。清空本地缓存后重下：

```
conan download ncurses/6.5 -r=ohpcd --only-recipe
  Downloading recipe 'ncurses/6.5#69914b9d115a9d31e4b32372c44e49bf'   RC=0
conan install --requires=ncurses/6.5 --build=never -pr:h -pr:b
  ncurses/6.5#69914...:21b17f8b...#f68a0f13... - Download (ohpcd)
  ncurses/6.5: Package installed 21b17f8b2bc0e9511e276e3d57a23893067cefe5
  Install finished successfully                                        RC=0
```

即 recipe 与 OHOS-aarch64 二进制**都已发布**（6.4 / 6.6 同测亦均发布，备查）。
原始日志：`~/tmp/uc2/z45-sntop/w0b.log`（含 `Downloading recipe` 行，
不是 `Skip recipe ... already in cache` 那种假成功）。

### 取源合规（PF7，`scripts/ohc/preflight.py` 的 `_pf7_classify`）

`conandata.yml` 的 url 为 `https://downloads.sourceforge.net/project/sntop/sntop/1.4.3/sntop-1.4.3.tar.gz`：
https 且非 `file://`、主机名不在镜像前缀表、不是 Debian 系主机、不含 `+dfsg`
⇒ **四类判据全部不命中，未改动 conandata**。哈希对字（实测下载件）：

```
943a5af1905c3ae7ead064e531cde6e9b3dc82598bbda26ed4a43788d81d6d89  sntop-1.4.3.tar.gz
```

### G1 首轮红与本棒修复

首轮 `conan-verify` 唯一红项是 `conanfile.py 缺少: export_sources() 方法`
（原配方写的是类属性 `exports_sources = "patches/*"`）。仓内惯例是方法形态
（`def export_sources` 5109 份 vs 类属性 778 份），且原配方已经 import 了
`export_conandata_patches` 却未使用 ⇒ 改为

```python
    def export_sources(self):
        export_conandata_patches(self)
```

这是结构闸的形式修复，未动任何构建逻辑。

### conan-verify 与 W3 判决

```
conan-verify sntop 1.4.3 -> RC=0
  G1: PASS / G2 conan create: PASS / G3 系统同名库隔离 (R26): PASS
  判决行原文：✅ 配方验证通过: sntop 1.4.3   （可标记 status: published）
  报告：reports/conan-verify-report.md

finish sntop 1.4.3 built -> W3 本地 CI 模拟
  W3 判绿两条（同判）：
    ① 日志标记行原文：      ✅   ✅ W3 本地 CI 模拟通过
    ② .ci-result.json：     "step": "W3_local_ci"   "exit_code": 0
         log_sha256 24f80dace57c2f6e6d1feeb269a6f75986a84e3800fbca40222332237a7f7a73
         （与 reports/w3-local-ci.log 的实测 sha256 逐字一致）
    互证：Build Summary Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1)
          L0/L1/L2/L4/L5 全 pass；L1e 破坏性负照轮确认测试真依赖 sntop
          （[sabotage] bin/ moved away → Negative test confirmed）
  finish 侧另报 失败步骤 = step5b, step8（**不是 W3 的判据**，是收尾与汇总两步）：
    step5b：finalize 报缺 release/debug tar.gz、notes.md 无对话记录、
            manifest knowledge_count=6 unreferenced=6
    step8 ：gen_summary 失败: 'str' object has no attribute 'append'
    两者属框架互斥面（与本包无关），未以删件规避。
  末行 [step] Pre-download: conandata.yml 已还原为官方 URL（工作区无脏）
```

### 本报告引用的探针件来源说明

* `reports/p9-upstream-tests.txt`、`reports/p5-build-evidence.txt`、
  `reports/p6-tty-probe.txt`、`reports/p7-consumer-trial.txt` 是**第 2 棒重新复现**
  的捕获（第 1 棒把这些名字写进了台账但件未落盘）。其中 p9 用官方 tar 的新鲜解包 +
  真实 `configure`（`CONFIGURE_RC=0`，确实生成了 Makefile）后再问 `check`/`test`
  目标，并对两份 makefile 各数了一次 `^check:` / `^test:` 规则（都是 0）；
  p5/p6 的驱动对象是 `conan create` 真正装进包目录的那个二进制。
* `reports/p1-arm-cmdline.log`、`p1-arm-env.log`、`p2-make.log`、`p4-make.log`
  是第 1 棒原始日志的逐字副本。
* p6 的 T1 复现值与第 1 棒记下的读数一致：`pty bytes captured: 141`，
  内含 `\x1b[?1049h` 与 `\x1b[?1049l`。


**编译结束**: 2026-09-25 19:20
**最终状态**: built
