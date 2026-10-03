# metastore 1.1.2 — 适配笔记

任务：积分赛适配｜语言 c｜构建系统 hand-written GNU Makefile｜首次适配（上游版本号直用，无 `.N` 后缀）
上游：https://github.com/przemoc/metastore（`przemoc`，"Store and restore metadata from a filesystem"，GPL-2.0-only，2018-01-06 至今无新版本）
源码：`v1.1.2` tag 归档，27816 B，sha256 `6e09b96f663665caae07cfff1a455674b2d35151c140ea9b25046b77836b2686`

---

## 0. W0 依赖发布检查（适配前第一件事）

`conan download "libbsd/*" -r=ohpcd --only-recipe` → `Found 0 pkg/version recipes matching libbsd/* in ohpcd`。
精确检索 `libbsd/0.11.2` 与 `libbsd/0.12.2` 均回 `error:system acceleration policy not enabled`（cnb.cool 加速策略闸，同轮对照 zlib rc=0）
⇒ **libbsd 未在制品仓发布**。按 W0 规程此处本应先做 libbsd 适配再回来，但本包的实际依赖面见 §1，
结论是**不需要**新制品包，故不触发依赖链。

## 1. 依赖面实测：libbsd 假依赖的真实边界（与 rdate 1.11 同族但不同结论）

台账/README 写"Requirements: Linux / GNU make / C99 compiler / **libbsd**"。逐项核到符号级：

- **唯一 libbsd 符号是 `strmode(3)`**。全树 grep `strmode` 只有一处命中 `src/metaentry.c:656`
  （`mentries_dump()` 渲染 `--dump` 的 mode 列），且**树内无任何定义** ⇒ 纯外部导入。
- 其余 string 系调用全是 ISO C：`memset/strcmp/strerror/strlen/strchr/strncmp/strcat/snprintf/strrchr/strdup/memcpy/strftime/bcmp`，
  全部由 musl 原生提供（`bcmp` 单独链接探针 rc=0）。
- **`strlcpy`/`strlcat` 根本不是依赖**。OHOS `libc.so` 上 `nm -D` 实测：
  `0000000000011d80 T strlcat` / `T strlcpy` —— musl 原生导出。Makefile 里那行 `-lbsd` 名义上伺候的
  其实就是这一对，它们根本不需要 libbsd。
- `strmode` 则**双重不可得**：`nm -D` 在 OHOS libc.so 上查无此符号；`<bsd/string.h>` 头文件也不存在
  （`fatal error: 'bsd/string.h' file not found`，未打补丁时 `metaentry.o` 第一个就编译失败）。

⇒ 依赖面 = **1 个符号**。为一个格式化函数去适配发布整个 libbsd 兼容库不经济（R41 口径的"换个机器能否解决"：
能，但代价与收益完全不成比例）。既有工艺里已有正解：**树内 shim**（rdate 1.11 的 `adjtime`→`adjtimex`、
OpenSSH 的 `openbsd-compat/strmode.c` 都是同一手法）。

**踩坑留档（一次假阳性，务必警惕）**：最初用 `-shared -fPIC` 链接探针测符号，得出
"musl provides strmode / strlcpy / strlcat / reallocarray 全部 RESOLVES"的错误结论。
原因：**动态库链接默认允许未定义符号**，探针根本没去 libc 找符号。改为链接**可执行文件**
（必须解析全部符号）后真相才出来：只有 `strlcpy`/`strlcat`/`arc4random`/`getopt_long`/`listxattr`/`bcmp` 解析成功，
`strmode`/`reallocarray`/`strtonum`/`explicit_bzero`/`setprogname` 全部 `undefined symbol`。
⇒ **符号存在性探针一律链可执行文件，不要链 .so**（此坑与仓库既有教训同族，建议入知识库）。

## 2. 补丁 0001：树内 strmode(3) + 摘除 -lbsd

- **守卫用 `HAVE_STRMODE` 而非平台宏**（R8 硬闸：`patches/` 里默认禁止 `__OHOS__` 之类）。
  沿用 OpenSSH `openbsd-compat/strmode.c` 的 `#ifndef HAVE_STRMODE` 惯例：真实 libc 若自带 strmode，
  `-DHAVE_STRMODE` 即可选出系统的那个。
- **逐字节对齐 libbsd/OpenBSD 行为**，含类型位（`-`/`d`/`l`/`c`/`b`/`s`/`p`/`?`）、
  九个权限位、以及 setuid(`S`/`s`)/setgid(`S`/`s`)/sticky(`T`/`t`) 的双字形分支。
