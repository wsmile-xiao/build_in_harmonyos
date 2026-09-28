# wmcube 1.0.2 适配笔记

- 构建系统：手写 GNU Makefile（`wmcube/Makefile`，另有 `Makefile.LINUX/FREEBSD/NETBSD/OPENBSD/SOLARIS` 五份同源副本）
- 编译器：clang（profile `ohos-aarch64`，`tools.build:compiler_executables` 的 `c` 键）
- 补丁：**1 枚 portability 补丁**（`patches/0001-wmgeneral-tentative-definition-display.patch`，720 B，sha256 `daa6663d0ade72012cf06f36cd9263d6db7c4e1168bdbde83825ec725bd2e3c3`）——把 `wmgeneral.h` 的头文件内 tentative definition 改为 `extern` 声明 + `wmgeneral.c` 内单一定义；**除此之外上游源码一字未改**，无平台宏（R8/PF5 干净）
- 首轮构建红旗（真实首错）：`ld.lld: error: duplicate symbol: display`（G2/conan create，VERIFY_RC=2）——见 §4 第 7 条
- 状态：见 `manifest.yaml`（`status`）与 `reports/`

---

## 1. 症状（任务进来时的待否证面）

候选行给了四条假设，本窗一手复算后**两条半为假**：

| # | 候选行原文 | 实测 | 结论 |
|---|---|---|---|
| ① | 取源用 Debian `wmcube_1.0.2.orig.tar.gz` | 官方 `https://www.dockapps.net/download/wmcube-1.0.2.tar.gz` 返回 200、`Content-Length: 56908`、sha256 `5e9f15a1…a63989`，与本地 Debian `.orig` **逐字节相同**（`cmp` 判 IDENTICAL） | **可推翻**：改用官方 https 直链，sha256 一字未动，PF7 的 Debian 命中随之消失 |
| ② | 语言 c=7 / 共 68 文件 | `tar tzf \| wc -l` = 72 条目，其中 4 个是目录 ⇒ **68 个文件**（`find -type f \| wc -l` 独立复核 = 68）；C 文件 `.c`=4（`wmcube/wmcube.c`、`wmgeneral/{list,misc,wmgeneral}.c`）、`.h`=3 ⇒ 合计 7 | **成立**（7 的口径是 `.c`+`.h`，单算 `.c` 是 4） |
| ③ | 裸 Makefile 烧 `/usr/local`、install 走 `cp`、带 `PREFIX` | `PREFIX = /usr`（**不是 /usr/local**）；`BINDIR/DOCDIR/MANDIR/OBJDIR` 全部由它派生；install 确实走 `cp -f`/`cp -p`/`cp -pr`；烧死的检索路径是 `LIBDIR = -L/usr/X11R6/lib` 与 `INCDIR = -I/usr/X11R6/share/include` | **半假**：`PREFIX`/`cp` 成立，`/usr/local` 为假 |
| ④ | 依赖 libdockapp（已归档 0.7.3）+ libx11/libxext/libxpm | Makefile 的 `LIBS = -lXpm -lXext -lX11 -lm`，**没有 `-ldockapp`**；符号面复核：`XpmCreatePixmapFromData`（libXpm）、`XShapeCombineMask`（libXext，在自带的 `wmgeneral/wmgeneral.c` 里）、其余 `X*` 核心调用（libX11）。上游把 `wmgeneral/` 六个文件随包附带 ⇒ 自己编译，不链 libdockapp | **libdockapp 为假**；libx11/libxext/libxpm 为真。本包**不需要** libdockapp，dockapp 家族里"必须先看是否自带 wmgeneral"这一刀是分水岭 |

依赖发布态（W0，全部用**空缓存 CONAN_HOME** 实测，避免 `Skip recipe ... already in cache` 的 rc=0 假成功）：

```
libxpm/3.5.17     → Downloading recipe …   + ref#rrev - Download (ohpcd)  → Package installed
libxext/6.4.0     → + ref#rrev - Download (ohpcd)  → Package installed
libxext/6.4.0.1   → + ref#rrev - Download (ohpcd)  → Package installed
libx11/6.4.0      → + ref#rrev - Cache/Download    → Install finished successfully
xorgproto/2025.1  → + ref#rrev - Cache/Download    → Install finished successfully
（对照：libxext/1.3.7、libxdamage/1.1.1、xorgproto/2023.2 → rc=1，
 ERROR: error:system acceleration policy not enabled —— 该错误体不作为“未发布”判据）
```
全部命令均带 `--build=never -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`，即 **OHOS 二进制包实物可得**，不只是 recipe 存在（libxmu/1.3.1 型陷阱在本包不成立）。

