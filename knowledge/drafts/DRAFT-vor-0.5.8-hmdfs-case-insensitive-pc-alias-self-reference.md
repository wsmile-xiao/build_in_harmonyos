# DRAFT: HMDFS 大小写不敏感使仅大小写不同的 pkg-config 别名 .pc 覆盖真身，别名自引用把 --cflags/--libs 静默清空

- **草稿 ID**: `DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference`
- **来源**: vor 0.5.8 适配 run（任务号 11745；B 机 HarmonyOS PC aarch64，2026-09-27；分支 `feat/vor-0.5.8`）
  - 提交号按「首落 / 最后改动」分列，**别拿一枚去取全部**（本分支 `48d9cee684..HEAD` 共 6 枚；读数出自
`git ls-files` + `git log --diff-filter=A` 复算）：归档骨架（`conanfile.py`/`conandata.yml`/版本级
`manifest.yaml`/`notes.md`/`test_package` 三件/`commands.json`）首落 `ffe90f7859`；HMDFS 两处构建规避
= `bea346001d`；配方与 `test_package` 定稿 = `2ecf0e8b16`；版本级 `manifest.yaml` 与 notes 收口 =
`6efd5d5837`；**本草稿两件（.kv/.md）首次落盘 = `0226063a7b`**（原先只写 `6efd5d5837`，按它取不到这两件）；
**`reports/` 五件（含本条引用的 `failure-state-evidence.md` 与 `conan-create.log`）直到整改提交
`248c10f9ae` 才被 `add -f` 收进版本库**——它们此前被 `.gitignore` 的 `reports/` 规则挡住，
按任何更早的提交号都取不到。（随 PR 的 reports 本窗 z75z 现算 = **10 枚** = 上述 5 枚 + 第 5 轮 W4 判决件 `z75f-audit-result.json`、`z75f-w4-report.log` + 第 6 轮 W4 判决件 `z75q-audit-result.json`、`z75q-w4-report.log` + PF7 后半段取证件 `pf7-source-equivalence-evidence.md`；本条引用的两件仍属前 5 枚，取证据照旧认 `248c10f9ae`。）
- **状态**: DRAFT（随 vor feat 分支交付，待主编/AI 审核提升为 E 条目）
- **配套文件**: `knowledge/drafts/DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference.kv`（同 stem 配对）
- **申报域**: 平台文件系统语义 × 依赖元数据解析（platform / pkg-config）｜分层 **L1**（HMDFS 大小写不敏感是平台属性，复发面由平台保证；配方侧一行改写即可规避）

## 问题现象

编译阶段全过，链接阶段才失败：

```
ld.lld: error: undefined symbol: IMG_Load
ld.lld: error: undefined symbol: Mix_OpenAudio / Mix_LoadMUS / Mix_LoadWAV_RW / Mix_PlayChannelTimed
```

往回追，链接行里 `-lSDL_image`、`-lSDL_mixer` **根本不存在**，只剩一串 `-L`；`config.log` 里

```
pkg_cv_SDL_IMAGE_CFLAGS=''
pkg_cv_SDL_IMAGE_LIBS=''
pkg_cv_SDL_MIXER_CFLAGS=''
pkg_cv_SDL_MIXER_LIBS=''
```

而 `pkg_cv_SDL_CFLAGS` / `pkg_cv_SDL_LIBS` 有值。与此同时 configure 的输出是

```
checking for SDL_IMAGE... yes
```

即**依赖检查报 yes、取到的值却是空**——这是本条最难自证清白的地方：所有静态门禁（preflight、
`--exists`、configure 退出码）全绿，失败被推迟到链接期。

## 根因

三条规则叠起来才成立，缺一即不复发：

1. **pkg-config 按文件名找模块，且大小写敏感。** 上游 `configure.ac:16` 写
   `PKG_CHECK_MODULES([SDL_IMAGE], [SDL_image >= 1.2])`（实物见
   `/storage/Users/currentUser/tmp/ch/home-vor/p/voredd60360bd865/s/configure.ac:15-18`），
   于是要求 `SDL_image.pc`；而 conan 的 `PkgConfigDeps` 只产出 `sdl_image.pc`。