- **缓冲区尺寸严丝合缝**（这是最容易写错的一处）：调用方是 `char mode[11 + 1]`，即 **12 字节**。
  BSD `strmode` 写 11 个字符（1 类型 + 9 权限 + 1 ACL 占位符）再写 `*p = '\0'`，合计正好 12 字节。
  早先误以为 libbsd 写 11 字符 + NUL = 12 字节会**恰好填满**；核对源码后确认是
  10（类型+权限）+ 1（ACL 占位符）+ 1（NUL）= 12，与 buffer 等大，无溢出。
  shim 严格按此实现，**没有**多写一个字节。
- Makefile 同步摘掉 `metastore_DLIBS += -lbsd`（连同三层 `ifeq/ifneq BSD/DragonFly/Darwin` 条件），
  原地留注释说明原因。摘掉后**一个符号都不丢**（§1 已逐个核过）。
- 补丁 0001 共 **3 个 hunk / 2 个文件**（`src/metaentry.c` 两个 hunk、`Makefile` 一个）、**3896 B**，
  `patch -p1` 干净施加（conandata `strip: 1`）。补丁 0002（4 文件 / 6 hunk）见 §2b，
  补丁 0003（1 文件 / 2 hunk）见 §2c；三者的施加顺序约束见 §2d。

## 2b. HarmonyOS 无 passwd DB 条目 → 工具静默退化为空操作（补丁 0002，**真机才发现**）

这是本包**唯一一处只有真机能暴露**的适配点，也是本 PR 最重要的一条：

- **症状（CI build #66657 真机实测）**：`getpwuid failed for ./tree: uid 20001006 not found`，
  随后 `--save` 存出空 metafile、`--compare` 无输出、`--dump` mode 列为空、`--apply` 什么也不还原。
  消费者断言 6 PASS / 23 FAIL。
- **根因**：HarmonyOS **不为应用 uid（如 20001006）建 passwd/group 条目**，`getpwuid(3)`/`getgrgid(3)`
  合法返回 NULL。上游 `mentry_create()`（`src/metaentry.c:205-213`）把它当成致命错误
  `return NULL`——**整条 metaentry 被丢弃**，而不是只丢 owner 字段。
  于是在本平台上 save/compare/dump/apply 对该进程能看到的每个文件都是空操作。
- **本地为何没发现**：本机以 root 运行，uid 0 在 `/etc/passwd` 里有条目，`xgetpwuid()` 正常返回，
  12/12 全绿。**只有当测试用户本身不在 passwd DB 里时才会暴露**——这正是「设备与 CI 语义差异」。
- **补丁 0002**：uid/gid 查不到名字时回落到**数字形式**（与 `tar(1)` 的 numeric-owner 同思路），
  并让 apply 路径反过来接受这个十进制形式，于是「A 机存的 metafile 仍能在 B 机 apply」。
  metafile 格式不变（owner/group 仍是 CSTRING，只是内容可能是数字）。
  纯 POSIX：判据是「数据库里有没有这个 id」，与平台无关，**passwd DB 完整的主机行为逐字节不变**
  （实测：uid 0 仍记为名字 `root`，只有查不到时才记 `20001006`）。
- **本地复现与验证**（用 `setpriv --reuid=20001006`，本机该 uid 同样无 passwd 条目，等价于真机条件）：
  | 补丁 | 以 uid 20001006 跑消费者套件 | 结论 |
  |---|---|---|
  | 仅 0001（= #66657 测的版本） | 6 PASS / 25 FAIL，exit=1 | **精确复现真机失败** |
  | 0001 + 0002 | **12/12 PASS，exit=0** | 修复生效 |
  | 0001 + 0002，以 root 跑 | 12/12 PASS，exit=0 | 无回归 |
  另直接验证机制：metafile 内该文件 owner/group 字段为 `20001006`（同目录下有 passwd 条目的目录仍为 `root`），
  `--apply` 把 0777 复原为 0644。

## 2c. HMDFS 拒绝 `getxattr(..., NULL, 0)` 尺寸探测 → 空操作（补丁 0003，**真机才发现**）