## 2. 根因（这个包真正难在哪）

Makefile 里只有 **5 个变量被赋值**：`CC`、`CFLAGS`、`LIBDIR`、`INCDIR`、`LIBS`（外加 `OS`、`PREFIX`、`OBJS` 等非检索路径类）。而两条编译/链接规则长这样：

```make
.c.o:
	$(CC) $(OS) $(CPPFLAGS) $(CFLAGS) $(INCDIR) -c $< -o $*.o

wmcube: $(OBJS)
	$(CC) $(LDFLAGS) -o wmcube $^ -lXext $(LIBDIR) $(LIBS)
```

⇒ `CPPFLAGS` 与 `LDFLAGS` **被使用但从未赋值**。这在 make 里意味着两件事：

1. 它们从**环境**继承（make 只有在 makefile 里没有赋值时才让环境变量成为变量值），所以 Conan `conanbuild` 环境里的 `-I…/-L…` 能直接进到编译和链接命令；
2. `$(LDFLAGS)` 展开在 `-lXext` **之前**，而 `-lXext` 又写在 `$(LIBDIR)` 之前 —— 若按常规做法只在命令行接管 `LIBDIR`，`-lXext` 依旧在所有 `-L` 之前被处理，`libXext.so` 只会在默认目录里找。走 LDFLAGS 这条环境通道，`-L` 天然排在 `-lXext` 前面，顺序坑自动消解。

反过来，`CFLAGS` **被赋值** ⇒ 环境变量进不去；而 make 的命令行变量是**接管而非追加**（正式记录见 `knowledge/graph/E465.kv:27`，其 `forbid_1_reason` 原文为「Only a make command-line variable overrides the assignment and propagates through recursive makes」；旧稿此处误作「E568」——`knowledge/graph/E568.kv` 不存在、`knowledge/graph/index.tsv` 首列对 E568 零命中，E568 在 `knowledge/drafts/` 下被 11 个不同草稿复用为编号前缀（实测文件名含 E568 者 22 个，其中以 ^E568 开头的 16 个对应 8 个 stem）），一旦为了 `-O0/-O2` 去写 `CFLAGS=…`，上游的 `-Wall -O2` 会被整串替换掉（静默丢优化/告警）。所以本配方的取舍是：

- **接管**：`CC`（上游烧 `gcc`，必须换成 profile 的 clang）、`LIBDIR=`、`INCDIR=`（清空两条 `/usr/X11R6` 死路径，真实路径由 `CPPFLAGS/LDFLAGS` 提供）；
- **不接管**：`CFLAGS`（保住 `-Wall -O2`）、`LIBS`（上游的 `-lXpm -lXext -lX11 -lm` 已是完整且正确的闭包，接管反而要重抄一遍、易漏）。

## 3. 最小复现

```sh
# 复现 A：PREFIX 与 LIBS 实况（否证候选行 ③④）
tar xzf wmcube_1.0.2.orig.tar.gz
sed -n '1,25p' wmcube-1.0.2/wmcube/Makefile      # PREFIX=/usr；LIBS=-lXpm -lXext -lX11 -lm
grep -c dockapp wmcube-1.0.2/wmcube/Makefile     # 0

# 复现 B：无测试目标（R51 静态清点）
grep -nE '^[[:space:]]*[a-zA-Z_]+' wmcube-1.0.2/wmcube/Makefile | grep -E 'check|test'   # 空
tar tzf wmcube_1.0.2.orig.tar.gz | grep -cE '(^|/)(tests?)/'                             # 0

# 复现 C：依赖发布态（必须空缓存，否则拿到 already in cache 的假 rc=0）
CONAN_HOME=<空 home 且含 extensions/> conan download libxpm/3.5.17 -r=ohpcd --only-recipe
CONAN_HOME=<同上> conan install --requires=libxpm/3.5.17 --build=never -pr:h=ohos-aarch64 -pr:b=ohos-aarch64

# 复现 D：-h 是纯参数面（不经 X、不经 /proc）
#   wmcube.c: case 'h': print_help(); return 1;
#   位置在 getopt 循环内，先于 set_plugin()/init_calc_cpu()/openXwindow()
```

## 4. 已试过的失败方案（本轮真实发生，非推测）

