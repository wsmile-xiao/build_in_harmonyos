# W4 独立审计 r2 — trompeloeil-cpp/49（审计代号 z74-trompeloeil-w4r2）

- 绑定 HEAD：`3baa923a02b95c3c2ce620f30885c0d3636a76df`，本地 == `git ls-remote origin feat/trompeloeil-cpp-49`（实测一致）；归档目录 `git status` clean
- 坐标：B 机 `~/qzy/主理-74-trompeloeil-cpp-49`，归档 `archives/t/trompeloeil-cpp/49`
- **判决：pass**（P0=0 / P1=0 / P2=1 / P3=3；r1 六条：5 条 closed、W4-05 部分残留）
- 全程只读：未 commit/push/改表/改任何 worktree 文件，未跑 build·create·verify·finish。唯一写 = 本目录判决件与 `conan export` 落的**隔离新缓存** `~/tmp/uc2/z74-trompeloeil-w4r2/home-rrev{,2}`（交付缓存 `~/tmp/ch/home-trompeloeil-cpp` 只读访问）

---

## ★头号项（新判）：RREV 与取证的一致性 —— **证据传递成立，但披露缺两级台阶（P2）**

**独立复算结果（不是采信整改方叙述）**：

| 态 | rev | 取法 |
|---|---|---|
| 绿跑（W3 判定所绑定） | `#25e761fbcb34ada2255b27369fc16c44` | `reports/w3-local-ci.log:111`，该文件由 `.ci-result.json.log_sha256=ce7cc415…` 绑定，本窗 `sha256sum` 复算逐字相等 |
| 交付（HEAD 盘上态） | `#227d4eb61c6334d5a48de5f872754bcb` | 本窗隔离 home `conan export archives/t/trompeloeil-cpp/49` 实得，**与 notes.md:169 申报逐字相同** ⇒ 整改方读数复现 |
| 对照组（盘上 gh-proxy 注入备份） | `#5b752da75d75c778d6354f4e204f9645` | 把 `~/tmp/uc2/z74-trompeloeil/conandata.yml.harness-mutated.bak` 配同一份 conanfile.py 另置目录 export ⇒ **不等于绿跑 rev** ⇒ 注入态不止一档，绿跑真正导出的是 `file://` 形态 |

**桥的承重证据（本窗从缓存实物取出，只读）**：`conan cache path trompeloeil-cpp/49#25e761fb…` ⇒ `~/tmp/ch/home-trompeloeil-cpp/p/trompebaf8eb8ebf19/e/`。
- `conanfile.py` 与交付态 **`cmp` 逐字节相同**；
- `conandata.yml` 只差**一个 hunk 14,16c14**：绿跑态两条 `file:///<worktree>/.build-cache/predl_cache/{320623c7,7cef7f42}_v49.tar.gz`，交付态第 14 行单条官方 URL；两侧 `sha256` 锚点同值 `2523571f…5593`；
- 两枚预下载件 `sha256sum` 实测均 = `2523571f…5593`，与 `probe-s8-output.txt:19/22/25` 官方 URL 三次独立取档同值。

⇒ **判定：传递成立，但只到「被编译被测试的源码字节同一」为止。** 交付态那条官方 URL 的取源动作在 B 机从未跑通（`github.com` 不可直连），CI 侧可达性仍未证明 —— 此点已在 `notes.md:69`、`:172` 与 `test-report.md:36-40` 如实披露，不是隐瞒。

**为什么仍判 P2 而不是 closed**：`notes.md:169` 断言「差这一档文件」，但**PR 里没有任何实物能证伪/证实这句话** —— 绿跑态 `file://` 那份 conandata 只活在 B 机本地缓存（他机、评审、CI 都取不到），盘上唯一注入备份还是另一档（gh-proxy）。⇒ 评审与 CI 会在同一处反复要求「你怎么证明绿跑跑的就是这份配方」，而答案现在只有一段叙述。
**必须补进正文的原文（建议落在 `notes.md:169` 之后，替换现有那句「差这一档文件」）**：

> 两枚 revision 的 recipe 实物差异已核：`conan cache path trompeloeil-cpp/49#25e761fb…` 指向 B 机缓存 `p/trompebaf8eb8ebf19/e/`，其中 `conanfile.py` 与交付态 `cmp` 逐字节相同，`conandata.yml` 仅第 14-16 行不同（绿跑态为两条 `file://…/predl_cache/{320623c7,7cef7f42}_v49.tar.gz`，交付态为第 14 行单条官方 URL），`sha256` 锚点两侧同值；两枚预下载件 `sha256sum` 实测均 = `2523571f…5593`，与官方 URL 三次独立取档（`probe-s8-output.txt:19/22/25`）同值 ⇒ 被构建与被判定的源码与交付态声明的源同一，差异仅在取源写法。⚠ 绿跑态 `conandata.yml` 的字面形态**只存在于本地缓存**，他机不可复推，故本段即为披露凭据。