- **症状（CI build #66665 真机实测）**：补丁 0002 生效后 `getpwuid failed` 已消失，但换成
  `getxattr failed for ./tree: Invalid argument`，且 `--save` 只存出 **18 字节**
  —— 正好是 `MeTaSt00r3` 签名 + 8 字节版本头，即**一条记录都没有**。
  消费者断言 6 PASS / 23 FAIL，与 #66657 症状几乎一样。
- **根因**：`mentry_create()`（`src/metaentry.c`）读每个 xattr 时先做
  `getxattr(path, attr, NULL, 0)` 取尺寸——这是 POSIX 规定的标准问法，
  但 **HMDFS 对这个「NULL 缓冲区问尺寸」的形态直接回 EINVAL**，
  而 `listxattr()` 同一个文件却能正常报出属性名。
  上游随后把它当致命错误 `return NULL`，**整条 metaentry 作废**。
  于是同一个文件连 mode/mtime 都没了——而 mode/mtime 与 xattr 毫无关系。
- **补丁 0003**：① 尺寸探测改为「先问 NULL，EINVAL 就改用真实缓冲区并在 ERANGE 时翻倍增长」，
  NULL 探测降级为**建议性优化**而非前提；② 单个属性读不出来改为
  **报告并跳过**（`MSG_DEBUG` 打印是哪个属性丢失），不再中止整条记录；
  ③ 写进 metafile 的 `xattrs` 计数改为**实际读到的个数**，读不到时把三个数组释放并置 NULL。
- **纯 POSIX、无平台宏**：ERANGE 增长本就是 man page 允许的做法，NULL 探测只是被降级为可选快路径。
- **本地无法复现该 EINVAL**（WSL 的 ext4/overlayfs 接受 NULL 探测），
  但**逻辑退化路径可以在本地钉死**：0003 之前「一个属性读失败 ⇒ 整条记录丢失」，
  0003 之后「跳过该属性、其余照存」。

## 2d. 一个自己踩到的坑：conan 的补丁必须 offset 0 施加

0002 与 0003 初版都是**对原始树 diff** 的。Conan 顺序施加 conandata 补丁时
**不容忍只能靠 offset 落位的补丁**：

- 0002 初版：0001 已改写 `src/metaentry.c`（顶部删 3 行、增约 59 行）⇒ hunk 行号全错位，
  `git apply` 报 `hunk no.1 doesn't match`，conan 直接 `Failed to apply patch`。
- 0003 初版：对原始树 diff，GNU `patch` 打印 `Hunk #1 succeeded at 240 (offset 56 lines)`
  ——**本地看着是成功的**，但 conan 的 apply 同样拒绝。
  差点又交一版红 CI，是 `conan create` 抓出来的。
- **正解**：后一个补丁必须对**前序补丁已施加**的树 diff，并**断言 `--fuzz=0` + 无 offset 落位**。
  0003 生成脚本现在会显式校验基线树确实带 0001+0002 的特征，并以 `--fuzz=0` 空跑一遍三连施加。
- 顺带：本地用 `patch -p1` 手工验补丁是 **fuzz 容错**的，会掩盖这类问题；
  **只有 `conan create` 才是权威**。

## 2e. 测试自身的问题：断言了文件系统不允许的权限位（CI #66734）

0002+0003 生效后真机只剩两条红，且**都不是 metastore 的错**：

```
[5b] --apply: rc=0 file_a=-rw-r----- (want -rw-r--r--) sub/file_b=-rwxr-x--- (want -rwxr-xr-x)
[8b] strmode shim special-bit glyphs: setuid=0 setuid-noexec=0 setgid=0 sticky=0
```

- `[8]` 同一轮是 **PASS** 的：「strmode shim matches ls on 9 entries, each mode field exactly 11 bytes」——
  即 shim 与 `ls` **逐条一致**，说明 shim 本身正确。
- `--apply` 复原到的 0640 / 0750 恰好是**去掉 world 位**后的样子。
- 结论：真机文件系统（沙箱内）**不授予 other(3) 权限位，也不授予 setuid/setgid/sticky**，
  而测试把「我请求的 mode」当成「盘上的 mode」来断言。
  **这是在测文件系统的策略，不是在测 metastore。**

改法（让断言测的是 metastore 的契约，而不是文件系统的策略）：

1. `[5b]` 先 `chmod` 再 `ls -ld` **读回文件系统真正授予的 mode** 作为 `want_*`，
   断言 `--apply` 复原的正是这个 `want_*`（metastore 的契约就是「复原所记录的 mode」）；
   并要求中间态确实与 `want_*` 不同，否则整体 SKIP（没有可复原的差异就无话可测）。