1. **`ohc-run.py init-build wmcube 1.0.2 --url=…` → rc=1，且不是本包的问题**：
   `scripts/ohc/check_env.py:33` 的 `except Exception:` 分支里写了 `return False, str(e)`，而 `e` 未绑定 ⇒ 一旦工具探测子进程抛异常（本机 `~/usr/local/bin/automake` 的 shebang 指向 `~/usr/local/bin/perl`，子进程 exec 失败抛 `FileNotFoundError`）就 `NameError`，整条 init-build 在"[8] 环境检查"崩掉。骨架 `archives/w/wmcube/1.0.2/{manifest.yaml,notes.md}` 已建，但 `conanfile.py` 没生成、`.build-context-wmcube-1.0.2` 没写。
   ⇒ 属**框架缺陷**（框架改动须单独 PR），本窗不越权改 `scripts/`；处置：改走 `conan-init` + 手工按 makefile 形态定稿。**已入库的同类事实**：`check_env.py:33` 的 `str(e)` 使 init-build 假红（见工作区记忆条目）。
2. **`conan-init` 首稿用错模板**：init-build 崩后版本级 `manifest.yaml` 停在模板默认值（`build.system: autotools`、`{software}` 占位、`sha256: ""`），`conan-init` 据此选了 `conanfile-autotools.py.tmpl`（生成 `AutotoolsToolchain` + `autotools.configure()`，还带 `--enable-static/--disable-shared` 与 `package_type = "library"`），`conandata.yml` 的 sha256 也是 `REPLACE_WITH_ACTUAL_SHA256`。
   ⇒ 处置：`build_system` 改 `makefile`、`package_type` 改 `application`、删 `options.shared`（纯可执行文件不该有 shared 选项），并按 `templates/conanfile-makefile.py.tmpl` + coolmail/asmix 先例重写 `build()/package()`。
3. **`pipeline.py xfer` 子命令不存在**（本窗第一轮尝试 `xfer --host b` → `invalid choice`）。
   ⇒ 处置：`base64 -w0 <本地文件>` 经 `device` 通道 `echo … | base64 -d | tr -d '\r' > <设备路径>`，落地后 `file` 判无 CRLF（本仓 `archives/` 文本必须 LF，W4 会把 CRLF 判 P2）。
4. **设备通道遇非 UTF-8 输出整条崩**：读 `wmcube.c`（源码含 latin-1 字节）时 `pipeline.py cmd_device` 抛 `UnicodeDecodeError` → `TypeError: write() argument must be str, not None`。
   ⇒ 处置：设备侧输出一律经 `| iconv -c -f utf-8 -t us-ascii` 过滤。副作用要注意：**被过滤掉的中文不能当真**——本窗第一次抄 coolmail 的 `manifest.yaml` 时把 `*` 占位符当正文写了进去，随后发现并整体重写为纯 ASCII 正文。
5. **通配式判依赖发布态不可用**（R35）：`conan list` 一律未用；`libxext/1.3.7` 等三个对照包返回的 `system acceleration policy not enabled` 错误体按纪律**不判"未发布"**，只作对照组。
6. **G1 是字面量判据，"0 补丁"不等于"不写补丁钩子"**（本轮真实红牌）：`scripts/ohc/conan_verify.py:478` 起对 `conanfile.py` 做的是**字符串包含检查**，检查表里硬性含 `export_sources` 与 `apply_conandata_patches` 两项。本窗初版按"上游 0 补丁"把这两个钩子删掉 ⇒ G1 直接 FAIL（rc=2，根本没进 G2，白烧一轮）。
   另注意 `reports/conan-verify-report.md` 的**通过项与失败项共用同一句描述文本**（代码里 PASS 分支 `append(f"  * {desc}")`，FAIL 分支 `append(f"  * conanfile.py 缺少: {desc}")`，而设备通道 `iconv -t us-ascii` 会把中文一并抹成 `*`）⇒ 报告里满屏 `* name **` 看着像"全缺"，实际只有措辞更长的那两条是真失败。**判 G1 结果不能只看渲染文本，要用 rc 与条目措辞长度差**。
   ⇒ 处置：保留 `export_sources()` 里的 `export_conandata_patches(self)` 与 `build()` 首行 `apply_conandata_patches(self)`（钩子在无补丁时是 no-op，有补丁时是唯一注入口），G1 复跑。后来 G2 确实需要一枚 `0001` 补丁，这两个钩子立刻派上用场——**"按当前补丁数删钩子"是错的做法**。
