# DRAFT-mstpd-0.2.0-ohos-dirent-missing-versionsort-alphasort-fallback
> OHOS sysroot 的 dirent.h 不声明 GNU versionsort(3) 时，把 scandir 比较器回退为 POSIX alphasort(3) 的单库语义回退

## 问题特征（真实日志片段/标记）
- 编译期两条同错（原文逐字）：
  `ctl_main.c:452:57: error: use of undeclared identifier 'versionsort'`
  `ctl_main.c:1171:58: error: use of undeclared identifier 'versionsort'`
  随后 `make[1]: *** [Makefile:724: mstpctl-ctl_main.o] Error 1`，配方在 `build()` line 209 抛出。
- 该文件的**真实编译行本来就带 `-D_GNU_SOURCE`**（mstpd 0.2.0 / reports/conan-create.log:272，整行
  `/data/service/hnp/bin/clang -DHAVE_CONFIG_H -I. -I<build> -DNDEBUG -Os -Wall -D_REENTRANT
  -D__LINUX__ -I. -D_GNU_SOURCE -DMSTPD_PID_FILE='"/var/run/mstpd.pid"' -O3 -D__MUSL__ -MT
  mstpctl-ctl_main.o ... -c -o mstpctl-ctl_main.o ctl_main.c`）⇒ 报错与"特性宏没开"无关。
- 调用点只有两枚，且都是 `scandir()` 的第 4 参数（比较器）：
  `return scandir(SYSFS_CLASS_NET, namelist, isbridge, versionsort);`（枚举桥接口）与
  `if(0 > (res = scandir(buf, namelist, not_dot_dotdot, versionsort)))`（枚举某桥 `brif` 下的端口）。
- 全源码 grep `versionsort` 命中恰为这 2 行；上游 `configure.ac` 只有 `AC_CHECK_FUNCS(clock_gettime)`，
  **没有任何 versionsort 探测宏**可复用。

## 根因
- OHOS NDK sysroot（musl 系）的 `<dirent.h>` **根本不声明** `versionsort(3)`。三档一手证据：
  1. 对整棵 sysroot include 树 `grep -r versionsort <ohos-sdk>/native/sysroot/usr/include` 命中 **0** 次；
  2. `<dirent.h>` 里 `#if defined(_GNU_SOURCE) || defined(_BSD_SOURCE)`（40-53 行）与
     `#if defined(_LARGEFILE64_SOURCE) || defined(_GNU_SOURCE)`（55-64 行）两块**只补了**
     `getdents()`、`DT_*`/`IFTODT`/`DTTOIF` 与 `dirent64/readdir64/scandir64/alphasort64` 等别名，
     没有任何 versionsort 条目 ⇒ 打开 `_GNU_SOURCE` 也拿不到该符号；
  3. 同一组真实旗标下的最小 TU 对照（`-D_REENTRANT -D__LINUX__ -D_GNU_SOURCE -D__MUSL__ -Os -Wall`）：
     `scandir("/tmp",&l,keep,versionsort)` → rc=1 且报同一句 undeclared identifier；
     `scandir("/tmp",&l,keep,alphasort)` → rc=0、stderr 0 字节；
     `clang -dM -E` 实拍 `#define __OHOS__ 1`（守卫宏由 SDK clang 预定义，不需外挂）。
- 因此这是**平台头文件层的 GNU 扩展缺位**，不是配置探测失败，也不是链接期缺符号
  （sysroot 的 `alphasort`/`scandir` 声明与定义俱在）。

## 修复方案（rec）
1. 在两枚调用点各加 `#ifdef __OHOS__` 分支，把比较器换成 POSIX `alphasort(3)`，`#else` 分支保留
   上游 `versionsort` 不动（glibc/Linux 行为零改动）。可行性依据是签名逐字一致：
   sysroot `<dirent.h>:32-33` 的
   `int alphasort(const struct dirent **, const struct dirent **);` 与
   `int scandir(const char *, struct dirent ***, int (*)(const struct dirent *), int (*)(const struct dirent **, const struct dirent **));`
   的第四参数完全吻合（`versionsort` 在 glibc 侧也是同一签名，故这是等价换比较器而非改调用式）。
2. 落 `patches/0002-ctl-main-versionsort-alphasort-ohos.patch`（序号走 `0001-` 式规范），
   `conandata.yml` 的 `patches` 段登记 `patch_type: portability`，由 `build()` 顶部既有的
   `apply_conandata_patches(self)` 施加，不新增配方逻辑。
3. 语义边界必须写进 notes 与 PR：`scandir` 的**条目集合由第 3 参数过滤器决定**
   （`isbridge` / `not_dot_dotdot`），比较器只决定**列出次序** ⇒ 这是一次
   **排序语义降级**（版本号序 → 字典序），`mstpctl showbridge` / `showport` 的观感次序改变，
   可用性、字段与退出码不变；**不跳任何测试、不缩任何功能面**。
