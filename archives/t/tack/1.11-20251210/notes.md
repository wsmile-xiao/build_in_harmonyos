# tack 1.11-20251210 适配笔记

## 编译环境
- 构建系统: autotools（发布件带**已生成的 `configure`** 与 `Makefile.in`；`configure.in` 也在，但按发布产物对待，不跑 autoreconf）
- 编译日期: 2026-09-26
- 编译器: clang 15（profile `tools.build:compiler_executables` → `/data/service/hnp/bin/clang`，Target `aarch64-unknown-linux-ohos`，musl；产物解释器实测 `/lib/ld-musl-aarch64.so.1`）
- 机器: B 机（HarmonyOS PC aarch64，8 核 / 31G）
- profile: `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同给）
- CONAN_HOME: `~/tmp/ch/home-tack`
- 状态: built（conan-verify 判决见「验证结果」节）

## 软件与构建面（读源码与实测所得）
tack（T.A.C.K.，terminfo action checker）是**交互式终端探测工具**：用 `$TERM` 对应的 terminfo
条目驱动终端、逐项检查光标寻址/颜色/控制序列，并可从探测结果**生成/校正 terminfo 条目**
（`tack -l` 落 `tack.log`、`-d` 落 `debug.log`、`-i` 进入交互初始化）。

- 一次构建只产出**一枚可执行** `tack`（实测包目录 `bin/` 恰好 1 个条目，H1 断言固定）与
  `share/man/man1/tack.1`（18322 B，H2 断言非空）；许可证 `GPL-2.0-only`。
- 硬依赖 ncurses：`--with-ncursesw` 走宽字符库。本 profile 下仓内
  `archives/n/ncurses/6.6` 是 **`shared=False`（静态）** ⇒ 产物 `DT_NEEDED` 里**没有**
  `libncursesw.so.6`（F2 断言），链接的是 conan 包内的静态归档。
  ⚠ 宿主 `~/.harmonybrew` 里存在同名 `libncursesw.so.6`，配方用
  `ac_cv_prog_NCURSES_CONFIG=` / `ac_cv_prog_ac_ct_NCURSES_CONFIG=` **清空
  `AC_CHECK_PROG` 缓存**并显式 `--with-curses-dir=<ncurses 包目录>`，
  否则 configure 会 `checking for ncursesw-config... yes` 捡到宿主副本（实测取缓存值为
  `no` 时链接行只剩 conan 包路径、产物字节 `grep -a -c harmonybrew` = 0）。
- 上游 `configure:3146` 用 `DFT_OBJ_SUBDIR=`pwd|sed -e 's:.*/::'` 推导对象路径前缀，`Makefile.in:63` 再以 `MODEL = ../@DFT_OBJ_SUBDIR@` 消费它
  ⇒ **必须 in-tree 构建**：`layout()` 把 `source`/`build` 都指向 `src`，
  `generators` 单独放 `build-generators`。
- 上游**没有自动化测试**：`Makefile.in:211-212` 的 `check:` 目标体就是
  `@echo "** no self-test available"`（跑 `make check` 只会打印这一行）。
- 运行期语义（消费者断言的依据，全部实测）：
  `tack -V` 打印 `tack version 1.11 (20251210)` 后 `ExitProgram(EXIT_FAILURE)` ⇒ **退出码 1**；
  非法选项走 `main()` 的 `default:` 分支打 usage 后 `ExitProgram(EXIT_SUCCESS)` ⇒ **退出码 0**；
  无 `$TERM` 无参数 → `no useful value found for $TERM`，rc=1；
  两个位置参数 → usage，rc=1；未知终端名且 terminfo 可达 → `listed as generic`，rc=1。
  ⚠ 这两个"上游自相矛盾的退出码"是**上游行为**，本包不改，只把它钉成断言（A1/B1），
  免得后来人以为是适配引入的回归。

## OHOS 适配点（六条，全部实测命中）
1. **E160 / E007（三元组）**：随包 `config.guess`（2025-07-10）没有 `HarmonyOS` 分支 ⇒
   `configure: error: cannot guess build type`。处方＝在**起草期**用仓内
   `scripts/patch-autotools-ohos.pl` 生成成对随包补丁：
   `patches/0001-config.guess.patch`（加 `*:HarmonyOS:*:*)` → `aarch64-unknown-linux-ohos`）
   + `patches/0002-config.sub.patch`（把 `ohos-linux` 归一为 `linux-ohos`；**本包属防御性配套件**，实测该分支未被命中：`ohos-linux` 打补丁前后均 rc=1、实际使用的 `aarch64-unknown-linux-ohos` 打补丁前后均 rc=0），
   由 `export_conandata_patches()` + `apply_conandata_patches()` 应用。
   两处细节：① 去掉了 helper 的 `__OHOS__` LIBC 探测 hunk（**PF5 禁止补丁新增行出现
   `__OHOS__`**，且 HarmonyOS 分支根本不读 `LIBC`）；② ⛔ 未按某些做法塞
   `--build/--host`（`autotools-patterns #0` 与 E007 明令禁止：会被判交叉编译，
   `AC_RUN_IFELSE` 类探测静默跳过）。