7. **G2 真实首错：`ld.lld: error: duplicate symbol: display`**（第 2 轮，设备侧 `~/tmp/uc2/z64-wmcube/verify-2.log:25`（不随 PR）记 `G2: FAIL`；完整命令见 §8 的命令块，该首错原文的留存状态见下条——不要按本条旧稿去 `reports/` 里找它）
   根因（一手，非推测；本轮在 pristine 包上重算，包 sha256 同 `conandata.yml:3`）：`wmgeneral/wmgeneral.h:39` 写的是 `Display⇥⇥*display;`——**头文件内的 tentative definition**（该头文件作用域仅此一个定义点：`:25-33` 是 struct/typedef 成员、`:45-57` 全是函数原型）。**两个** TU include 该头——`wmgeneral/wmgeneral.c:52`（`#include "wmgeneral.h"`）与 `wmcube/wmcube.c:72`（`#include "../wmgeneral/wmgeneral.h"`），按 `wmcube/Makefile:22-25` 的 `OBJS` 即 `wmcube.o` 与 `../wmgeneral/wmgeneral.o` 各发一份 `display`；`wmgeneral/misc.c:22-25` 只 include `list.h`/`misc.h`、`wmgeneral/list.c:34-38` 只 include `list.h`/`stdlib.h`（`misc.h:4` 只有 `<unistd.h>`、`list.h` 无任何 include），两者不贡献副本 ⇒ 实为 **2 个 TU 而非 4 个**，而 2 份即足以在 `-fno-common` 下重复定义。1998 年的编译器按 common symbol 合并，clang 15 默认 `-fno-common` ⇒ 链接期重复定义。**失败轮日志未留存**：G2 失败轮的 `reports/conan-create.log` 已被下一轮同名 create 覆盖，现件对 `duplicate symbol` 的 `grep -c` = **0**（本行旧稿写作 `= 1`，属不实，已改）；该轮现存支撑只有设备侧 `~/tmp/uc2/z64-wmcube/verify-2.log:25` 的 `G2: FAIL` 判决行（不随 PR）与随 PR 的 `patches/0001-wmgeneral-tentative-definition-display.patch:21` 注释（本包自述，非工具读数）。唯一重名符号就是 `display`。
   知识图谱命中的是 **E540（make not found / runner-path-prepend）——错命中**：真错在链接期，与 PATH/hnp 工具无关，故 **E540 处方（EXTRA_PATH 前插）不可套用**。同族正解登记在 **E491**：`rec_priority 1` 明写 "replace tentative definitions with extern declarations plus one definition"，而 `forbid_1_pattern: (^|\s)-fcommon(\s|$)` 直接**禁止**用全局兼容旗标掩盖"声明/定义关系本身无效"，`forbid_1_consequence` 说得很清楚——重复或含糊的全局状态会以另一种链接形态复发。
   ⇒ 处置：出 `0001` portability 补丁（头文件改 `extern Display *display;`，`wmgeneral.c` 内最后一个 `#include` 之后补唯一一份 `Display *display = NULL;`），**不**接管 CFLAGS、**不**加 `-fcommon`、不引平台宏。补丁由 pristine 源码 `diff -u` 真实生成（非手写），落盘后 `sha256` 与 base64 回传件逐字节对账一致。

## 5. 最终方案

- **取源**：`https://www.dockapps.net/download/wmcube-1.0.2.tar.gz` + sha256 `5e9f15a1…a63989`（官方 https、逐字节等于 pristine `.orig`，不改 sha、不写任何镜像前缀、不用绕过旗标）。
- **依赖**：`libx11/6.4.0`、`libxext/6.4.0.1`、`libxpm/3.5.17`、`xorgproto/2025.1`，全图走 **6.4.0 track**（`libxpm/3.5.17` 配方注释明确 1.8.13 是 fatal）。
- **构建**：`make -j1 CC="<profile clang>" LIBDIR= INCDIR=`，`env="conanbuild"`, `cwd=<source>/wmcube`；依赖目录经未赋值的 `CPPFLAGS/LDFLAGS` 注入；`CFLAGS`/`LIBS` 保持上游原值。
- **打包**：不调用 `make install`（`chown root:root`、写 `/usr`、且 `cp -p wmcube.1 $(MANDIR)` 前没有 `mkdir -p $(MANDIR)`），改由 `package()` 用 `copy()` 复刻上游布局：`bin/wmcube`、`share/wmcube/*.wmc`（对应 `OBJDIR`）、`share/doc/wmcube-1.0.2/{README,CHANGES,INSTALL,THANKS}`（对应 `DOCDIR`）、`share/man/man1/wmcube.1`（对应 `MANDIR`）、`licenses/COPYING`。
- **R38**：`package_type=application` + `bindirs=["bin"]` ⇒ 软件级 `archives/w/wmcube/commands.json`（`name=wmcube`、`type=tool`、`versions."1.0.2".ref=wmcube/1.0.2`、`binary=true`）。
- **补丁**：仅 `patches/0001-wmgeneral-tentative-definition-display.patch`（portability，720 B，`strip: 1`），把 `wmgeneral.h` 的头文件内 tentative definition 改成 `extern` 声明并在 `wmgeneral.c` 保留唯一定义，解掉 `ld.lld: error: duplicate symbol: display`；取的是 `E491` 的 `rec_priority 1`，其 `forbid_1` 明禁 `-fcommon`，故**没有**接管 `CFLAGS`、**没有**加全局兼容旗标、**没有**平台宏。除此之外上游源码一字未改。
- **测试**：上游 `TESTS` 静态数实测 **0**（无任何测试目标、无 tests/ 目录，清点命令与原样输出写进 `test_package/MANIFEST.yml`）⇒ 分母不缩减、不用 `--disable-*` 凑绿；适配侧 `test_package/test.c` 16 条断言。

