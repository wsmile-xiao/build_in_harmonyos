# E-DRAFT: `-I` 源码根下的同名普通文件会遮蔽 C++ 标准库头（`<version>`）

- **触发实例**：libodb / libodb-pgsql 2.4.0 适配（2026-09，分支 feat/libodb-pgsql-2.4.0）
- **错误签名**：`error: expected unqualified-id`（错误位置指向源码根的 `version` 文件，如 `version:1:1`）
- **类别**：header-shadowing（include 搜索路径上的同名普通文件遮蔽标准头）
- **严重度**：2（C++17 下所有 TU 确定性编译失败，修复模式固定）

## 症状

任何 C++17 TU（含 `<memory>`/`<new>` 等经 libc++ 传递引入 `<version>` 的文件）一编译就死：

```text
.../libodb-2.4.0/version:1:1: error: expected unqualified-id
```

报错文件根本不是源码——是源码根下随 `dist_doc_DATA` 安装的纯文本文档 `version`。

## 根因

C++17 新增的标准头名字是常见英文单词（`version`/`compare`/`concepts`/`coroutine`…）。
autotools 项目普遍 `-I$(top_srcdir)`，以便源码写 `#include <odb/database.hxx>` 这类
私有头；libodb 2.4.0 源码根恰好躺着一个名为 `version` 的纯文本文件。于是：

`#include <version>`（libc++ 头传递引入）→ angle 搜索命中 `-I` 源码根的 `version`
文本文件 → 预处理器把它当头文件整篇吞入 → 编译器在文本内容上解析失败 →
所有 C++17 TU 全灭。

工具链没有任何问题：是项目自己的 include 根遮蔽了标准库。

## 最小修复（平台无关）

把遮蔽文件移出 include 搜索路径，而不是动标准库 include：

- autotools：从 `dist_doc_DATA` 剔除 `version` 并删除源码根文件（或移入 `doc/`
  子目录、改名为 `version.txt`、改为生成到构建目录）；
- include 路径保持原样，根因消除，可上游化。

已验证：剔除后全部 C++17 TU 编译干净（本 run 定向验证 baseline exit=1 →
patched exit=0；CI run2 起补丁携带、L1 PASS）。

## 退路（有代价）

把 `-I$(top_srcdir)` 改成 `-iquote$(top_srcdir)`（只影响 `"..."` 包含，不动 `<...>`）
可以解围，但这只是掩盖碰撞——源码根仍可能遮蔽其他经 angle 包含到达的标准头。
按 P-CFLAGS-001 记技术债务，交付物仍用正式修复。

## 禁忌

- 禁止把源码根包进 `-isystem`（诊断/搜索语义改变，遮蔽并未修复，换个标准或头照样炸）；
- 禁止改、挪、删 SDK libc++ 头（污染 SDK，不可交付）；
- 禁止只在 CXXFLAGS 里堆 include 顺序补丁而保留遮蔽文件。

## 适用范围与查重

- **适用**：任何把源码根/顶层目录放进 `-I` 的构建链（autotools `-I$(top_srcdir)`、
  手写 Makefile、部分 cmake），C++17 及以上。高危文件名：`version`、`compare`、
  `concepts`、`coroutine`、`source_location`、`ranges`——构建前静态扫一眼源码根即可预判。
- **独立验证**：`d=$(mktemp -d)` 造一个含纯文本 `version` 的目录加 `-I` 编译
  `#include <memory>` TU 必失败，去掉 `-I` 对照干净（本 run 探针
  A1=FAIL_REPRODUCED / A2=PASS_CLEAN，证据 curator/probe/probe_results.log；
  首次捕获见 builder/verify/result_baseline_cxx17.txt exit=1）。
- **查重**：检索 `shadow|遮蔽`（-i）命中 knowledge/graph 全部 544 个文件中的
  30 个，逐项核验均为异机理词汇碰撞（Shadow CI、zoneinfo shadow 等）；最相近条目
  为 E133——E133 是"musl/用户 include 目录污染系统头"（系统头侧冲突），本条是
  "项目源码根普通文件遮蔽标准头"（项目侧遮蔽），机理方向相反，故 E133 为
  similar_to 而非重复；本条新颖性成立。与本 run 另一条
  DRAFT-cxx17-removed-constructs-compile-out-via-feature-macro 同域互补（同一次
  编译失败链的两个独立机理）。