2. **HMDFS 大小写不敏感。** `SDL_image.pc` 与 `sdl_image.pc` 不是两个文件，而是**同一 inode、
   同一目录项**：实测 `stat -c '%i'` 两名为同一号，`ls -1` 只列出**先创建**的那个名字。
   于是最初那版"给上游拼写补一个只写 `Requires: sdl_image` 的前转桩"（在 ext4/CI 容器上完全无害）
   在 HMDFS 上**把真身整份覆盖**，覆盖后目录里只剩那个桩。
3. **桩的 `Requires` 指向的正是被自己覆盖掉的名字。** pkg-config 于是自引用：

   ```
   Searching for 'sdl_image' requirement 'sdl_image'
   Package sdl_image already in requires chain, skipping
   ```

   把自身从依赖链剔除后，`--cflags` 与 `--libs` 返回**空串**，而 `--exists` 仍返回 0
   （文件确实在位）⇒ configure 的 "yes" 是假绿。

选择性症状也因此解释得通：`sdl` 与 `sdl12-compat` 拼写本不相同、不成对 ⇒ 幸存，所以只有
image/mixer 两个缺符号。

**正解方向随根因确定**：别名既不能是前转桩，也不能指望"另建一个只差大小写的文件"
（HMDFS 上建不出来，只会覆盖真身）；必须是**读回原 `.pc` 全文后改写副本**——`Libs`/`Requires`/
`Version` 一字不动，只改 `Name`/`Description`，并按需追加头文件第二拼写的 `-I`。
这样在大小写不敏感 FS 上那个唯一 inode 承载的仍是完整可独立解析的元数据；在大小写敏感 FS 上
则产生两个各自完整的文件。**同一份代码在两种文件系统上都成立，不需要 FS 探测或平台分支。**
落地形状见 `archives/v/vor/0.5.8/conanfile.py:111-153`（别名表 `:68-72`，读全文 `:136-137`，
写目标 `:150-152`）。

## 方案空间

- **rec_*（主方案）**：`rewrite-alias-pc-from-original-content-not-case-variant-stub` —
  生成器目录内读回原 `.pc` 内容、改写 `Name`/`Description`（本包另加 `-I<inc>/SDL` 与 `-I<inc>`
  两种头文件拼写，因为 `sdl_image`/`sdl_mixer` 把头放在 `include/SDL/` 而 `cpp_info.includedirs`
  是 `include`），整体写到上游拼写的文件名。**读全文与写目标必须分两步**：在 HMDFS 上源与目标是
  同一 inode，无临时介质的原地重定向会先把真身截成 0 字节（实测见「证据」第 3 条）。
- **fallback_1**：绕开 pkg-config，直接把 `pkg_cv_SDL_IMAGE_LIBS` 一类的 AC_CHECK 缓存变量从
  configure 命令行喂进去（criticalmass 即用此法达成同一效果）。代价：路径与静态库链手工维护、
  依赖版本一变即漂移，且不再验证配方自身的可复现性 ⇒ 仅当上游 `.pc` 内容本身有缺陷、改写无法
  自洽时才用。
- **forbid_1**：拿 `pkg-config --exists` 的返回码判成败。别名覆盖真身后它仍返回 0——假绿正是
  本机制的伪装面。判据只能是 `--cflags`/`--libs` 的实际字符串。
- **forbid_2**：把上游模块名改成全小写、重命名 `.pc` 迁就 HMDFS、或 `autoreconf` 改
  `configure.ac`。上游模块名是对外契约的一部分，改它属上游源码变更（要另立补丁与 PR 说明）；
  而且在 HMDFS 上"重命名"根本产生不了第二个文件。

## 复现与判据（正文从 `.kv` 的 `verification_cmd` 迁到这里，那个键现在只有一行命令）