### 测试数字五维账本

| 维度 | 数 | 口径/来源 |
|---|---|---|
| 上游 TESTS 静态总数 | **0** | 目标枚举只有 `all:: / clean:: / install:: / uninstall:: / wmcube:`（6 份 makefile 全查）；`tar tzf` 内无 `tests/` 目录；68 文件里 4 个 `.c` 均非测试。**上游确无测试，清点证据见下** |
| 上游可执行测试数 | **0** | `make -n check` 实跑 rc=**2**、原文 `make: *** No rule to make target 'check'.  Stop.`——同一读数已整行抄进随 PR 的跟踪件：`test_package/MANIFEST.yml:22`（`upstream_check_command_evidence`）与 `archives/w/wmcube/1.0.2/manifest.yaml:84-85`（`upstream_evidence`）；设备侧原始日志 `/storage/Users/currentUser/tmp/uc2/z64-wmcube/evidence/upstream-make-check.log` 不随 PR，只作出处备忘 |
| 适配后可执行测试数 | **1** | `test_package/test.c` → `test_wmcube`，由 `test()` 经 `self.run()` 执行，**16 条断言** |
| 实测通过数 | **1**（断言 16/16） | `RESULT: PASS (16/16 assertions passed, 0 failed)`——日志 `archives/w/wmcube/1.0.2/reports/conan-create.log:175`（同轮 `Calling build()` 在 :146、RUN 命令行在 :148/:153；该日志与 `.ci-result.json` 已 `git add -f` 随 PR，行号 = 本轮 r2 重跑后实算） |
| 跳过数 | **0** | 无跳过项 |
| 失败数 | **0** | — |

链接面实物（同日志 :163-166，随 PR 可读；由 L1 harness 解析产物 `.dynamic` 得到）：
`DT_NEEDED[1] = libXext.so.6`、`DT_NEEDED[2] = libXpm.so.4`、`DT_NEEDED[3] = libX11.so.6`、`DT_NEEDED[4] = libc.so`
⇒ 上游 `LIBS = -lXpm -lXext -lX11 -lm` 三个 X 库**全部真实入链**，不是靠 `--build=never` 之外的放宽条件拿到的绿。

框架侧门禁的**如实读法**（报告原文见 `reports/conan-verify-report.md`，判决三一致：`VERIFY_RC=0` + `**Verdict**: PASS` + 各行 `✅ PASS`）：

- `## L2/L4/L5: ✅ PASS` 的正文是 **`⏭️ 跳过（无 cache 路径）`** —— 标题写 PASS、正文写跳过，两种读数都有歧义；**本账本一律按"跳过、不构成证据"计**，绝不把它当运行面或安全扫描的通过凭证。
- `## G4: ✅ PASS` 带 `⚠️ 无法找到程序包 ID`（本包是纯可执行包，无 `lib/`，G3 亦记"无 lib/ 目录（纯可执行包）"）。
- `## G0` 命中 **E490**（"Autotools helper scripts are executable programs…"，处方是 `chmod +x configure config.guess install-sh …; ./configure; make check`）并把构建系统标成 **autotools** —— **属误判式告警**：本包无 configure/config.guess/install-sh 任何一件，配方里的 `AutotoolsToolchain/AutotoolsDeps` 只是取环境通道的工具类，不产生 autotools 脚本；`make check` 在上游根本不存在（见上表 rc=2）。故 E490 处方**不套用**，也不因此改动配方。

### 运行面能力划界（不是缺陷，也不得声称可用）