4. 补丁自证要走两条独立路径：toybox `patch -p1 --dry-run` rc=0 且目标文件未被改动 →
   真 apply rc=0 且产物 sha256 等于生成器期望值 → `patch -p1 -R` 反向回到原始 sha256；
   再用 conan 实际使用的 `patch_ng.fromfile(...).apply(strip=1)` 复核同一 sha
   （`--dry-run` 的 rc=0 单独不可信：续行导致 hunk 行数不符时它会假绿）。
5. 验证：`python3 scripts/ohc-run.py conan-verify mstpd 0.2.0` 的 `**Verdict**: PASS`，
   日志内 `error:` 0 次、`undeclared identifier 'versionsort'` 0 次、`undefined symbol` 0 次。

## 禁止策略
- **禁止靠 `-D_GNU_SOURCE` 硬救**（含"在源文件顶部补 `#define _GNU_SOURCE`"）：本包真实编译行本来就带
  该宏仍报同错，buildtorrent/0.9.1 的 R3 判决也一样（还多出 `_GNU_SOURCE` 重定义警告）。
  这样做的后果是编译面持续红、退回修复循环，并把平台头缺失伪装成特性宏问题。
- **禁止 `#if 0` 删掉调用面、把比较器改成 `NULL`、或加 `--disable-*` 开关凑绿**：`NULL` 比较器等于
  不排序、删调用面等于砍掉桥/端口枚举，属缩分母；次序变化也会因此不被披露。
- **禁止给 `configure`/`config.h` 加"探测 versionsort"的假探测**：上游 `configure.ac` 无该探测项，
  补一个宏也没有消费者，等于把编译期事实伪装成探测期事实。
- **禁止写成"上游不支持"**：上游代码明确使用 GNU `versionsort`，缺失在平台头一侧，
  本条是"单库语义回退 + 次序降级披露"。

## 与相近条目的边界（查重）
- **最相近的在池条目 E171**（`knowledge/graph/E171.kv:3-5` `trigger_tool: clang++|clang|gcc|g++`、
  `phase: compilation`、`error_signature: use of undeclared identifier 'euidaccess'|…`；
  `:13-16` 根因；`:21-26` rec=`euidaccess`→`eaccess` 的源码改名；`:28-31` fallback=在源文件顶部
  `#define euidaccess(path, mode) eaccess(path, mode)`）：**形状同族、机制不同层**——
  E171 的替换是**语义等价的改名**（`eaccess` 承担同一权限判定，换名不改变任何输出），
  本条的替换是**语义降级**（版本号序 → 字典序），换之前必须先证明"比较器只决定次序、
  条目集合由过滤器决定"，并把次序变化写进 PR 披露；E171 也不含"`-D_GNU_SOURCE` 不足"这一判据
  （它的错误面里该宏根本没出现）。`draft-review` 实算 E171 `score=0.39`、分项
  **`sig=0.6 / kw=0.0 / cat=0.14`**——关键词零重合，分值全由通用报错字样撑起 ⇒
  按"无可复用即不构成真重复"维持 create，并已把 E171 写进 `.kv` 的 `similar_to` 供下次人工比对。
- **E152**（`knowledge/graph/E152.kv:8` `phase: compilation`、`:10` 根因"musl 需显式包含 time.h
  并可能需要 `_GNU_SOURCE` 启用 POSIX 定时器常量"、`:18-19` rec=`add-cflags`＋
  `CFLAGS="-D_GNU_SOURCE"`）：它的**处方恰是本条 forbid_1 明令禁止依赖的那一招**。
  差别在缺口的层：E152 是"符号在头里，但被特性宏挡住"⇒ 开宏即可；
  本条是"符号在整棵 include 树里根本不存在"（grep 命中 0）⇒ 开宏无效，本包编译行已带
  `-D_GNU_SOURCE` 仍报同错。两条是同一句报错文字下的**相反结论**，不是 hit，也不该合并。
- **E500**（`knowledge/graph/E500.kv:19` 条目本体；根因由 `draft-review` 原样引为
  "OHOS musl libc 无 glibc 的 MAX_INPUT 宏; 需用 _POSIX_MAX_INPUT 兼容定义"）：
  处置是**换常量名/补兼容定义且语义不变**；本条要换的是**有可观察行为差异的函数指针**，
  多出"次序降级须披露"这一层，且 E500 不涉及特性宏是否足 ⇒ 不是 hit。
- **E077**（`knowledge/graph/E077.kv:2-11`，`trigger_tool: patchelf|strip|llvm-objcopy|binary-sign-tool`、
  `phase: post-install`、错误面 `operation not permitted|codesign|Permission denied.*ELF`）：
  属**安装后 ELF 签名/strip 层**；本条是**编译期符号声明缺失**，工具、阶段、解法三条全不重合 ⇒ 不是 hit。