2. `[8b]` 四个特殊位字形逐个先确认文件系统**真的授予了该位**，再断言确切字形；
   未授予的分支计入 `unverifiable` 并在结论里如实列出，不算 PASS 也不算 FAIL。

两种文件系统下的实测（本地）：
| 场景 | 结果 |
|---|---|
| ext4 风格，权限位齐全 | 12/12 PASS，4/4 特殊位分支可验证 |
| 模拟「抹掉 world 位」的受限文件系统 | 12/12 PASS，3 个特殊位分支如实标为 unverifiable |

**教训**：`chmod` 之后必须读回实际值再断言，不能拿请求值当事实。
这与 §2b/§2c 是同一个家族——**平台差异有三种面孔：编译期、运行期逻辑、以及「你以为的前提」**。

## 3. 构建与打包

- 上游是手写 Makefile，没有 configure 步骤，`make` 直接出 `bin/metastore`。
- **R33**：`CC` 从 `self.conf.get("tools.build:compiler_executables")` 读出后**显式写在 make 命令行**上，
  绝不裸用 `${CC}`（release worker 上为空 → 静默回落到 Makefile 自带的 `gcc` 默认值 → 产出 x86 宿主二进制）。
  写在命令行还顺带让 Makefile 的 `ifneq ($(origin CC),environment)` 分支不去改写它。
- `-j1`：Makefile 的 `Makefile.dep` 生成步骤是一个 `for` 循环串行调 `$(CC) -MM`，非并行安全（R9）。
- **`-D_FILE_OFFSET_BITS=64` 已在 MustHAVE_FLAGS 里**，无需额外处理 32 位 time_t 截断。
- **`METASTORE_VER` 链路**：`Makefile` 用 `$(shell version.sh)` 取版本；tarball 里没有 `.git`，
  `version.sh` 自动回退到 `grep -no '^v[0-9][^ ]*' NEWS` → `v1.1.2`（实测输出）。
  消费者断言 [2] 就是钉这条链路的，防止将来 version.sh 回退路径被改坏。
- **不走 `make install`**：上游 `install-mans`/`install-docs` 走 `cp -P --parents`，
  会把 man page 落到 `$MANDIR/man1/metastore.1` 这种多一层 `man1/` 的位置。
  改为在 `package()` 里显式 `copy()`，包布局确定：`bin/metastore`、`share/man/man1/metastore.1`、
  `share/doc/metastore/*`、`licenses/LICENSE.GPLv2`。
  上游 `DOCS` 里的 `examples/`（git hooks 示例）是使用说明而非运行期交付物，未进包，已在此声明。

## 4. 上游测试清点（R51）

| 维度 | 读数 |
|---|---|
| 上游静态注册 N_static | **0** |
| 本环境注册/执行 | 0 / 0 |
| 通过 | 0 |
| 未执行 | 0（无注册即无未执行） |
| 消费者 | **1 程序 / 9 组断言共 12 条**，12/12 PASS |

清点证据（三条独立面全为 0，故"上游确无测试"是实测结论而非省略）：
① tarball 共 **27 个条目（22 个常规文件 + 5 个目录）**，**无 `tests/` 目录**（`tar tzf | grep -c tests/` = 0）；
② Makefile 的 `.PHONY` 目标全集为 `all bins libs strip strip-bins strips-libs install install-bins
install-libs install-includes install-configs install-docs install-mans install-shares uninstall*
clean distclean dep printvars` —— **无 `check`/`test`**；
③ 全树无 ctest/pytest/meson 注册。
metastore 是纯文件系统命令行工具、不提供库 API，故无测试可移植。

## 5. 消费者断言明细（真实执行打包产物 `bin/metastore`）