wmcube 是 X11 dockapp。CI worker 无 X server，`wmcube` 无参运行会走到 `openXwindow()`（`XOpenDisplay`）并终止。本 PR 的运行面证据**只到**：
1. **链接成功** —— 产物 DT_NEEDED 含 `libX11 / libXext / libXpm`（断言 A10–A12）；
2. **可执行** —— AArch64 ELF64 可运行镜像（A1–A5）；
3. **参数/版本面** —— `-h` 的 usage 串、`CK_WMCUBE_VERSION` = `1.0.2`、`-o` 说明行均编译进镜像（A13–A15）。
**不声称渲染/取色/鼠标区可用**。另有两条已知能力边界如实记录：
- CPU 负载来自 `#if defined LINUX` 分支读 `/proc/stat`（`init_calc_cpu()` 失败即 `die()`），OHOS 上该节点的可用性本窗**未实测**（第 2 棒范围只有 build + conan-verify）；
- 默认 3D 对象目录是上游 `set_plugin()` 里的硬编码字面量 `/usr/share/wmcube/`（先 `access(path, R_OK)` 试 `-o` 传入的路径，失败才拼该前缀）⇒ 装在 Conan 包前缀下时，需 `-o <可读路径>` 才能加载 `.wmc`。**本窗未改这条硬编码**（唯一那枚 `0001` 补丁只动 `display` 符号的声明/定义形态，不碰 OBJDIR 语义），如实披露；产物内该字面量存在本身也是断言 A16 的核验项。

## 6. 候选机制台账（B 终判归主理，本窗不自判 create、不建 Issue）

| ID | 一句话机制 | 泛化面 | 查重结果（四范围计数） | 层次差：能否对齐既有条目行号 |
|---|---|---|---|---|
| M1 | **Makefile「未赋值变量」= 依赖注入的自由通道**：一个 makefile 若使用但**从不赋值** `CPPFLAGS/LDFLAGS`，则 Conan `conanbuild` 环境能把全部依赖 `-I/-L` 直接送进编译与链接规则（且 `-L` 天然排在上游硬编码 `-lXext` 之前）；判据是 `grep -E '^(CPPFLAGS\|LDFLAGS)\s*=' Makefile` 为空，而非"能不能设环境变量" | 全部"裸 Makefile + X11/图形依赖"包（本仓 Makefile 类占 21%） | `knowledge/graph/`：`CPPFLAGS` 命中 **8** 文件、`command line.*override` **0**；`knowledge/drafts/`：`CPPFLAGS` **91**、`command line.*override` **3**、`X11R6` **1**；`archives/**/notes.md`：`CPPFLAGS` **242**、`make.*CC=` **414**、`X11R6` **4**、`chown root` **5**；`经验文档/手册/07-技术速查.md`：`CPPFLAGS/LDFLAGS/接管/X11R6/chown/dockapp/X server/Xvfb` **0 命中**（**控制组** `Autotools\|CMake\|HMDFS` = **8 命中**，证明该 0 是真空而非 grep 失效） | **对不上行号**。最接近的是 `knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override.{kv,md}`（automake **per-target** `xml_la_CPPFLAGS =` 空赋值把 `AM_CPPFLAGS` 吃掉 ⇒ 解法是"命令行逐个回填"）。同一根轴的**相反杠杆**：那里变量**被（空）赋值** ⇒ 环境进不去、必须命令行接管；这里变量**根本没被赋值** ⇒ 环境进得去、反而要刻意**不**接管。该草稿的 `error_signature`/`prescan_pattern`（`^[A-Za-z_]*_(la_)?CPPFLAGS\s*=`、`AM_CPPFLAGS`、VPATH）在本包 Makefile 里**一条都不匹配**（无 automake、无 per-target、无 VPATH），故其行号与判据不可移植 ⇒ 层次对不上 |
| M2 | 上游 `make install` 含 `chown root:root` / 写 `/usr` / 拷 man 前不 `mkdir -p $(MANDIR)` ⇒ 不引 coreutils、不 patch，改在 `package()` 用 `copy()` 复刻布局 | 无安装器规范的裸 makefile 包 | `archives/**/notes.md`：`chown root` **5** 文件已有同类处置；`knowledge/drafts/`：`X11R6` **1**；`手册/07`：**0**（同 M1 的控制组口径） | **对得上**：与 `archives/c/coolmail/1.3/conanfile.py` 的 `package()`（"upstream `make install` silently skips the copy when BINDIR/MANDIR are not writable"）**同一层次、同一手法** ⇒ 属既有机制复用，本窗不据此主张新知识 |
| M3 | dockapp 家族判依赖的第二刀：先看包内是否**自带 `wmgeneral/`**（自带 ⇒ 不链 libdockapp，真实 LIBS 只有 `-lXpm -lXext -lX11`）；运行面证据在无 X server 时划到 ELF/DT_NEEDED + 编译进镜像的 usage 串为止 | X11 dock 应用族 | `knowledge/graph/`：`X server` 类 **1**、`Xvfb` **2**；`knowledge/drafts/`：`X server` **5**、`Xvfb` **5**；`archives/**/notes.md`：`X server` **10**、`Xvfb` **7**；`dockapp` 关键字在 graph/drafts/notes **均为 0**；`手册/07`：`dockapp/X server/Xvfb` **0** | 运行面划界**对得上既有先例**：`archives/c/coolmail/manifest.yaml:23` 已写「GUI 工具在设备与 CI worker 都无 X server 可用……验证用 coolmail -h 退出码与 usage 文本」（本轮复核该行对号）⇒ 属 hit 面。⚠ 旧稿此处写「E2164 同族」是**悬空裸号**，已删：`knowledge/graph/E2164.kv` 不存在、`knowledge/graph/index.tsv` 首列零命中，而 `E2164` 在 `knowledge/drafts/` 下被两个主题不同的草稿复用（`E2164-draft.kv`＝内核 release 串非数字容错、`E2164-draft-ocserv-vpn-tun-boundary.md`＝VPN/TUN 运行边界），故本行一律改按「文件 + 行号」引用。「`dockapp` 关键字全库 0 命中」是**检索面**事实，不构成机制，本窗不据此主张 create |

