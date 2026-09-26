# tarball 缺 autotools 生成产物：prebuilt 文本携带 + 规则剥离 + os.utime 钉 mtime

- **草稿 ID**: DRAFT-libkdumpfile-0.5.6-autotools-prebuilt-utime-pin-rule-strip
- **来源**: libkdumpfile/0.5.6 G2 CI 连续 4 次失败根因修复本地验证
- **分类**: build-system / autotools / timestamp / conan-recipe / ohos-platform
- **状态**: 本地草稿（关联 PR !11680 未合入；未生成知识编号，无审核结论）

## 问题 / 错误签名

- CI G2/W3 日志（连续 4 次失败）：`missing automake-1.16`、`automake-1.16: command not found`、`Makefile: ... Error 127`；make 调试模式出现 `Must remake target 'configure'` / `'config.status'` / `'Makefile'`。
- 修复后验证：`make -d -n all`（顶层 + 9 子目录）危险目标 remake 为 0；conan-create.log 出现 `mtime 钉扎: 33 个 autotools 输入文件 -> 2020-01-01`。

## 根因（4 层）

1. **上游 tarball 缺生成产物**：libkdumpfile 0.5.6 官方 tarball 不含 configure/Makefile.in/aclocal.m4/m4/*.m4；CI worker（/data/service/hnp/bin）无 automake/aclocal，配方必须随附本地预生成产物。
2. **GitCode PR diff 不携带二进制文件内容**：prebuilt 若以 tar.gz 二进制提交，worker checkout 得到空文件 → 必须以文本形式（prebuilt/ 目录 31 个文件）提交；且 W3 JC3/PF2 制品闸明确禁止压缩/归档文件。
3. **make "严格更新" 比较 + 缺失前置 = "刚更新"**：conan export/copy2 流水线的 mtime 偏斜（缓存时间与写入时间混杂）、E114 式就地改写（umask replace_in_file）在 configure 运行后改变 configure 的 mtime —— 任一输入更新于生成目标、或任一前置文件缺失，都会触发 $(AUTOMAKE)/$(AUTOCONF)/$(ACLOCAL)/$(AUTOHEADER) recipe，在缺工具的 worker 上 exit 127 崩溃。E248 的单文件对齐（Makefile.in → Makefile.am）只覆盖一条规则，不足。
4. **本机 shell touch 不可靠**：`touch -t 202001010000.00` 存在 8 小时时区偏移（实测 1577808000 vs 期望 1577836800），`touch`（当前时间）在 HMDFS 上行为未验证 → 改用 Python `os.utime` + `stat` 校验。

## 最小修复方案（三段组合，均在 archives/l/libkdumpfile/0.5.6 范围内）

1. **全套前置携带（31 文件，文本）**：12 个顶层文件（configure/config.h.in/ltmain.sh/compile/config.guess/config.sub/install-sh/missing/depcomp/ar-lib/test-driver/aclocal.m4）+ m4/*.m4（9 个）+ 10 个 Makefile.in。prebuilt/ 下 Makefile.in 以连字符编码路径命名（Makefile-<path>.in），规避 .gitignore 的 `archives/**/include/` 规则，由 conanfile.py 的 `_MK_MAP` 反向映射回源码树位置。
2. **剥离危险规则**：从每个 Makefile.*.in 剥离 recipe 调用外部工具的 4 类规则块：

   | 剥离规则 | 调用工具 | 剥离原因 |
   | --- | --- | --- |
   | `$(srcdir)/Makefile.in:` | $(AUTOMAKE) | worker 无 automake，触发必崩 |
   | `$(top_srcdir)/configure:` | $(AUTOCONF) | worker autoconf 工具链不全 |
   | `$(ACLOCAL_M4):` | $(ACLOCAL) | worker 无 aclocal |
   | `$(srcdir)/config.h.in:` | $(AUTOHEADER) | worker 无 autoheader |

   保留：`Makefile:` 与 `$(top_builddir)/config.status:`（仅重跑 ./config.status，自修复、无需外部工具）、空规则 `$(am__aclocal_m4_deps):`、`am--refresh`（空 recipe）。
3. **os.utime 钉 mtime（带校验）**：conanfile.py build() 顺序 `apply_conandata_patches → _install_prebuilt_autotools（copy2+chmod +x）→ replace_in_file（E114 umask）→ _pin_autotools_input_mtimes → Autotools.configure()`。钉扎对象为 33 个输入（configure/configure.ac/aclocal.m4/config.h.in/10×Makefile.in/9×m4/*.m4/10×Makefile.am），统一 `os.utime(p, (1577836800,)*2)`（2020-01-01 00:00:00 UTC）；逐文件 `int(os.stat(p).st_mtime) != PIN` 校验，未生效即 `raise ConanException` 快速失败（不静默偏斜）。

## 实际验证结果

- **本地 repro 树（make -d 干跑）**：顶层 + 9 个子目录 `Must remake target '(Makefile|config.status|configure)'` 全部为 0；`make -n all` 全链 missing/automake/autoconf/aclocal 调用 0 次。
- **conan-verify（fix7）**：G0–G4 + L2/L4/L5 全 PASS，exit=0，"配方验证通过: libkdumpfile 0.5.6"；conan-create.log 出现 `mtime 钉扎: 33 个 autotools 输入文件 -> 2020-01-01`，`Must remake` 危险目标 0 次。
- **finish（W3 本地 CI）**：W3 PASS（JC6 单软件原子性在 `git fetch` 更新 origin/main 后通过，PR diff 仅含 archives/l/libkdumpfile）；W2 原子性 PASS（86 文件，无框架文件）；.ci-result.json exit_code=0（integrity_hash + log_sha256 已刷新）。
- **已知非阻塞警告**（不在 CI 门禁内）：finalize-archive RC=2（软件级 README.md / release+debug tar.gz 缺失、notes.md 无对话记录、manifest 补丁数 8 vs 磁盘 9）；W5 manifest knowledge unreferenced=3（notes.md 为空所致）；review 自检 packaging_present / test_report_present WARN（JC3/PF2 明确禁止 tar.gz 进 PR，故不提供打包产物，属预期）。

## 适用范围

- autotools tarball 不含预生成产物（configure/Makefile.in/aclocal.m4/m4）、CI worker 无 automake/aclocal、配方必须随附 prebuilt 产物的 C/C++ 库。
- 凡 make mtime 规则与"mtime 偏斜 / 就地改写 / 文件缺失"的输入集相互作用的场景。

## 非适用边界

- tarball 生成产物齐全、仅 patch 应用顺序造成 Makefile.in/Makefile.am mtime 倒挂 → 用 E248 单文件 os.utime 对齐即可，无需剥离规则。
- worker 具备完整 automake/aclocal 工具链 → 可直接 autoreconf -fis，无需携带 prebuilt。

## 查重差异

- 与 `E248`（patch 致 Makefile.in mtime 早于 Makefile.am，无 automake 时触发重生成崩溃）同属一根因族（make mtime 比较触发 automake 重生成），但 E248 前提是"tarball 生成产物齐全"、修复只对齐单文件对；本条前提是"tarball 完全缺生成产物"，需全套前置文本携带 + 剥离 4 类外部工具规则 + 全输入集 mtime 钉扎（带校验），是 E248 的必要超集扩展，二者互补、不重复。
- 未与其余 prebuilt / 工具链缺失类条目重复；无伪造编号/链接/审核。

## 关联交付

- 本草稿与 `archives/l/libkdumpfile/0.5.6/**` 同属路径 B（知识库扩展）交付范围，同一 PR（!11680）提交，PR 标题前缀为【知识库扩展】。
- 当前仅生成/放置本地草稿文件；未 commit、未合入、未触发远端 Review（远端写操作待用户确认）。