2. **E011 / E114**：`build()` 里把 `configure` 的 `umask 077` 就地改写为 `umask 022`
   （实测命中并打印 `UMASK077_RELAXED hits=…`；命中数为 0 时打 warning 不静默）。
3. **E386**：profile 注入的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在 HMDFS 上
   `getcwd()` 失败而 configure 会用它 re-exec 自身 ⇒ 起手即死。处方＝所有命令前缀
   `env -u CONFIG_SHELL SHELL=/bin/sh`，且**与 configure/make 在同一条 shell 命令行里**。
4. **E467 同族**：`AutotoolsDeps` 生成的 `$LIBS` 会让最早的"能否运行 C 程序"探测链接依赖闭包；
   本包 ncurses 为静态 ⇒ 实测未复现该故障，仍按 wmcore/lft/mpop 的同一形状保留
   `env -u CONFIG_SHELL` 单命令形态（未额外内联 `LD_LIBRARY_PATH`，因为没有共享依赖闭包可指）。
5. **依赖的 run 传播（本次唯一的真实返工）**：`tack` 运行期需要 ncurses 包内的 terminfo 数据库，
   而 ncurses 的 `package_info()` 是用 `runenv_info.define_path("TERMINFO"/"TERMINFO_DIRS")`
   声明的。**第 2 轮实测**：消费者测试里 `E2` 失败，
   无 `TERMINFO` 时 tack 报 `The terminal database could not be found`；
   手工 `TERMINFO=<ncurses 包>/share/terminfo` 时同一命令报 `listed as generic`
   ⇒ 缺陷在**环境传播**而不是产物。根因：ncurses 在本 profile 下 `shared=False` ⇒
   Conan 2 默认不给静态库传 run 信息 ⇒ 它的 `runenv_info` 不进入消费者运行环境。
   正解＝`self.requires("ncurses/6.6", run=True)`（与本仓既有 6+ 枚 `run=True` 配方同形；
   机制同族先例见 knowledge/drafts 的 `DRAFT-E568-mdp-ohos-musl-terminfo-path`、
   `DRAFT-E5xx-terminfo-database-bundle`）。改完第 3 轮 21/21 全绿。
6. **宿主前缀防漏（G1/G2 断言）**：`Makefile.in`/`configure` 内 `/usr/local` 出现 18 次，
   因此安装走 `--prefix=/` + `DESTDIR=<package_folder>`，并对**产物字节**断言
   `harmonybrew` 计数 0、二进制 + man 页里 `/usr/local` 计数 0（实测均为 0）。

## 消费者测试口径（赛道二：真实执行、断言决定退出码）
- 载体：`test_package/test.sh`（POSIX sh，OHOS 上是 toybox ash），由
  `test_package/conanfile.py::test()` 以 `self.run(..., env="conanrun")` 调起；
  每条 `gate` 打 `ok <编号>` 或 `FAIL <编号>` 后 `exit 1` ⇒ 断言直接决定退出码。
- 分层：A 版本横幅（3）/ B 非法选项（2）/ C 无 `$TERM`（2）/ D 多参数（2）/
  E terminfo 可达（2）/ F ELF 结构（AArch64、DT_NEEDED 不含 ncursesw、含 libc.so、
  裸 soname、musl 解释器、`.codesign` 段数）（6）/ G 宿主前缀泄漏（2）/ H 产物落位（2）。
- **自签边界**：OHOS 对未签 ELF 直接 exec 返回 `Operation not permitted`，且 **CI 不给产物签名**，
  所以 `test()` 先把包内 ELF 复制到**归档树外**临时目录、`llvm-objcopy --remove-section .codesign`
  去旧签、`binary-sign-tool sign -selfSign 1` 重签，再对**同一枚产物**跑断言，
  `finally` 删临时目录；F6 因此按分支判定（OHOS 期望 1 段、非 OHOS 期望 0 段）。
- 两个口径（都可复算，写在 `test_package/MANIFEST.yml`）：
  - 用例数（一次运行实际打印的检查点）= **21**；复算
    `grep -c '^ok ' reports/conan-create.log`
  - 判定表达式静态数 = **22**（F6 写成 OHOS/非 OHOS 互斥双分支，单次运行只判一次）；复算
    `grep -cE '^[[:space:]]*gate \$\(' test_package/test.sh`
- 实测：`consumer assertions passed: 21/21` 原文在 `reports/conan-create.log:123`（同一判决在 `reports/w3-local-ci.log:410` 也有一条）；逐条 21 行 `ok` 为 `:102`–`:122`。**0 条 skipped**
  - `log_sha256`（本窗在构建主机侧实算，`sha256sum`）：`reports/w3-local-ci.log` = `f8ff99acb34ff4bb898503d719e142b11721faa24ed7bd8ca0559f75753d6df8`、`reports/conan-create.log` = `d737b6c24b8dacaedc0e178234d9ac2b1f8f46e0a1eb81288254f913bd953421`；两份日志被仓根 .gitignore 的 reports/ 规则排除、不随 PR 入库，故对外以这两个哈希为锚
  ——下面这条能力面**没有做成断言**，故不进分母也不进通过数。