- **E392**（`knowledge/graph/E392.kv:17-29`，`trigger_tool: conan|make`、`phase: source|compilation`、
  签名 `BadZipFile.*File is not a zip file|No targets specified.*No makefile found|tools\.build:compiler_executables`）：
  讲的是 raw makefile 配方的取源/字典/cwd 三陷阱；本包 conan 与 make 均正常工作，
  失败点在 C 源码可见的库符号声明 ⇒ 不同层，不是 hit。
- **`knowledge/drafts/DRAFT-buildtorrent-0.9.1-autoconf-umask-tmpdir-readonly-fix.md:19`** 原文
  已把本机制**明文划出自己的范围**：「同PR后续`versionsort回退alphasort`属OHOS SDK缺GNU符号的
  单库语义回退…均不属本条范围」⇒ 池内既无条目覆盖它、也无人在认领它。
- **E534**（`knowledge/graph/E534.kv:6` 头注「本条目验证的具体函数(gethostid/strverscmp/sigisemptyset/getusershell)未被任何已有条目覆盖」、`:13` 签名四条 `undefined symbol: …`/`call to undeclared function …`、`:28-29` rec=`compat-patch-in-missing-syscalls`（在 `libbb/missing_syscalls.c` 里以 `__attribute__((weak))` **自写实现体**））：它是本轮`grep -rln "versionsort\|alphasort\|strverscmp" knowledge/` 的命中件之一，但命中的词是**`strverscmp`（子串包含）而不是 `versionsort`** —— 该文件全文不含 `versionsort`/`alphasort` 二字（同一条 grep 只从 `strverscmp` 命中）。两层差别是实质性的：E534 的缺口在**链接期未定义符号**、解法是**新增实现体**（并靠弱符号让 glibc 强符号优先，语义不变）；本条的缺口在**编译期头文件不声明**、解法是**改用 sysroot 已声明的同族 POSIX 函数**（不新增实现，代价是排序语义降级须披露）。⇒ 不是 hit；已并列进 `.kv` 的 `similar_to` 供下次比对。
- **`knowledge/graph/index.tsv` 对 `versionsort|alphasort` 命中 0 行**（实测
  `grep -c "versionsort\|alphasort" knowledge/graph/index.tsv` = 0），
  且 `knowledge/graph/*.kv` 全文无这两个词 ⇒ 图谱空白。
- 因 `draft-review` 的相似面只取 `knowledge/graph/index.tsv`、不扫 `knowledge/drafts/`，
  上面的 drafts 手工 grep 是本条定档的前置动作，不能省。
- **本条 `draft-review` 原样读数**：质量预检 `signature=✅ root_cause=✅ rec=✅`；
  相似 TOP3 = `E171 score=0.39 (sig=0.6 kw=0.0 cat=0.14)`、
  `E152 score=0.39 (sig=0.6 kw=0.0 cat=0.14)`、`E500 score=0.37 (sig=0.6 kw=0.0 cat=0.33)`
  ——三条的关键词分项全为 **0.0**，分值只由 `sig=0.6` 的通用报错字样撑起；
  预审建议 `review-similar → E171`（灰区，**无 merge-into**），纳入决策权在人工审核。
- **判 create 的依据（三条件同时成立）**：①多包复发且解法已在仓内落地 5 处——
  `archives/b/buildtorrent/0.9.1/conanfile.py:97-138`（配方内 regex 全量替换成 alphasort）、
  `archives/a/alsa-lib/1.2.12/patches/0001-src-conf.c.patch:326` 与
  `0002-src-ucm-parser.c.patch:123`（`#define SORTFUNC versionsort64` → `alphasort64`）、
  `archives/a/alsa-utils/1.2.14/notes.md:68,112-114`（同族 `versionsort64` 排除）、
  `archives/l/libgpiod/2.0/patches/0004-tools-tools-common.c.patch:22-54`（`#if !defined(__GLIBC__)`
  自实现 strverscmp）与 `archives/l/libgpiod/2.1.3/patches/0004-versionsort-compat.patch:8,42`
  （`#ifdef __OHOS__` 守卫的**自实现兼容函数**，是同问题的另一解）；
  ②图谱零命中；③既有草稿明文不覆盖。本条的增量是把"如何判定 `_GNU_SOURCE` 不足、
  比较器与过滤器各自的职责边界、次序降级的披露口径、两条独立 apply 自证"固化成可复用判据。

## 适用判断
- 适用：上游源码把 `versionsort`（或 `versionsort64`）用作 `scandir()`/`newdir()` 比较器，
  在 OHOS 上编译期报 `use of undeclared identifier 'versionsort'`，且
  ①sysroot include 树 grep 该符号 0 命中、②该文件编译行已带 `-D_GNU_SOURCE`。
- 不适用：`undefined symbol: versionsort`（链接期缺**定义**而非缺**声明**，处置是补兼容实现体而非换比较器）；
  已声明但被特性宏挡住的平台符号（先查该宏）；排序次序被下游行为依赖的场景
  （按第一个条目挑设备一类）——那要走 fallback（自带数字感知比较器），不能按次序观感降级处理。
