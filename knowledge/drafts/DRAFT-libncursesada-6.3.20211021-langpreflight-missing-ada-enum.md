# DRAFT-libncursesada-6.3.20211021-langpreflight-missing-ada-enum

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-17
> **Severity**: 🔴 high | **Category**: preflight / language / ada / tooling
> **Source**: task #13329 `libncursesada@6.3.20211021`（平台 `lang=c`）

## 使用说明（何时用）

在 `ohc-run.py lang-preflight` 报出「语言匹配」但**证据可疑**时使用：

- `language_evidence.build_system` 为 `none`（`未发现语言 manifest 文件`）；
- `language_evidence.source_stats` 的**主体数量远小于源码树规模**（本例 `源文件 4 个（c:4, bash:2）`，而树内有 137 个 Ada 文件）；
- 任务名/上游名带语言线索（`*ada*`、`*lgnat*`、`AdaCurses`、`.gpr` 等）。

判定：把 `detected_language` 与**扩展名普查**对照；若"未被枚举覆盖的扩展名 ≫ 已统计主体"，
则语言门结论不可采信，必须人工裁定并在 `notes.md` 记录真实语言。

## 适用范围

- **直接**：所有 Ada（GNAT）库/工具（`.adb`/`.ads`/`.gpr`）；本例 AdaCurses / libncursesada。
- **同构**：任何主体语言不在 `LANG_ENUM` 内的项目 —— `LANG_ENUM` 只有
  `c, cpp, rust, python, go, perl, lua, nodejs, java, bash, mixed, other`，
  因此 **Fortran、D、Nim、Zig、Crystal、Ada** 等纯项目都会被判成 `c`/`cpp`/`mixed`。
- 不适用：源码树确实以 C/C++ 为主、只是夹带少量脚本的项目（那正是正常判定）。

## 输入 / 输出定义

**输入**

| 项 | 说明 |
|---|---|
| 任务元数据 | `lang`（dispatch 注入 `OHPCD_LANG`） |
| 源码目录 | `--src <checkout>` |
| 参考命令 | `find <src> -name "*.adb" \| wc -l`、`find <src> -name "*.ads" \| wc -l` |

**输出（本例实测 JSON）**

```json
{ "expected": "c", "detected_language": "c",
  "language_evidence": { "build_system": "none",
                         "manifest": "未发现语言 manifest 文件",
                         "source_stats": "源文件 4 个（c:4, bash:2），主体占比 100%" },
  "notes": [] }
```

**判定（本条目引入的补充规则）**

```
未被枚举覆盖的扩展名计数 = count(.adb) + count(.ads) + ...   # 本例 72 + 65 = 137
若 未被枚举覆盖计数 > 已统计主体计数（本例 4）  →  语言门结论不可采信，人工裁定
```

## 示例

```bash
$ OHPCD_LANG=c python3 scripts/ohc-run.py lang-preflight libncursesada 6.3.20211021 \
      --src /home/qianxia/tmp/builds/libncursesada-6.3.20211021.work
  ✅ 语言匹配: task=c, detected=c — 继续适配主流程        # <- 静默放行

$ find /home/qianxia/tmp/builds/libncursesada-6.3.20211021.work -name "*.adb" | wc -l
72
$ find /home/qianxia/tmp/builds/libncursesada-6.3.20211021.work -name "*.ads" | wc -l
65
$ find /home/qianxia/tmp/builds/libncursesada-6.3.20211021.work -name "*.c" | wc -l
4
```

→ 真实语言是 **Ada**（137 源文件 vs 4 个 C 胶水文件），被判成 `c` 并放行。

## 查重差异表

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect` | 草稿 | `GNUmakefile` 未被识别为 manifest | 非本题 —— 那是**构建文件识别**；本条是**语言枚举本身缺失** |
| `DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect` | 草稿 | 辅助 `Cargo.toml` 触发 mixed | 非本题 —— 那是**优先级/冲突规则**；本条没有任何 manifest 命中，是"枚举缺语言 + 扩展名不收录" |
| E007 / E064（autotools 相关） | 正式 | configure/build type 探测 | 非本题 —— 那发生在语言门之后的编译阶段 |
| E452 / E502 / E517（gnat/ada 关键词命中的既有条目） | 正式 | 均为 **gcc-ada 工具链/签名**问题 | 非本题 —— 本条是 **R47 语言门失效**，与工具链运行时无关 |

> 全库查证（2026-09-17）：在 `knowledge/` 全文检索 `LANG_ENUM` / `missing language enum` /
> `lang-preflight ada` 等关键词，**无正面撞车**；本条为真增量。

## 验证证据

- 原始输出：`/home/qianxia/tmp/builds/../logs/000-lang-preflight.log`（见任务工作区 `logs/000-lang-preflight.log`）
- 退出码：`EXIT=0`（**错误地**放行）
- 扩展名普查：`.adb=72`、`.ads=65`、`.c=4`（同一源码树，命令见上）
- 相关源码位置：`scripts/ohc/lang_detect.py:40`（`LANG_ENUM`）、`:47-55`（扩展名表）、`:92-138`（`_manifest_scan`）

## 平台侧修法建议

1. `LANG_ENUM` 增补 `ada`（并按需 `d`/`nim`/`zig`/`crystal`/`fortran`）；
2. `_EXT_LANG` 收录 `.adb`/`.ads`（Ada）、`.d`/`.nim`/`.zig`/`.cr`；
3. `_manifest_scan` 把 `configure.in`/`Makefile.in` 作为 autotools 的弱信号；
4. 当 `detected` 与 `expected` 仅靠 `_COMPAT_FAMILY` 相容、且 `build_system=none` 时，
   输出 warning 而不是静默 `exit 0`。