- ⚠ 能力面边界（如实声明，不伪装）：tack 的**交互式主循环**（真实用途：探测终端并重建
  terminfo 条目）在无头构建主机上不可无人值守运行。实测
  `timeout 20 tack vt100 < /dev/null` → **rc=124**，期间 stdout 累计写了 **89440575 字节**
  （含 `Using terminfo from: <ncurses 包>/share/terminfo/./v/vt100`、`Terminal reset (rs2)`），
  stderr 为空；不加 timeout 的一次累计 CPU 9 分 32 秒仍不退出。
  ⇒ "真探测一台终端"这一档能力**未验证**，本包只证明"能加载、能解析参数、能读到 terminfo 库、
  产物洁净且签名合规"。


## 路径与知识声明（与 PR 正文逐字同源，B 判定=hit）

- **适配路径**：路径 A（基础适配）＋ 知识库命中复用（无新增知识条目）
- **使用知识库**：`openharmony-compile-agent`（本 worktree 根 SKILL.md 及其路由的 KNOW_YOUR_WHY.md / CONTRIBUTING.md / 阶段文档）；`scripts/ohc-run.py recipe-search tack` 在重建后的 6174 条 catalog 里**无同名底稿**，取同族先例 `archives/g/gtypist/2.10.1`、`archives/l/luit/20250912`、`archives/d/dialog/1.3-20240307`；命中并复用既有处方的条目（每条都先读原文标题与处方再采纳）：`E160`＋`E007`（随包 `config.guess` 不识别 `uname -s = HarmonyOS` ⇒ `configure: error: cannot guess build type`；处方＝用仓内 `scripts/patch-autotools-ohos.pl` 成对打 `config.guess`/`config.sub`，并明令禁止用 `--build/--host` 绕过——那会被判成交叉编译、`AC_RUN_IFELSE` 类探测静默跳过）、`E011/E114`（`umask 077` 建的 scratch 在 HMDFS 回读丢检索位）、`E386`（profile 注入的 `CONFIG_SHELL` 指向在 HMDFS 上 `getcwd()` 失败的 HNP bash，configure 会用它 re-exec 自身）、`E467` 同族（`AutotoolsDeps` 注入 `$LIBS` 影响最早的运行探测；本包依赖为静态故未复现，仍保持同一命令形态）；终端类程序的 terminfo 运行期路径一族已有 `knowledge/drafts/DRAFT-E568-mdp-ohos-musl-terminfo-path`、`DRAFT-E5xx-terminfo-database-bundle` 覆盖，本包按其口径处理。
- **知识库扩展**：无新增条目。本包唯一的新形态候选是"静态依赖（`shared=False`）默认不向消费者传递 run 信息 ⇒ 依赖包用 `runenv_info` 声明的 `TERMINFO` 丢失"，但 `requires(..., run=True)` 是 Conan 2 通用 trait、仓内已有 6 处以上先例，且 terminfo 运行期数据面已由上述既有草稿覆盖 ⇒ 判 `hit` 不升 `create`（判据逐条见 `archives/t/tack/1.11-20251210/notes.md` 第 5 条适配点）。
- **关联 Issue**：无（B 判定=hit，本 PR 不携带 `knowledge/drafts/` 成对草稿、不建知识库扩展 Issue）

## 已知限制 / 未覆盖
1. 交互式终端探测与 terminfo 条目重建未做端到端验证（见上一节实测数据）：需要真实终端设备。
2. `tack -d`/`-l` 会在工作目录落 `debug.log`/`tack.log`：测试改在临时目录里跑，
   因此**不验证**这两个文件的内容正确性，只验证不落进归档树。
3. 上游退出码语义本身不一致（`-V` 返 1、非法选项返 0），本包按上游原样断言，未修正。
4. ⚠ **货源 URL 是滚动的**：invisible-island.net 不为 tack 提供版本化文件名
   （`/archives/tack/`、`/archives/ncurses/tack/`、`/datafiles/current/tack-1.11-20251210.tgz`
   等 6 个候选全 404；`/datafiles/release/tack.tar.gz` 是同位滚动旧快照 PATCH=20250503）。
   ⇒ 若日后上游发新件导致 `sha256` 失配或解包后 `tack.h` 的 `PATCH_VERSION` 不再是
   `20251210`，**处置是重取哈希**，绝不改写版本串（版本串必须与任务号 11005、
   归档目录、分支名保持一致）。作者 GitHub 快照仓 `ThomasDickey/tack-snapshots` 虽有 tag
   `t20251210`，但 git-archive 出的件不含生成的 `configure`，需要 autoreconf，
   而 B 机 `automake`/`perl` 环境已损坏（见主理-62 备注）⇒ 不取。
5. TLS/网络面无关：tack 不联网（探测本机终端），故本包不声明任何网络依赖。
---

**编译结束**: 2026-09-26 11:03
**最终状态**: built