> 结论口径留给主理：M2/M3 我判为既有机制（可对齐先例行号）；M1 与最近邻草稿**层次对不上、判据互不匹配**，是否升 B 由主理定。草稿若需要，本窗只做过 `PRE_CREATE` 级起草，未动 `knowledge/drafts/` 之外的任何知识位。

## 7. 适用边界

- 只对"**手写 makefile** 且 `CPPFLAGS/LDFLAGS` 未被赋值"的上游成立；一旦 makefile 里出现 `CPPFLAGS = …` 或 automake 的 per-target `*_CPPFLAGS =`，本机制立即反转（见 M1 的最近邻草稿），必须走命令行回填。
- 判据要现场复核，不能凭包名族系：
  `grep -nE '^[[:space:]]*(CPPFLAGS|LDFLAGS|CFLAGS|LIBS|LIBDIR|INCDIR)[[:space:]]*[:+?]?=' Makefile`。
- 版本串纪律：任务版本、Conan 版本、归档目录、分支版本全部 = `1.0.2`（未做"归一化"）。
- 交付边界（分棒记账，不把别棒的读数当本棒自证）：第 1 棒 = build + conan-verify 绿 + commit/push 分支；第 2 棒 = `finish` 内的 W3 本地 CI（真跑，判决见 §9）；W4 独立审计与 PR 创建归主理窗。

## 8. 交付物与证据索引

### 对话 #1（2026-09-26，构建主机 B 机，worktree `~/qzy/主理-64-wmcube-1.0.2`，分支 `feat/wmcube-1.0.2`）

| 交付物 | 绝对路径（设备侧） | 说明 |
|---|---|---|
| 配方 | `/storage/Users/currentUser/qzy/主理-64-wmcube-1.0.2/archives/w/wmcube/1.0.2/conanfile.py` | 裸 makefile 形态，接管 CC/清 LIBDIR·INCDIR |
| 源声明 | `.../archives/w/wmcube/1.0.2/conandata.yml` | 官方 https 直链 + sha256 + 1 枚补丁 |
| 补丁 | `.../archives/w/wmcube/1.0.2/patches/0001-wmgeneral-tentative-definition-display.patch` | 720 B，sha256 `daa6663d…e3c3` |
| 两级 manifest | `.../archives/w/wmcube/manifest.yaml`、`.../archives/w/wmcube/1.0.2/manifest.yaml` | 软件级 + 版本级 |
| R38 声明 | `.../archives/w/wmcube/commands.json` | `name=wmcube`/`type=tool`/`versions."1.0.2".ref`/`binary=true` |
| L1 测试 | `.../archives/w/wmcube/1.0.2/test_package/{conanfile.py,test.c,MANIFEST.yml}` | 16 断言，上游静态测试数 0 的清点证据在 MANIFEST 头注释 |
| 门禁报告（框架生成，未编辑） | `.../archives/w/wmcube/1.0.2/reports/conan-verify-report.md`（被 `.gitignore:96` 忽略，**不随 PR**）、`.../reports/conan-create.log` 与 `.../.ci-result.json`（**已 `git add -f` 纳入 PR**，本文件的行号引用只指向这两件与跟踪件） | 判绿权威口径见下 |
| 逐轮 verify 日志 | `/storage/Users/currentUser/tmp/uc2/z64-wmcube/verify-<N>.log` | 每轮新名，不截断旧文件 |
| W0 发布态实测 | `/storage/Users/currentUser/tmp/uc2/z64-wmcube/logs/binprobe-*.log`、`.../w0/*.log` | `Downloading recipe` / `- Download (ohpcd)` 实物行 |