| # | 断言 | 性质 |
|---|---|---|
| 1 | runenv PATH 可解析打包二进制 | 打包面 |
| 2 | `--version` == `metastore v1.1.2` | version.sh→NEWS→`-DMETASTORE_VER` 全链路 |
| 3 | 无参 → 打印 Usage 且非零退出 | CLI 契约 |
| 4 | 非法选项 `-Z` 被拒 | getopt 错误路径 |
| 4b | `--empty-dirs` 缺 `--apply` 被拒 | 上游互斥选项校验 |
| 5a | `--save` 产出非空 metafile（196 B） | 落盘产物 |
| 5b | 权限往返：改乱 mode → `--apply` 复原（用 `ls -ld` **独立**读回） | 功能 |
| 6 | mtime 往返 `--mtime`：2001 → 2020 → 2001（`date -r` 读回） | 功能 |
| 7 | `--compare` 能发现 mode 漂移 | 功能 |
| **8** | **[鸿蒙特有]** in-tree strmode shim 的 `--dump` mode 列与 `ls -ld` 逐条对拍（10 条：`-`/`d`/`l`/`p` 四类型 + setuid/setgid/sticky 分支） | 适配正确性 |
| **8b** | **[鸿蒙特有]** 特殊位字形钉死：`-rwsr-xr-x` / `-rwSr--r--` / `drwxr-sr-x` / `drwxrwxrwt` | 适配正确性 |
| **9** | **[鸿蒙特有]** `user.*` xattr 往返：setxattr → `--save` → removexattr → `--apply` 复原 | OHOS `<sys/xattr.h>` 调用链 |

断言 8/8b 是本包**最关键**的一组：libbsd 被替换掉的就是 `strmode`，只测"能跑"不足以证明替换正确。
这里让被测实现（我们的 shim）与一个**完全独立的实现**（`ls` 自己的 mode 渲染）逐条对拍，
并额外把四个特殊位字形硬编码断言，任何一个分支写错都会红。
断言 9 覆盖 metastore 的招牌能力（xattr）与 OHOS 的 xattr 系统调用面。

**能力边界（诚实声明）**：
- 断言 5/6/7 覆盖属主/属组维度中的 mode 与 mtime；**属主/属组本身未纳入断言**——
  改 chown 需要 root 且在 CI 容器里不可靠，故只验证"存/取这两个字段不崩溃"（`--save`/`--apply`/`--dump` 全程 rc=0）。
- 断言 9 若遇不支持 `user.*` xattr 的文件系统（`ENOTSUP`）或无 setfattr/python3，
  会**显式 SKIP 并打印原因**，绝不静默通过；本次实测环境支持，故 PASS。
- 跨设备语义边界：本机 WSL 下 aarch64 OHOS ELF 经 `binfmt_misc` + `qemu-aarch64` 运行，
  内核是 WSL2（`uname -r` = 6.18.33.2-microsoft-standard-WSL2），
  故 xattr/mtime 的**宿主机文件系统**语义与真机 HMDFS 不完全等同；CI 在真机 OHOS 上原生复跑。

## 6. 源码取源与哈希核验（R39）

`v1.1.2` 的 GitHub **release 只挂了签名** `metastore-1.1.2.tar.gz.asc`，tarball 本体从未上传
（`GET /repos/przemoc/metastore/releases/tags/v1.1.2` 的 assets 数组实测只有 `.asc` 一项）。
因此官方源取 **仓库 tag 归档** `archive/refs/tags/v1.1.2.tar.gz`。

**双权威交叉核验**：该归档与 Debian 上游 orig tarball
`http://deb.debian.org/debian/pool/main/m/metastore/metastore_1.1.2.orig.tar.gz`
**sha256 完全一致**（两者同为 `6e09b96f…`）——即 Debian stable/trixie/sid 打包 `metastore 1.1.2-1`
所用的上游 tarball 就是它。两条独立权威链路对同一哈希背书，E299 类「404 伪装成 HTML」风险由 sha256 硬闸兜底。
（注：nixpkgs 的 `fetchFromGitHub` 哈希 `0mb10wf…` 是 NAR 序列化哈希，与裸 tarball 哈希本就不同，不可直接比对。）

## 7. B 判定（知识库）

- **hit（E534 家族，判不新建草稿）**：「musl 缺 GNU/BSD 函数 → 自实现树内兼容层」是既有工艺，
  rdate 1.11 的 `adjtime` shim 同族，不新建同名草稿。
- **create**：`DRAFT-7C3E-metastore-1.1.2-strmode-only-libbsd-import-and-sh-symbol-probe-lies`——
  两条本包独有、可复用的知识：①「libbsd 假依赖」必须核到**符号级**（本例真依赖面是 1 个符号而非 1 个库，
  且 `-lbsd` 名义上伺候的 strlcpy/strlcat 其实是 musl 原生自带）；
  ②**符号存在性探针链可执行文件、不要链 .so**（共享库默认放行未定义符号，会把"不存在"误判成"存在"）。

**编译结束**: 2026-10-02 08:30
**最终状态**: built