**期望读数**（B 机 pkg-config 0.29.2 实测，2026-09-27；命令 = `.kv` 的 `verification_cmd` 单行）：
`A_unique_inodes=1`｜`A_dir_entries=foo.pc`（别名不产生第二个目录项）｜`A_exists_rc=0`
（假绿，configure 因此报 yes）｜`--debug` 打出「Searching for 'foo' requirement 'foo'」与
「Package foo already in requires chain, skipping」｜`A_libs=[]`；
修复态 `B_unique_inodes=1`｜`B_libs=[-lfoo_real]`｜`B_cflags=[-I/opt/inc]`｜`B_lower_libs=[-lfoo_real]`。

**三个探针坑（本条撰写与整改时实拍）**：

1. 自造的最小 `.pc` **必须带 `Description` 字段**，否则 pkg-config 0.29 会报
   「Package 'foo' has no Description: field」使 `--exists` 返回 1 —— 那是**探针缺陷**而非本机制
   （conan 生成的真身 `.pc` 一律有 `Description`；第一轮探针就踩在这里）。
2. 「already in requires chain, skipping」**单独不是判据**：传递链上的正常重访也会打印它
   （实测真身 `.pc` 集合下该行为 **9 条** = `failure-state-evidence.md:188` 的 `B_selfref_lines=9`）。
   可用判别式 = 「`Searching for 'X' requirement 'X'` 这一**同名对**」**加上**返回值为空。
3. ⚠ **inode 数与目录项计数受 HMDFS 目录状态影响，不得当判据**：同一条命令在 B 机上实测过**两种**
   读数——撰写棒用自己的私有目录 `~/tmp/uc2/z75x-vor-fix/kc-pc-alias` 连跑两次均为
   `A_unique_inodes=1 / A_dir_entries=foo.pc / A_libs=[] / B_libs=[-lfoo_real]`
   （两次输出逐字节相同，sha256 `7906fba85918cab139cbee9011dcc475a1a3d394f14233f0396266a72b1b54f4`），
   而另址（换一棵假 HOME / 换目录名）实测过 `A_unique_inodes=2 / A_dir_entries="foo.pc Foo.pc"`
   且**修复态三值全空**。**⇒ 稳定判据只有「`A_libs` 为空 + 同名对」这一条形**，
   其余读数只作现场记录。第三方按本条复算时若拿到 1/2 两种值，属预期方差，不是本条失效。
   - **整改棒（写入区 `~/tmp/uc2/z75r-vor-fix2/`）的复核**：本键的 `verification_cmd` 现已把探针目录
     改到该私有目录，用本仓解析器 `scripts/ohc/models.py:72` 的 `parse_kv_file` 取出该键得
     **41 键 / 1199 字节 / 1 行**（无续行、尾部无悬空 `-`），原样交给 sh 连跑两次，两次输出逐字节
     相同（11 行 / 284 B）、sha256 与撰写棒**同一个值** `7906fba8…`、`VC_RC=0`
     ⇒ 单行可执行成立、且"两处私有目录同一读数"是实测；逐字命令体与输出见
     `archives/v/vor/0.5.8/reports/failure-state-evidence.md` §10。

## 查重（四范围多轴）

`draft-review` 的相似面只取 `knowledge/graph/index.tsv`（540 条），**不扫 `knowledge/drafts/`**
⇒ 范围 2 为本条手工补做。

