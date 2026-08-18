# DRAFT-ELBATCH - 纯 Emacs Lisp 包需要可复用的 emacs --batch 上游验证链路

> 正式编号未分配；合并/提升时由知识库维护流程分配下一个可用 E###。

## 错误特征

纯 Emacs Lisp 包在 OHOS Conan 环境中经常只有文件完整性、source-load 或 `test_package` marker 验证。上游真正定义的 batch 检查没有执行，日志中可能出现：

- `make: emacs: Permission denied`
- `emacs: not found`
- `Cannot open load file: compat`
- `Cannot open load file: org`
- `Cannot open load file: notmuch`
- `batch-byte-compile`、`loaddefs-generate`、`check-declare` 被记录为 `not_run`

## 触发条件

- 包主体是 `.el` 文件，没有传统 C/C++ 二进制或独立 test runner。
- 上游测试入口依赖 `emacs --batch`，例如 `make lisp`、`make compile`、`make test`、`make check`。
- 上游 Makefile 需要通过 load path 找到其他 Elisp 包，例如 `compat`、`org/lisp`、`notmuch/emacs`。
- OHOS Conan 环境尚未提供可消费的 packaged Emacs batch 执行器和对应 `EMACSLOADPATH`。

## 根因分析

这类包的“真实上游测试”不是编译一个本地二进制，也不是导入一个 Python/JS 模块，而是让 Emacs 在 batch 模式中读取项目的 Lisp 文件、解析依赖、执行 byte compile、生成 autoload、运行 ERT 或 check-declare。

如果环境里没有可运行的 `emacs --batch`，或者依赖包没有把 Lisp 安装目录暴露给下游，Conan recipe 只能退化成：

- 检查 `.el` 文件是否存在；
- 在 `test_package` 中输出 marker；
- 手工加载单个文件但绕过上游 Makefile。

这些只能证明打包产物形态存在，不能证明上游 batch 检查真实通过。

## 推荐方案

先构建最小可运行的 `emacs/29.1` batch 工具包，再把 pure Elisp 依赖拆成 Conan 包暴露 Lisp 安装目录。`emacs` 包应通过 `buildenv_info` 和 `runenv_info` 给下游导出：

- `EMACS`
- `EMACSLOADPATH`
- `EMACSDATA`
- `EMACSDOC`
- `EMACSPATH`

目标包在 `build()` 阶段执行上游入口，而不是只在 `test_package` 中做消费验证。典型链路：

```text
ncurses/6.5 -> emacs/29.1 -> compat/31.0.0.2 -> org/9.8.8 -> notmuch-emacs/0.40 -> ol-notmuch/2.1.4
```

对于 `ol-notmuch/2.1.4`，上游 `make lisp` 至少覆盖：

- `batch-byte-compile`
- `loaddefs-generate`
- `check-declare-directory`

## 禁止做法

- 不要把 `test_package` 当作上游测试。
- 不要把 marker、source-load smoke 或文件存在检查写成上游 `100.00%`。
- 不要把 batch 工具链申报成完整 Emacs GUI/桌面迁移。
- 不要把 `notmuch-emacs` pure Elisp 依赖申报成完整 Notmuch native runtime。
- 不要使用已关闭或不可发布的 `ncurses/6.5` recipe revision 作为最终验收证据。

## 验证口径

PR 和 metadata 应分别记录：

- 上游测试入口：例如 `make lisp`、`make compile`、`make test`、`make check`。
- 上游测试结果：只统计实际由上游入口执行的检查。
- 新增测试：只统计 `test_package` 或为 Conan 消费路径新增的测试。
- 依赖边界：列出 `emacs`、`compat`、`org`、`notmuch-emacs` 等包版本和 full ref。

若依赖尚未发布，当前结果只能写为 POC 或 pending，不能写成最终可提交验收。

## ol-notmuch 证据状态

2026-08-09，新端口 `33332` 上已使用远端已发布的 `ncurses/6.5`
跑通完整链路：

```text
ncurses/6.5 -> emacs/29.1 -> compat/31.0.0.2 -> org/9.8.8 -> notmuch-emacs/0.40 -> ol-notmuch/2.1.4
```

`ol-notmuch/2.1.4` 已真实执行上游 `make lisp`，并通过 packaged lisp
目录加载 `compat/org/notmuch/ol-notmuch`。`ncurses/6.5` 从 `ohpcd` Conan
remote 下载，package ID 为 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`；
不再依赖旧的本队自建 POC 产物。

本次最终链路 run id：

- `emacs/29.1`：
  `codex-a-emacs-ol-chain-ncurses65-20260809-r1-emacs-r2-conan-20260809-115855-39995`
- `compat/31.0.0.2`：
  `codex-a-compat-ol-chain-ncurses65-20260809-r1-compat-r1-conan-20260809-121741-15972`
- `org/9.8.8`：
  `codex-a-org-ol-chain-ncurses65-20260809-r1-org-r1-conan-20260809-121840-16673`
- `notmuch-emacs/0.40`：
  `codex-a-notmuch-emacs-ol-chain-ncurses65-20260809-r1-notmuch-emacs-r1-conan-20260809-122057-17554`
- `ol-notmuch/2.1.4`：
  `codex-a-ol-notmuch-ol-chain-ncurses65-20260809-r1-ol-notmuch-r1-conan-20260809-122331-18871`

## 关联条目

- Issue `#1773` / PR `!3863`：路径 B 知识库扩展 PR 可使用 `【知识库扩展】` 前缀并携带知识草稿。
- PR `!3755`：`ol-notmuch/2.1.4` 当前主 PR，建议最终作为路径 B 主载体。
- PR `!3901`：`emacs/29.1` batch 工具链依赖。
- PR `!3891`：`compat/31.0.0.2` pure Elisp 依赖。