判绿口径（三一致，不认图标只认文字与 rc）：`VERIFY_RC=0` **且** 报告内 `**Verdict**: PASS` **且** G0/G1/G2/G3/G4/L2/L4/L5 各行文字判决均为 `PASS`。
本轮真实命令：

```bash
export CONAN_HOME=/storage/Users/currentUser/tmp/ch/home-wmcube-64
export SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem
export PATH=/storage/Users/currentUser/usr/local/bin:/storage/Users/currentUser/.local/bin:$PATH
cd /storage/Users/currentUser/qzy/主理-64-wmcube-1.0.2
sh /storage/Users/currentUser/tmp/uc2/gate.sh                       # GATE_PASS
bash ci/scripts/preflight_check.sh wmcube/1.0.2                     # W0
sh /storage/Users/currentUser/tmp/uc2/build-slot.sh --kind short --wait 1800 --mem 2500 -- \
  python3 scripts/ohc-run.py conan-verify wmcube 1.0.2              # G0-G4/L2/L4/L5
```

## 9. 状态

状态：built（第 3 棒整改后 r2 重跑：conan-verify 三一致——报告 `**Verdict**: PASS` + G0/G1/G2/G3/G4/L2/L4/L5 各行文字 PASS + runner rc=0，runner 日志在设备侧 `~/tmp/uc2/z64-wmcube/verify-r2a.log` 与 `runner-verify-r2.out`（不随 PR）；W3 本地 CI 已在 `finish` 内真跑并收口，判决记在随 PR 的 `.ci-result.json`：`exit_code:0`、`step:W3_local_ci`、`timestamp` 2026-09-26T04:46:07、`log_sha256` `8979feb79a3cd904…c74f12c0b` 与 `reports/w3-local-ci.log` 的 `sha256sum` 实算一致，该日志内 `[step]` 标记 48 处、`_RESULT=` 8 处（w3 日志本体不随 PR，其完整性由上面那枚 `log_sha256` 绑定），`finish` 仍只报框架侧 `step5b/step8`（与设备侧第 2 棒 `~/tmp/uc2/z64-wmcube/finish-b1.log`（不随 PR）里的同一条，非本包缺陷，无裸 `step5`）；W4 审计 r1 的 4 条 P1 已整改完毕；产物未 upload，PR 未建）
---

## 10. 路径 B 披露声明（3+2）

- **适配路径**：路径 B（配方适配 + 知识库扩展）
- **使用知识库**：`knowledge/graph/E491.kv:21`（`rec_priority 1` 那句里的「replace tentative definitions with extern declarations plus one definition」）与 `knowledge/graph/E491.kv:33-34`（`forbid_1_pattern` 明禁 `-fcommon`、`forbid_1_reason` 说明全局兼容旗标会掩盖无效声明关系）⇒ 本包的 `ld.lld: error: duplicate symbol: display` 走 `wmgeneral.h` 改 `extern` 声明 + `wmgeneral.c` 内单一定义（`patches/0001-wmgeneral-tentative-definition-display.patch`），未加 `-fcommon`、未接管 `CFLAGS`、未引平台宏；另「make 命令行变量覆盖 makefile 内赋值」这条取舍在仓内有正式记录可对齐：`knowledge/graph/E465.kv:27` 的 `forbid_1_reason` 写「Only a make command-line variable overrides the assignment」，本配方只接管 `CC`/`LIBDIR`/`INCDIR`、刻意不接管 `CFLAGS`，与该语义一致（动作见 §2 与 §5）。⚠ 更正：上一棒把后一条机制写成「E568 同族」，而 `knowledge/graph/E568.kv` 不存在、`knowledge/graph/index.tsv` 首列对 E568 零命中（E568 在 `knowledge/drafts/` 下被 11 个不同草稿复用为编号前缀（实测文件名含 E568 者 22 个，其中以 ^E568 开头的 16 个对应 8 个 stem）），已在 §2 与本包草稿改按「文件名 + 行号」引用。
- **知识库扩展**：`knowledge/drafts/DRAFT-11940-wmcube-1.0.2-makefile-unassigned-flag-channel.kv` 与同名 `.md`（裸 Makefile 的依赖注入通道判别：使用但从未赋值的 `CPPFLAGS`/`LDFLAGS` 是 `conanbuild` 环境的自由通道，已被赋值的只能靠命令行整串接管）
- **关联 Issue**：`#3435`（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3435）
---

**编译结束**: 2026-09-26 04:44
**最终状态**: built