| 近邻 | 层次差（指到行号） |
|---|---|
| E193 `knowledge/doc/E193.md:14-21` / `:23-27` | 根因段只讲"仅大小写不同的文件名指向同一 inode"这一平台属性；推荐方案是 `skip-case-sensitive-tests`，说明为"检测到 HarmonyOS 就跳过大小写敏感**测试用例**"（其代码块是 test 脚本里 `continue` 掉 `case_*sensitive`）。本包不是测试失败，是**构建期**依赖元数据被清空，处方是"按原 `.pc` 内容改写副本"——该处方在 E193 全文不存在 ⇒ 根因半边重叠、**解法不覆盖** ⇒ 非 hit |
| E075 `knowledge/doc/E075.md:14-20` / `:22-34` | 根因是 `C_INCLUDE_PATH` 让 pkg-config 把 `-I` 判为系统路径而过滤（**环境变量层**，且只影响 `--cflags`），处方 unset 两个变量。本包 `--cflags` 与 `--libs` 双双为空，且 unset 后仍为空 ⇒ 症状同族、根因与处方均不同层 |
| E247 `knowledge/doc/E247.md:14-20` | 根因是 `.pc` 的 `Libs.private` **字段内容**漏写 C++ 运行时，处方往字段里补库。本包 `.pc` 字段一字未改，是整份文件被覆盖后**文件级**丢失；`--static` 在两种状态下都不是判据 |
| E004 `:17-21` / E015 `:14-18` | undefined symbol 症状族（musl BIND_NOW × dlopen / 未调 `AM_GNU_GETTEXT` 缺 `-lintl`），均无"pkg-config 元数据被覆盖"这一层 |
| `DRAFT-cmake-target-dir-hmdfs-case-collision.kv:43-54` / `:67-72` | 同平台属性，碰撞物是 CMake 的 target 派生**目录**，处方 `rename target + OUTPUT_NAME`。本包碰撞物是单个 `.pc` **文件**，且"改名"对上游模块名不成立 |
| `DRAFT-liboggz-1.1.1-hmdfs-patches-collision.kv:17-20` / `:29-30` | 同平台属性，碰撞面在 `source()` 解包（PATCHES 文件对 patches 目录）并抛 `IsADirectoryError` **显式失败**；本包发生在 `generate()` 之后、**全程零报错**，处方（`get()` 排除项）对 `.pc` 别名不适用 |
| `DRAFT-ohos-pkgconfig-name-alias.kv:31-34` 根因、`:47-51` rec（`pc-alias-copy`：`shutil.copy2` 把 `sqlite.pc` 复制成 configure 期望的 `sqlite3.pc`） | **池内与本条最近的一条**，同为"补一个 `.pc` 别名"。层次差三条：①它的名字差异是 sqlite 对 sqlite3（**拼写不同**、与大小写无关），在大小写敏感与不敏感 FS 上行为一致，不产生覆盖；②它的失败是**显式**的 `No package 'sqlite3' found`，直接卡住 configure，本包是 configure 报 yes、失败推迟到链接期；③它的处方是"整份复制、不改内容"，本条的处方增量为"⛔ 前转桩"＋"先读满再写"＋"`--exists` 假绿不可作判据"，这三点在该条全文不存在 ⇒ 仍非 hit，但必须交叉引用 |
| `DRAFT-ohos-dbus1-pc-alias.kv:32-40` 根因、`:20-23` error_signature | dbus 包 `set_property("cmake_file_name", "dbus")` ⇒ PkgConfigDeps 生成 `dbus.pc`，而 configure 查 `dbus-1.pc`。同类"拼写不同 ⇒ 显式 No package found"，别名两侧名字不成对、不涉大小写 ⇒ 非 hit |
| `DRAFT-conan-shared-pkgconfig-requires-drop.md:38-45` / `:47-61` | 同为"PkgConfigDeps 的 `.pc` `Requires` 链没有效果"，但根因是 conan 依赖图把传递依赖标 `Skipped binaries` 后由 `pkgconfigdeps` 剔除引用，处方 `transitive_headers=True`。本包依赖图完好、`Requires` 链完整，是**整份文件被同名覆盖** ⇒ 症状近、根因不同层 |

- 另做一项全库交集检查：`grep -rilE "pkg.?config" knowledge/doc/` 的命中集与
  `grep -ilE "大小写|case.insensitive"` 的交集为 **0 条** ⇒ 正式库里没有任何条目同时谈这两件事。
- **最锋利的判别式**：`grep -rilE "already in requires chain" knowledge/` 在加入本条之前命中数
  **= 0**（正式库 540 条 + 池内 2922 份件皆无）⇒ "别名自引用"这一层此前无人写过。
  池内确有 2 条"补 `.pc` 别名"的先例（`DRAFT-ohos-pkgconfig-name-alias`、
  `DRAFT-ohos-dbus1-pc-alias`），但两条都是**拼写不同**（sqlite 对 sqlite3、dbus 对 dbus-1）
  且**显式报 `No package found`**，与大小写成对覆盖 + 假绿不是同一层——见上表逐条。
