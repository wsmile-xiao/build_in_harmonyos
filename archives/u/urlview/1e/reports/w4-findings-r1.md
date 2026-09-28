# urlview/1e — W4 独立审计 第 1 轮（z74-urlview-w4）

- 绑定 HEAD `65bdf7f9a63e32d2500f76f0d17c6665349487c7`（远端 `feat/urlview-1e` == 本地；`git status --porcelain -- archives/u/urlview` 空 ⇒ 盘 == HEAD）
- 判决：**pass**（P0 0 / P1 0 / P2 3 / P3 4）
- 一手取证全量：`~/tmp/uc2/z74-urlview-w4/probe-r1.txt`（67042 B，12 段）

## A W2 结构 / 取源诚实性 — 过
- `conandata.yml:6-26` 两枚补丁**均已登记**（无漏登记）。
- `source.url` 单枚官方址 `https://git.sr.ht/~nabijaczleweli/urlview-ng/archive/1e.tar.gz`，无 `file://`、无池址、无镜像；`git show HEAD:conandata.yml` 与盘上同值 ⇒ 未见 gh-proxy 注入残留。
- 实算：`sha256sum ~/tmp/uc2/z74-urlview/tmp/builds/urlview-1e.tar.gz` = `8522c5a5…d571`，size 31192，与 `conandata.yml:4` / `manifest.yaml:32` 逐字一致。
- `git diff --name-only origin/main...HEAD` = 10 件，全在 `archives/u/urlview/` 内，无框架文件。
- 两补丁新增行 `__OHOS__` 计数 0（逐文件实测 `0001:0 0002:0`）。

## B 上游测试申报 — 口径属实，未见 rule4 少报
- `Makefile:44-46` 实测：`check: quote` / `$(SHELLCHECK) url_handler.sh` / **`./quote`** ⇒ 委托方"2 条断言 + shellcheck"成立。
- `quote.cpp:55-63`：`#if TEST` 内一张 **2 行** `std::pair` 表，循环内一条 `assert(!strcmp(...))` ⇒ 2 条断言。
- 中性化双依据：`Makefile:9` 上游自身 `SHELLCHECK ?= $(shell command -v shellcheck … || echo @#)`；`.builds/sid+void.yml:29` `make -C urlview-ng check SHELLCHECK=:`。
- `Makefile:30` CXXFLAGS 无 `-DNDEBUG` ⇒ assert 真生效。
- `notes.md §7.1` 明写"shellcheck 是 lint 不是断言，本机 MISSING"、"不写上游测试全通过" ⇒ 未把中性化当通过。

## C 消费者测试 — 质量高，点数自洽
- 25 = 8 用例×2 + stdin×2 + 缺文件×2 + 安装面 4 + shebang 1（与 `MANIFEST.yml:19 assertion_count: 25` 相符）。
- 真跑包内二进制（`env="conanrun"` + `runenv_info.prepend_path PATH`），走 `!isatty(1)` 抽取分支；`HOME` 钉空目录消 `.urlview` 干扰。
- 夹具/输出用 `tempfile.mkdtemp`（读 `$TMPDIR`）+ `finally rmtree`，未写相对 cwd（R10 过）；`|| true|set +e|skip` 计数 0。
- 缺文件负例按上游真实语义钉 stderr 文案 + rc=0，未伪造成"应当失败"。
- ⚠ P3：`notes §7.3` 引 `urlview.c:425`，实测 pristine 428 / patched 435。

## D W3 证据自洽 — 过
- `sha256sum reports/w3-local-ci.log` = `55738f849d5a5ac88f92ba4b4a082ff5e86fa4d0e4e34850393e28ee8c310707` == `.ci-result.json:9 log_sha256`；`exit_code 0`、`integrity_hash 9174d1bb61179e14`。
- 日志 :175 `Building from source`、:183 `Calling build()`、:184 `Apply patch (portability)`、:200/:209 两条 make（含 `SHELLCHECK=:`）、:287 `urlview consumer assertions: 25`、:292 L1c ok。
- manifest 复原：`build_system: makefile`、`sha256`、`patch_classification` 的 type/platform_only/guard 均已复原为实物值（`manifest.yaml:21,32,91-99`）。
- ⚠ **P2 ×2**：`manifest.yaml:13 software: "{software}"` 占位仍在（对照 `mpgtx/1.3.1:1` 是 `software: mpgtx`）；`manifest.yaml:68 patches_applied: []` 与同文件两枚 `patch_classification` 矛盾（mpgtx 该字段有值）。
- ⚠ P3：`source_orig_hash/source_work_hash` 在随包日志内 0 命中 ⇒ 出处不可独立复核（仅 generated_at 与备份目录名相互对应）。

