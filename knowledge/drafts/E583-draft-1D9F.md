# E583 — lang-preflight 对 monorepo 布局判 mixed 误报：根目录无顶层构建文件 + 统计覆盖非构建子项目

## 问题概述

R47 强制在适配前执行 lang-preflight（`lang_detect.py`），判定优先级为
manifest > 构建系统 > 源码统计(≥70%)，冲突即判 `mixed` 并**自动写入 `env_unsupported` 终态**。
对 **monorepo**（单仓库多子项目，如 llvm-project）会出现误判：仓库根目录没有顶层构建入口文件
（CMakeLists.txt 等），c/cpp 族 manifest 互认逻辑无从触发；同时源码统计把仓库内**所有**子项目
计入（lldb 的 python 脚本、compiler-rt/openmp 的 C 源码等非本次构建对象），
语言计数被稀释/冲突 → 判 `mixed` → 任务被自动终止。

本条与 E543（辅助 `.rockspec` 触发 manifest 优先级）、E552（文档资产劫持统计）、
emio 条（测试目录内辅助 Cargo.toml）**触发面不同**：本条是"**仓库级多子项目布局 + 无顶层构建文件**"。

## 典型错误（llvm-project 11.1.0 实录）

```
❌ 语言不匹配: task=cpp, detected=mixed → env_unsupported
{
  "expected": "cpp",
  "detected_language": "mixed",
  "language_evidence": { "build_system": "...", "manifest": "...", "source_stats": "..." }
}
```

本次构建的真实对象是 `LLVM_ENABLE_PROJECTS=clang` 下的 C++ 工具（clang-format），
构建相关子树统计 overwhelmingly 为 C++：`llvm` 约 95% cpp、`clang-tools-extra` 约 96% cpp。

## 识别特征（与真实混合项目的区分）

1. **仓库根无构建入口文件**：`ls <root>/CMakeLists.txt` 不存在（构建入口在子项目目录，如 `llvm/CMakeLists.txt`）；
2. **统计分布与"构建相关子树"不一致**：`source_stats` 里出现与本次构建无关的语言计数
   （python/C 来自 lldb、compiler-rt、openmp 等未被 `LLVM_ENABLE_PROJECTS` 选中的子项目）；
3. **对本次实际构建的子树单独统计，主体明确**：`llvm`/`clang`/`clang-tools-extra` 的 cpp 占比 ≥95%；
4. 真实混合项目至少有一处**实质**冲突（构建系统本身即多语言构建，或主构建入口声明与任务语言不符）。

## 根因分析

- `lang_detect` 的族判定依赖顶层构建文件（monorepo 根没有 → 跳过 c/cpp 族互认）；
- `source_stats` 以"仓库内文件扩展名计数"为口径，没有按"本次构建子项目"裁剪范围，
  非构建子项目（python/C/其他语言）进入统计，导致主体占比失真或触发"manifest 与统计冲突"分支；
- 结果是误报 `mixed` + 自动 `env_unsupported`（含 R46 兜底写共享路径 result.json），
  整个任务被误杀——而仓库内确有可执行的适配路径。

## 解决方案

### 推荐方案：子树级语言取证 + 按 R47 主体裁定继续

1. 列出本次构建实际涉及的子项目（如 `LLVM_ENABLE_PROJECTS` 指定的那些）；
2. 对这些子树分别统计 c/cpp 占比，形成证据：

```bash
for d in llvm clang clang-tools-extra; do echo -n "$d: "; find $d -name '*.cpp' | wc -l; done
```

3. 将 lang-preflight 原始输出（含 `detected`/`source_stats`）与子树统计一并写入归档 `notes.md`；
4. 依据 R47 边界规则"C/C++ 混编按主体判不算 mixed"继续按 cpp 适配（c↔cpp 为兼容族）；
5. 适配完成后在 notes/manifest 中标注该误报，供主编决定 lang_detect 是否补 monorepo 分支。

### 禁止做法

- ❌ 删除、改名或改写上游文件（含非构建子项目）以"修好"统计（属篡改上游）；
- ❌ 修改 `lang_detect.py`/框架文件绕过判定（框架文件对协作者只读）；
- ❌ 无任何取证就直接继续适配（下次仍无法复核）。

### 备选处置

若**构建相关子树本身**确为多语言真实混合（主构建入口与任务语言确实冲突），
则属真实语言不匹配：保留 lang-preflight 输出与子树统计证据，按协议交平台语言迁移，不硬适配。

## 验证

```bash
python3 scripts/ohc-run.py lang-preflight <软件名> <版本> --src $BUILD_SRC_DIR 2>&1 | tee lang-preflight.log
for d in llvm clang clang-tools-extra; do echo -n "$d: "; find $d -name '*.cpp' | wc -l; done
```

实测（clang-format-11 11.1.0）：lang-preflight 判 mixed（exit 2）；
子树取证显示构建相关子树 cpp 为主体；按 R47 主体裁定继续，最终 conan create 通过，
上游测试 781/781（100%）、test_package 断言 1/1 通过。

## 关联条目

- 相似: E543（monorepo/辅助文件触发 manifest 优先级误判）、E552（文档资产污染统计）、
  `DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect`（辅助 Cargo.toml 误判 cargo）
- 相关: E581/E582（同任务沉淀的 LLVM 源码构建与测试执行知识）