- 交集全量处置（`grep -rilE "pkg.?config"` 259 份 ∩ `grep -ilE "大小写|case.insensitive"` 47 份
  = 6 份，除本条两件外另 4 件已逐一看过上下文）：
  `DRAFT-cmake-cpm-addpackage-local-package-offline.kv:68,73`（讲"conan 包名与上游名常含大小写差异、
  `find_package(X)` 对 X 大小写敏感"——作用层是 **CMake find_package/CPM 包名匹配**，不涉 `.pc`
  文件名查找，也不涉文件系统大小写不敏感；是同现象在另一层的同类，交叉引用而非近邻）、
  `DRAFT-cyrus-sasl-...md:26`（SASL 插件注册表的字符串匹配）、
  `DRAFT-vips-8.18.4.1-meson-codec-feature-pkgconfig.md:121`（`strstr` 比较 codec 名）、
  `E574-draft-3021.kv:11`（engine 的 `error_signature` 匹配忽略大小写）——
  四处的"大小写"都是**字符串比较/名字匹配**语义，与"文件系统大小写不敏感"无关 ⇒ 均不构成近邻。
- 七轴：`exact_duplicate=false`｜`causal_duplicate=false`（同平台属性、不同作用层）｜
  `trigger_overlap=true`（HMDFS 大小写不敏感）｜`solution_overlap=false`｜`combination_novelty=true`｜
  `boundary_novelty=true`｜`test_migration_novelty=false`。
- ⇒ **判定 create**。

## 证据（B 机 2026-09-27 实拍，四条独立；1–3 的逐字摘录已随 PR 附在
`archives/v/vor/0.5.8/reports/failure-state-evidence.md`，该件 §0 列了每枚来源件的绝对路径与实算 sha256）

1. **自造最小复现**（sha256 本窗复算一致）
   `/storage/Users/currentUser/tmp/uc2/z75q-vor/selfcheck-pc-alias.log`（394 B / 14 行，
   sha256 `d9c0a27e6335b5da3894478be3f6d19bacaad8c84505931302fdd3848200a3ec`）。 ⇒ **逐字摘录已随 PR 落 `archives/v/vor/0.5.8/reports/failure-state-evidence.md` §7**（该件 :200-213，来源件与 sha256 登记在同件 §0 :20）⇒ 读者先核仓内件，设备路径只是原件所在。
   ⚠ 归属先钉清楚：**这份日志不是本条 `verification_cmd` 的原样输出**，而是该探针**前一版**的输出——
   它多打了 `B_body`/`B_exists_rc`/`B_selfref_lines`/`RC` 四行、少打了 `A_dir_entries` 一行。
   实物 14 行如下（逐字）：

   ```
   A_unique_inodes=1
   A_exists_rc=0
   Searching for 'foo' requirement 'foo'
   Package foo already in requires chain, skipping
   Package foo already in requires chain, skipping
   A_libs=[]
   B_unique_inodes=1
   B_body=[Name: Foo;Description: real package;Version: 1.0;Libs: -lfoo_real;Cflags: -I/opt/inc;]
   B_exists_rc=0
   B_libs=[-lfoo_real]
   B_cflags=[-I/opt/inc]
   B_lower_libs=[-lfoo_real]
   B_selfref_lines=0
   RC=0
   ```

   当前这版 `verification_cmd`（已收成**单行可执行**）的原样输出与逐字摘录，随 PR 附在
   `archives/v/vor/0.5.8/reports/failure-state-evidence.md` **§9**（撰写棒在自己的私有目录跑：该件
   `:236-257` 是节标题与两块正文，命令体在 `:241`、输出 11 行在 `:247-257`）与 **§10**（整改棒把键里的
   探针目录换成自己的私有目录后**原样**复跑，两次输出与 §9 逐字节相同）⇒ 单行命令在两处私有目录都跑得通、
   读数一致；这两件在版本库里的首落提交 = `248c10f9ae`（此前被 `.gitignore` 的 `reports/` 规则挡住）。
   ⚠ 这条更正的意义：原先写"本条 verification_cmd 的原样输出"，读者拿 `verification_cmd` 去对
   这份日志会发现少一行 `A_dir_entries`、多四行 B_* —— 那是**版本错位**，不是读数错。

   上面「三个探针坑」里的坑 1 与坑 2 在这份 14 行日志里同样成立，一并重述：自造 `.pc` **必须带
   `Description`**，否则 pkg-config 0.29 会以 `Package 'foo' has no Description: field` 让
   `--exists` 返回 1（那是探针缺陷，不是本机制；第一轮探针就踩在这里）；并且
   `already in requires chain, skipping` **不是**自引用独有——传递链上的正常重访也打印（实测真身
   集合下 9 条），判别式是 `Searching for 'X' requirement 'X'` 这一**同名对**加上返回值为空。