**诚实性评估：合格。** `notes.md:161-167` 对「改写不自动还原」「备份件第 15 行逐字」「还原走 备份 + `git show fd547a…:… > 原路径`（⛔ checkout/restore 路径式）」三项申报与盘上一致；HEAD 树内 `conandata.yml` 的 `gh-proxy` 命中 = 0，盘上 clean。

---

## r1 六条逐条复验

### W4-01（P1 撞名）→ **closed**
`conanfile.py:201/202` = `trompeloeil-cpp` / `trompeloeil-cpp::trompeloeil-cpp`；`set_property` 全文只命中这两行，**无 `cmake_target_aliases`、无 `namespaced_targets`**（没走 alias 后门把上游名搬进 target 名）。`test_package/CMakeLists.txt:4,9` 同步。已合入包未被改动（`git show origin/main:archives/t/trompeloeil/49/conanfile.py` 仍是 190/191 上游名）。
**交集独立复算 = 0**：generators/ 实存 `trompeloeil-cpp-config.cmake`、`-config-version.cmake`、`Targets.cmake`、`-Target-release.cmake`、`-release-armv8-data.cmake` 五枚，目录内**不存在任何裸 `trompeloeil*.cmake`**；`trompeloeil-cppTargets.cmake:17` = `add_library(trompeloeil-cpp::trompeloeil-cpp INTERFACE IMPORTED)`；全目录 grep 非 -cpp 的 `trompeloeil::trompeloeil` = 0 命中 ⇒ 两包并存不再互相覆盖。绿跑日志 `w3-local-ci.log:383` 亦印 `Target declared 'trompeloeil-cpp::trompeloeil-cpp'` ⇒ 改名在绿跑之前已生效（与 rev 口径自洽）。

### W4-02（P1 申报无来源）→ **closed**
`probe-output.txt` 166 行 / `probe-s8-output.txt` 30 行 / `lsremote-mirror.txt` 50 行 / `lsremote-direct.txt` **0 字节** / `tdiff-real.txt` 0 字节。抽查 notes 引用的 **24 条行号全部逐字命中**（含 `:32 curl(28) 20001ms 0 bytes`、`:36 http=000 size=0 time=65.003883`、`:65 Failed to connect … 65472 ms`、`:66 clone_rc=128`、`:25/:28` 两次 200/336774、`:41/:42/:47` 7908 全量、`:118 tar_rc=0`、`:124 diff_rc=0`、`:125 tdiff_real_lines=0`、`:128/:129` 123/123）。
**无「已删读数」残留**：全归档扫 `2756|Empty reply|codeload.*超时|65s` 只命中 `notes.md:65`，而该行本身是「本轮不复现、已据实删除」的申报句，正文其余处不再依赖这两个数字 ⇒ 不判 P1。受影响面收窄（只 `github.com` 主机名 + git 克隆）与盘证一致。

### W4-03（P2 来源件行号）→ **closed**
主载体 `w3-local-ci.log` 实算 **435 行**、`conan-create.log` **152 行**。读数表 **9 处行号逐条抽查全中**：243=1361/604、308=1394/615、246=thread_terror RUN、250=custom_recursive_mutex RUN、251=Pass! (the program compiled)、311=c++14 `cases=68 executed=50 pass=50 fail=0 excluded=18`、312=c++20 68/68 excluded=0、404=5 断言/4 用例、并列出处 `conan-create.log:150` 同文。另抽 `notes.md:126` 判决行 6 处：23 G0 pass、51 `[OK] KC2`、65 KC pass、92 JC pass、93 JC_ERRORS=0、421 L0 pass。`test-report.md:5-8`、`MANIFEST.yml:60-63` 同批同步（435/152 与两份 sha256 逐字正确）。

### W4-04（P2 假结论）→ **closed**
「diff -rq 0 行差异」已删并改写为「当时 `gt` 不存在、18 行全是单侧 `Only in`」（`notes.md:37-48`，四点盘证 `probe-output.txt:12/:67/:93/:114-115` 互洽，并解释 18 = 15 顶层 + 3 点开头条目）。真比较已落盘并逐行核到（见 W4-02）。哈希面自 r1 起即合格。

