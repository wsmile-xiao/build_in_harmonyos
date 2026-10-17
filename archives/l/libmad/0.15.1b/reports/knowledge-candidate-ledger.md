# Knowledge Candidate Ledger — libmad 0.15.1b

**路径初判**: B（知识库扩展）— 存在已验证、可跨库复用的查重未命中候选
**task**: libmad-0.15.1b-r01-pc6-5-20260906T152808Z
**日期**: 2026-09-07

## 候选台账

### C1: autotools configure 无法识别 HarmonyOS（config.guess/config.sub 缺 OHOS 分支）

- **真实错误**: configure 报告 `cannot guess build type; you must specify one`（UNAME_SYSTEM=HarmonyOS 不可识别）；config.guess/config.sub 无 ohos/linux-ohos 规范名。
- **根因**: 2004 年的 config.guess/config.sub 无 HarmonyOS 探测分支与规范三元组映射。
- **修复/规避**: config.guess 增加 `*:HarmonyOS:*:*` 分支输出 aarch64-unknown-linux-gnu；config.sub 增加 `ohos*`、`linux-ohos*` 规范名。
- **验证**: conan create 在 OHOS aarch64 profile 下 configure 成功，test_package 2/2 通过。
- **适用范围**: 所有基于 autotools 且内置旧 config.guess/config.sub 的 C/C++ 库。
- **查重结果**:
  - 正式知识（graph/E*.kv + doc/E*.md）: **已覆盖** — E007（config.guess 无法识别 HarmonyOS）、E160（config-guess-harmonyos-patch）、E205（patch-autotools-ohos.pl，禁止 --build/--host）、E268（config.sub Kernel not known to work with OS ohos）、E122（linux-ohos kernel-os 校验缺失）。
  - 图谱（knowledge/graph/index.tsv）: **已覆盖** — 同上多条命中。
  - 草稿（knowledge/drafts/）: **已覆盖** — DRAFT-6048-babeltrace-glibtest-autotools 等同类主题。
  - 结论: **完整重复 → 复用既有知识（E007/E205/E268），不建草稿。**

### C2: HMDFS 下 config.status mktemp 临时目录创建失败

- **真实错误**: configure 运行时 `./config.status: can't create ./confstatXXXXXX/config.h: Permission denied`（HMDFS 下 mktemp -d -q 受限）。
- **根因**: HMDFS 文件系统对 `mktemp -d` 临时目录创建有特殊限制（UID/setgid/umask 语义差异）。
- **修复/规避**: 将 `tmp=\`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null\` &&` 替换为 `tmp=./conftmp; mkdir -p $tmp;`。
- **验证**: 替换后 configure/config.status 完成，conan create 全链路通过。
- **适用范围**: 一切在 HMDFS 上跑 autotools configure 的项目。
- **查重结果**:
  - 正式知识: **已覆盖** — E011（HMDFS umask 077 mktemp）、E052（HMDFS config.status 临时目录创建失败 + tmpdir）、E060（use-tmpfs-workaround）。
  - 图谱: **已覆盖** — E011/E052/E060 命中。
  - 草稿: **未额外检索命中**（E011/E052/E060 已完整覆盖方案）。
  - 结论: **完整重复 → 复用既有知识，不建草稿。**

### C3: configure 内嵌 GCC 专属优化 flag（-fforce-mem 等）在 clang 下不可识别

- **真实错误**: configure 生成的优化 flags 含 GCC 专属 `-fforce-mem`/`-fforce-addr`/`-fthread-jumps`/`-fcse-follow-jumps`/`-fcse-skip-blocks`/`-fexpensive-optimizations`/`-fregmove`/`-fschedule-insns2`，clang 15 不识别。
- **根因**: 2004 年 libmad configure.ac 的 optimize 变量对这些 GCC 历史 flag 硬编码；clang 支持集不含它们。
- **修复/规避**: build() 中用 replace_in_file 在 configure 中逐行删除 `optimize="$optimize <flag>"` 行。
- **验证**: 删除后 configure + make 无未知选项报错，conan create 通过、解码测试输出 1152 样本。
- **适用范围**: 从 GCC 3.x 时代保留下来的 autotools 项目在 clang 工具链（OHOS 含 clang-15）适配。
- **查重结果**:
  - 正式知识（graph/doc）: **未命中** — fforce-mem/fexpensive-opt/fregmove 全库检索 0 命中；E063（-Werror）主题不同。
  - 图谱（index.tsv）: **未命中**。
  - 草稿（knowledge/drafts/）: **未命中** — 现有草稿无 GCC 专属优化 flag 主题。
  - 结论: 已验证、可跨库复用、四范围查重均未命中 → **建立草稿对 `DRAFT-libmad-0.15.1b-clang-gcc-only-optimization-flags.{kv,md}`**。

### C4: aarch64 上 mad.h 定点位宽错误（FPM_INTEL + SIZEOF_LONG=4）

- **真实错误**: libmad 默认 FPM_INTEL 定点宏 + `SIZEOF_LONG 4` 与 aarch64 的 64 位 long 不符，定点乘法/解码输出错误。
- **根因**: mad.h 由 configure 生成，x86 时代默认 FPM_INTEL 且 long=4；aarch64 需要 FPM_DEFAULT（64 位安全路径）+ SIZEOF_LONG=8。
- **修复/规避**: mad.h 内 `# define FPM_INTEL` → `FPM_DEFAULT`、`# define SIZEOF_LONG 4` → `8`。
- **验证**: 修复后完整解码一帧 MPEG-1 Layer II（128kbps/44.1kHz）输出 1152 个 PCM 样本，test_ohos 全绿。
- **适用范围**: 使用 32 位 long 定点宏的 DSP/音频解码库移植到 64 位 aarch64。
- **查重结果**:
  - 正式知识（graph/doc）: **未命中** — E117（cmake config template）仅含字面 SIZEOF_LONG 但与定点宽度无关；E306/E360/E447 主题不同。
  - 图谱（index.tsv）: **未命中**。
  - 草稿（knowledge/drafts/）: **未命中** — DRAFT-gcem（libm long double 边界）为数学库参考值域问题，非定点位宽。
  - 结论: 已验证、可跨库复用、四范围查重均未命中 → **建立草稿对 `DRAFT-libmad-0.15.1b-aarch64-fixed-point-width-wordsize.{kv,md}`**。

## 路径决定

- C1、C2 完整重复 → 复用既有知识，走路径 A 特征（常规基础适配）。
- C3、C4 已验证、可跨库复用、四范围查重均未命中 → **满足路径 B 条件**（知识库扩展：
  问题/根因/方案/验证/适用边界/查重差异齐全）。
- 判 **路径 B**：新增 2 个知识草稿（.kv/.md 同 stem 配对），PR 前缀保持【知识库扩展】。
- 知识草稿与三方库归档文件（archives/l/libmad/0.15.1b/）进入同一 PR。