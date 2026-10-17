# 知识候选台账 + 七轴查重 + 路径判定 — dict 1.13.3

## 关键前提：与仓内既有 dictd/1.13.3 为同一上游

本任务 lib="dict" 1.13.3 的上游即 SourceForge DICT 项目（tarball `dictd-1.13.3.tar.gz`，
SHA-256 `192129df...`），与仓内既有归档 `archives/d/dictd/1.13.3/`（commit 965177cc75，
【知识库扩展】feat(dictd): 1.13.3 适配鸿蒙PC，2026-09-10 合入）**完全相同**：
同一上游 URL、同一版本、同一 SHa-E 校验、同一构建产物集（dict/dictd/dictzip/dictfmt/colorit/dictl 等）。
因此本任务适配知识与本仓 dictd 先例知识构成同源重复，查重必须显式列出该先例关系。

## 知识候选逐项（非噪声）

### C1: libmaa 无仓内 Conan recipe → recipe 内 vendored 静态构建（BSD make/mkc 语义）
- 真实错误：dict configure 硬查 `-lmaa`（`AC_CHECK_LIB(maa, maa_shutdown)` → AC_MSG_ERROR）；
  ohpcd registry 无 libmaa recipe；系统无 libmaa。
- 根因：上游 dictd 硬依赖 libmaa（同 SourceForge 项目配套库），仓内无其 Conan 配方。
- 修复：conanfile source() 拉取官方 libmaa-1.4.7 归档（SHA256 固定于 conandata.yml），build()
  中直接用 clang 编译 maa/*.c（命令行提供 mkc 特性宏 `-DSIZEOF_LONG=8
  -DHAVE_HEADER_SYS_RESOURCE_H=1`，arggram.c 用 `awk -f arggram2c` 预生成），llvm-ar 归档为
  libmaa.a，dict 通过 `-L maa-build -lmaa` 链接。**timer.c 必须保留**（maa.c 引用 tim_* 符号，
  排除会链接失败；1.4.7 旧笔记"排除 bit.c/timer.c"为缺宏误诊，已在 dictd 先例纠正）。
- 验证：conan create 干净构建通过（G2 PASS，conan-create.log）；本机 configure/make 亦通过。
- 适用范围：任何硬依赖无配方库（尤其 BSD make/mkc 构建的 vendored 库）的 autotools 包。
- 四范围查重：正式知识 = E277（vendored 依赖 build-to-staging，autotools 通用模式，部分覆盖）；
  图谱 = 无 libmaa/mkc 具体条目；草稿 = 无同 stem 草稿；
  **仓内 dictd 先例 notes.md/manifest 已完整记载同一方案（含误诊纠正）→ 已有条目**。

### C2: config.guess/config.sub 2021 版不识别 OHOS → 手工补丁加 HarmonyOS 分支
- 真实错误：`./config.guess: unable to guess system type; configure: error: cannot guess build type`。
- 根因：2021-06-03 版 GNU config 脚本无 `aarch64:HarmonyOS` / ohos 分支。
- 修复：patches/0001-config.guess.patch（aarch64:HarmonyOS → aarch64-unknown-linux-gnu）、
  0002-config.sub.patch（ohos 识别），与 dictd 先例同款（全仓 dialog 等通用模式）。
- 验证：patch 应用到 pristine 上游源码（dry-run 通过），conan create 干净构建通过。
- 适用范围：所有捆绑 2021 版 config.guess/sub 的 autotools 包。
- 四范围查重：正式知识 = E072（config.sub invalid triplet ohos）；草稿 = DRAFT-E564
  （old-style config.guess OHOS 补丁换锚点）→ 已覆盖。

### C3: HMDFS 上 config.status 临时目录 Permission denied → tmpfs 构建目录
- 真实错误：`config.status: can't create ./confOGoOgM/subs1.awk: Permission denied`
  （umask 077 + HMDFS setgid 语义）。
- 根因：HMDFS 目录权限位不保留 POSIX 语义，mktemp/umask 077 临时目录不可写（E011 类）。
- 修复：构建移至 `/data/storage/el2/base` tmpfs（真实保留权限），TMPDIR/TMP/TEMP 指向
  tmpfs 下 0700 目录；conanfile build() 用 `_prepare_ohos_workdir` 复制到 tmpfs 构建。
- 验证：configure/make/conan create 全部通过。
- 适用范围：所有 autotools 包在 HMDFS 上的 configure/config.status 阶段。
- 四范围查重：正式知识 = E011/E052/E060/E110/E112/E114/E118/E125/E126/E129（HMDFS
  config.status 临时目录族）→ 完全覆盖。

### C4: AC_PROG_LEX(yywrap) 无 -lfl 时把 LEX 降级为 ':' → make 前预生成 scanner
- 真实错误：`make: [Makefile:174: servscan.c] Error 1`（LEX=: 静默不生成 lex.yy.c）。
- 根因：autoconf AC_PROG_LEX 找不到 yywrap 提供库（libfl 缺失）时 LEX=':'；上游
  scanners 自带 yywrap，本可工作。
- 修复：conanfile `_pregenerate_scanners()` 按上游命令行预生成 servscan.c/servparse.c/
  clientscan.c/clientparse.h（flex + bison -tdv）。
- 验证：make 全绿，make test 47/47。
- 适用范围：所有 flex/bison scanner 且无 libfl 依赖链的 autotools 包。
- 四范围查重：草稿 = DRAFT-autotools-ac-prog-lex-demotes-lex-when-libfl-unlinkable
  → 已覆盖。

### C5: 设备 bash 在 HMDFS 启动 getcwd 失败 → run 命令 cd 前缀 + CONFIG_SHELL=/bin/sh
- 真实错误：bash 启动报 shell-init getcwd 错误 / libtool 重 exec 失败。
- 根因：OHOS hnp bash 在 HMDFS 路径 getcwd() 失败（errno 随机）；libtool 重 exec 需
  有效工作目录。
- 修复：所有 self.run 以 `cd '<workdir>' &&` 前缀重建工作目录；configure 用 bash +
  export PWD，make/libtool 用 CONFIG_SHELL=/bin/sh SHELL=/bin/sh；构建/测试放 tmpfs。
- 验证：conan create + test_package 全绿。
- 适用范围：所有在 OHOS HMDFS 上跑 conan 自定义 run 命令的配方。
- 四范围查重：草稿 = DRAFT-6487-classads-configshell-hmdfs-getcwd、
  DRAFT-E551-ohos-conan-configshell-bash-libtool-escaping → 已覆盖。

### C6: upstream 测试入口是 `make test`（非 make check），server 用例走 dictd --stdin2stdout
- 真实错误：`make check` 无此目标；测试集中在 test/dictd_test + test/dictzip_test。
- 根因：上游 Makefile.in 只有 test 目标，含 DICTFMT/DICTD/DICTZIP 三段。
- 修复：conanfile build() 内 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh make test` 实际运行；
  双口径台账 47/47（DICTFMT 21 + DICTD 17 + DICTZIP 9）。
- 验证：make test 三段全绿（conan-create.log 40 个 passed 标记 + DICTZIP 9 段）。
- 适用范围：dict/dictd 套件及类似"测试入口非 check 而是 test 脚本"的包。
- 四范围查重：仓内 dictd 先例 notes.md 已记载（make test 入口 + stdin2stdout 管道结论）
  → 已有条目；图谱无独立 E。

## 七轴查重

| 轴 | 结果 | 说明 |
|---|---|---|
| exact_duplicate | **是** | 与仓内 dictd/1.13.3 先例（同一上游同一版本）知识完全一致：C1/C2/C6 每条均已在 dictd notes.md/manifest 记载 |
| causal_duplicate | **是** | 同源：同一 tarball 的同一批 OHOS 适配问题（config.guess、libmaa、AC_PROG_LEX、getcwd、HMDFS） |
| trigger_overlap | **高** | 全部触发条件（unable to guess/Libmaa not found/LEX=:/getcwd/Permission denied）与 dictd 先例及 E011/E072 高度重叠 |
| solution_overlap | **高** | 解决方案逐字同源：patches 直接复用 dictd 先例；vendored libmaa 同方案；tmpfs/CONFIG_SHELL 同款 |
| combination_novelty | **无** | 本轮未发现 dictd 先例之外的组合性新知识 |
| boundary_novelty | **无** | 无新边界/反例超出 dictd 先例记录（如 timer.c 必须保留的纠正已在 dictd 先例完成） |
| test_migration_novelty | **部分** | 本轮新产出 dict 版双口径测试台账（47/47 枚举与映射），但测试入口与内容与 dictd 先例 make test 完全一致，非跨库新技术 |

## 关系字段

- `similar_to`: dictd/1.13.3 先例归档（archives/d/dictd/1.13.3/，commit 965177cc75）、
  E011（HMDFS temp dir）、E072（config.sub ohos）、E277（vendored 依赖构建）、
  DRAFT-E564（旧式 config.guess）、DRAFT-6487（HMDFS getcwd）、DRAFT-E551（libtool/CONFIG_SHELL）
- `caused_by`: 上游 dictd 硬依赖 libmaa（无配方）+ OHOS/HMDFS 平台语义
- `prerequisite_of`: 无（本任务不留新前置知识）
- `conflicts_with`: 无；dictd 先例"排除 bit.c/timer.c"的旧结论已被其自身纠正，本轮以
  纠正后方案（保留 timer.c）一致执行

## 路径判定

- **决定：reuse_existing（复用已有知识，路径 A）**，理由：
  1. 同一上游、同一版本、同一测试入口已在 2026-09-10 以【知识库扩展】合入仓内
     （archives/d/dictd/1.13.3/ + commit 965177cc75），六条候选全部在该先例 notes.md/
     manifest 已有记载（含 libmaa timer.c 误诊纠正）；
  2. 与正式知识图谱/草稿四范围查重后，每条候选均被既有 E 条目或既有草稿覆盖
     （E011/E072/E277、DRAFT-E564/E551/6487/ac-prog-lex），无未命中条目；
  3. 七轴中 exact/causal/solution 全重复，combination/boundary novelty 均无，
     test_migration 仅台账形式差异、无跨库新技术价值；
  4. 按规则"完整重复且无独立差异时复用原条目"，不新建 .md/.kv 草稿，不硬凑
     （改标题/换关键词凑新增被禁）。
- **路径 B 不成立**：未证明新增知识价值，回报 `reuse_existing` / `path_a_no_knowledge`。
  本任务交付物 = dict 库归档（独立 PR），知识侧完全复用 dictd 先例 + 既有图谱条目。