2. **用 conan 真实生成集复算**（不是自造件）
   `/storage/Users/currentUser/tmp/uc2/z75q-vor/probe-real-pcset.log` ⇒ **逐字摘录已随 PR 落 `archives/v/vor/0.5.8/reports/failure-state-evidence.md` §7**（:168-192，来源登记同件 §0 :19）
   （sha256 `30498e10c05a9bff4b65e8b734b7cb46dafbaa9a24df0d9f49be1964099721e4`）：
   把上一棒留下的 8 枚 `.pc` 快照（`/storage/Users/currentUser/tmp/uc2/z75v-vor/pc-probe/`）铺满
   目录后，故障态 `A_exists_rc=0`、`Searching for 'sdl_image' requirement 'sdl_image'` 与
   `Package sdl_image already in requires chain, skipping` 齐备、`A_CFLAGS`/`A_LIBS`/`A_upper_LIBS`
   全空；改写为"按原内容复制"后 `B_upper_LIBS` 含 `-lSDL_image -lSDL-1.2 -lpng -ltiff -lz -ljpeg
   -lturbojpeg -lzstd -lwebp -lsharpyuv`，小写名同样有值。
   （⚠ 上一棒 notes §4.2 记的这条 `--debug` 实拍在其证据目录里**并没有留下日志件**，本轮是
   重新复现并落盘，两处日志即本条的一手凭据。）
3. **原地重定向的危险性**：`sed "s/^Name: foo/Name: Foo/" $d/foo.pc > $d/Foo.pc`（无临时文件）
   在 HMDFS 上得到 `C_bytes_after_inplace_redirect=0`、`C_libs=[]` ⇒ 真身被截空。
   这解释了配方为何必须先 `read()` 满到内存再打开目标（`conanfile.py:136-137` → `:150-152`），
   属正确性要求而非风格。
4. **本包最终交付读数**（构建事实，非本轮新跑）：`conan create` + `conan-verify` 由上一棒完成，
   台账见 `archives/v/vor/0.5.8/notes.md:209-241`（§7 五维账本，消费者断言
   `ASSERTIONS=25 PASSED=25 FAILED=0`）。该节自述"G0–G4 PASS，L2/L4/L5 判决 PASS 但实为跳过"，
   本条只引用其**已如实标注**的口径，不重述为"有覆盖"。

## 关系

- `caused_by`: HMDFS 大小写不敏感（E193 现象域）× pkg-config 按文件名且大小写敏感的匹配规则
- `causes`: `ld.lld: error: undefined symbol`（`IMG_Load` / `Mix_` 一族）、configure 报 yes 而 `pkg_cv_*` 取空
- `similar_to`: E193、E075、E247、E004/E015、DRAFT-ohos-pkgconfig-name-alias、
  DRAFT-ohos-dbus1-pc-alias、DRAFT-cmake-target-dir-hmdfs-case-collision、
  DRAFT-liboggz-1.1.1-hmdfs-patches-collision、DRAFT-conan-shared-pkgconfig-requires-drop
  （逐条层次差见上表，均不满足"根因与解法两条同时覆盖"的 hit 口径）
- `prerequisite_of`: 任何"上游 pkg-config 模块名与包名仅大小写不同"的包（SDL 1.2 家族、
  ZLIB/OpenSSL 拼写族）在 HMDFS 上的配方写法
- `conflicts_with`: 无