## E 交付物三件 — 缺失成立但不构成缺陷
- `git check-ignore -v` 实测成因：`.gitignore:96 reports/` ⇒ **新包无法把 `reports/test-report.md` 送进 PR**（main 内 478 枚系旧基线）；`.gitignore:2 packaging/` ⇒ PF2 申报属实；`.staging-verified` 在 main 内仅 2 枚，正是 §10 点名的他包杂件 ⇒ 非常规交付件。
- 委托方的 `mpgtx/1.3.1` 对照**为真**（main 内该包 11 件，三件皆无）。判决四字段已按口径抄进 `notes §10`。
- ⚠ P3：`untracked=0` 是靠忽略规则达成——盘上仍留 `patches/.patch-backup-20260927030721`、`-030935` 两枚目录与 `test_package/` 内 6 枚 conan 生成 `.sh`；清理义务未做。

## ★ F B 证据三问（只交证据，结论归主窗）
1. **libintl 空壳头骗过 `__has_include`**：`grep -ril "__has_include" knowledge/graph` = 0（棒的读数本身成立），但整 `knowledge/` 面命中 3 条同机制条目 —— `knowledge/drafts/E2181-draft-1531.md:1,13,19`（空壳头 ⇒ gettext 无声明；处方"零源码补丁注入恒等宏"；触发条件"典型裸 Makefile"）、`DRAFT-13410-trueprint-libintl-stub-header.md:1,36`、`DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext.md:59`。E015 原文复核无误（`E015.kv:18` 检测 libintl.h 后用 dgettext、`:29` `LIBS="-lintl"`，链接期家族，处方前提本平台不成立）。⇒ **既有覆盖成立，棒漏查 knowledge/drafts**（P2 见 W4-3）。
2. **libc 无 `reallocarray`**：`git grep reallocarray origin/main`（除本包）= 158 路径，含成品先例 `archives/c/confuse/3.3/notes.md:135,145,283`（"HarmonyOS 系统缺少 reallocarray()"）、`archives/b/bmon/4.0/conanfile.py:46-47,129-131`（自备 reallocarray.c）；机制条 `DRAFT-ohos-musl-glibc-specific-symbols`（rec_approach `macro-or-provide-substitute`，"②函数：提供 POSIX 等价实现…无条件、禁平台宏 R8"）与本包 patch 0001 **同处方**；但其 error_signature 字面只枚举 `program_invocation_*|get_current_dir_name|error_at_line|mkostemp`，且 `knowledge/musl-glibc-full-comparison-gnu-linux.md:166` 记"musl 1.2.3+ 有 reallocarray"（本平台实测无）。⇒ **棒未查该草稿即判不 hit，证据不足**；症状同形+处方同一条成立，字面枚举不覆盖。
3. **裸 makefile CC/CXX MISSING + 命令行覆盖 `+=`**：第 1 层已被 `E392`（`knowledge/graph/E392.kv:29,35,49`）覆盖（compiler_executables 用 `check_type=dict`、make 钉 `cwd=self.source_folder`），本包写法即 E392 原文，不得计新知识；第 2 层"命令行变量整段覆盖上游 `+=` 链 ⇒ 必须走环境通道"在本窗检索面内未见同一条，最接近的是**方向相反**的 `DRAFT-hoedown-3.0.7-makefile-cflags-override`（上游 `=` 直赋吃环境 ⇒ 改命令行传）与 automake per-target 的 `DRAFT-10251`。⇒ 若新建须写成"变量传递三层 × 上游赋值语义"合并条目以免撞 hoedown。
4. **C++23 面全绿推翻同族**：同族包在 main 属实（`archives/u/urlview-ng/1e/`，13 件）；原文 `notes.md:28,29,44,45` 已一手抄到。但 #6 把 `std::bit_width` 归为 C++23（实为 C++20），其"C++17 下不支持"本身不错 ⇒ 两包非严格互斥，差异在"是否必须改源码"。上游 `Makefile:30` 确自带 `-std=c++2b`。⇒ **属纠正既有条目，不是新机制**。

## G 框架侧两条申报 — 均属实（未代改）
- `scripts/ohc/check_env.py:32-33` 实物 `except Exception:` / `return False, str(e)` ⇒ `e` 未绑定；`~/usr/local/bin/automake` shebang 指向 `…/usr/local/bin/perl`，`ls` 该 perl = **No such file** ⇒ 触发路径成立。
- `ci/scripts/junk_check.sh:33-59`：prdiff → incremental(`:40`) → full(`:55,59`) 三级属实；三枚他包隐藏件经 `git ls-tree origin/main` 复核**均 TRACKED**（cloog 0.21.1 `.build-closed`/`.staging-verified`、kics 2.1.20 `.staging-verified`，皆空 blob `e69de29`）；本 worktree `upstream/main` = `5acd1dc19e7…`（已 fetch）、`origin/main` = `48d9cee684`（本分支基线）。

## 收口前最欠的 3 件
1. 复原 `manifest.yaml:13 software` 与 `:68 patches_applied`（两处机器可读字段与实物矛盾）。
2. 重写 `notes.md §4` 第 1/2 行的检索列（补 `knowledge/drafts` 与 `archives/*/notes.md` 两面读数，点名 E2181/DRAFT-13410/confuse/bmon），再据四条件重判 B。
3. 清 `patches/.patch-backup-*` 两枚目录与 `test_package/` 内 conan 生成 `.sh`（现靠 .gitignore 兜住，非"已移出"）。