### W4-05（P3 口径混用）→ **partially_open（转 W4R2-03）**
50/68 已标 executed、跳过维度已单列 ⇒ 方向已修。**残留**：`notes.md:114`「可执行数」把条目（3 目标 + 68 编译单元 + 消费者 1）与 `= 运行时用例 1219（604+615）` 用等号串起来，和式在算术上不成立；且消费者在 notes 计 **1**（程序）、`test-report.md:15` 计 **4**（用例）⇒ 同维度两口径。**处方**：拆两行 —— 「静态可执行面 = 3 自测目标 + 68 expect-to-fail 编译单元 + 1 消费者程序」「运行时用例 = 604+615 = 1219；另独立程序 2、负向 executed 50/68、消费者 4 用例 5 断言」。非阻塞。

### W4-06（P3 杂件）→ **closed**
`git ls-files -o --exclude-standard -- archives/t/trompeloeil-cpp` = **0 条**；杂件逐件取到 ignore 出处：`conandata.yml.ghfast-bak`←`archives/.gitignore:2`、`conandata.yml.orig`←`archives/.gitignore:4`、`CMakeUserPresets.json`←`.gitignore:169`、`reports/`←`:96`、`.ci-result.json`←`:238`。tracked 全包扫 `ghfast|gh-proxy|file://|pending|TODO|占位|xxxx` 只剩 `notes.md:126/160/163/167/169` 五条**披露性文字**，无申报源、无未完成标记。

---

## 通用面

- **W3 自洽**：`sha256sum reports/w3-local-ci.log` = `ce7cc415…6569` = `.ci-result.json.log_sha256`；`exit_code=0`、`step=W3_local_ci`、`integrity_hash=186d57017ea6c08c` 三处 json/notes 一致；`Building from source`×1、`Calling build(`×2 真在。注入痕迹如实同存：`w3:101` `conandata.yml updated to file:// URLs`、`w3:173` `Source ['file:///…predl_cache/…']`。
- **L 门**：`L1_RESULT=pass: test_package executed`(:422) 名副其实（:404 真跑）。`L2_RESULT=skip: no bin/ dir`(:423)、`L5_RESULT=warn: no artifacts found`(:425) 对 `header-library` + `bindirs/libdirs=[]` **良性**，不是拿 skip 当通过 —— 但行号重算后 notes 不再引用二者，`L5 warn` 全文无定性句 ⇒ **W4R2-04（P3）**：判决行清单补三条并给定性。
- **rule4/rule12**：五维读数同源 `w3-local-ci.log`；18 excluded 归因上游 `verify_compilation_error.sh` 的 `// exception:` 规则（非本窗裁剪）；鸿蒙特有面 ≥1（上游全套件 OHOS clang15/libc++ 跑 C++14+C++20 两轮 + 负向编译 `TMPDIR` 改造）；非「头文件存在即通过」（`MAKE_MOCK*`/`REQUIRE_CALL`/`TIMES`/`LR_SIDE_EFFECT`/`expectation_violation` 真断言）。
- **check-knowledge-gap 本窗实跑**（带参数 `trompeloeil-cpp 49`）：`manifest.yaml knowledge_count=5 unreferenced=0`、`notes.md total=0 extracted=0 pending=0`、`✅ 知识完整性检查通过`。补的 ref **真实存在**：`knowledge/doc/E002.md`、`knowledge/doc/E017.md`、`knowledge/drafts/DRAFT-11301-ohos-compile-fail-suite.kv` + `.md` 成对在 HEAD 树内；`manifest.yaml:31-35` 五条 `knowledge_gained` 各自带 ref。
  ⚠ 口径提醒：该门在**无「发现与知识」小节时恒绿**，绿只证明已登记条目无悬挂引用，不证明知识已入 notes 小节；本包走 manifest 通道，5 条均落 ref ⇒ 合格但不等于已登记到 notes。

## 未审（边界所致）
线上 PR 标题/正文四件套与 presubmit；CI/AI 判决与未解决意见（归 CIW）；交付态 rev 的真实 create/build（禁止重跑）；双包共存工程实跑回归；`w3-verify-r2.log:9` 未逐字复算。

## 收口前最欠 3 件
1. **W4R2-01**：按上文处方，把「`conanfile.py` cmp 相同 + `conandata.yml` 单 hunk 差异 + 绿跑态 `file://` 形态只在本地缓存」写进 `notes.md:169` 之后（这是评审/CI 会反复追问的唯一软肋）。
2. **W4R2-03 + W4R2-02**：`notes.md:114` 可执行数拆两行、`:121-123` rev 归因改成「两次换 rev，最终差在 conandata」。
3. **W4R2-04**：判决行补 `L1/L2/L5` 及定性；并确认 PR 正文携带 notes 的同一段 RREV 披露（正文不在本窗只读范围内）。
