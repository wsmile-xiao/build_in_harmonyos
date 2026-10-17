# DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect

> Contributor: pc4-9 | Status: Draft | Updated: 2026-09-06
> Source: 任务 debugbreak-1.0-r01-pc4-9-20260906T133424Z（debugbreak 1.0 语言预检误判）

## 背景

debugbreak 1.0 是单头文件 C/C++ 库（debugbreak.h + gdb 辅助脚本 debugbreak-gdb.py +
test/{break.c,break-c++.cc,fib.c,trap.c}），构建入口为 `GNUmakefile`（无 configure/CMake）。
`ohc-run.py lang-preflight` 输出判定：

```json
"detected_language": "mixed",
"language_evidence": {
  "build_system": "none",
  "manifest": "未发现语言 manifest 文件",
  "source_stats": "源文件 5 个（c:3, python:1, cpp:1），主体占比 60%"
}
```

并按 R47 自动写终态 `env_unsupported`（任务语言 cpp ≠ mixed）。

## 根因

`scripts/ohc/lang_detect.py` 两处与协议边界规则不一致：

1. `_manifest_scan` 只精确匹配文件名为 `Makefile` 的入口（`if "Makefile" in names`），
   `GNUmakefile`（GNU make 优先读取的入口名）未命中 → `build_system="none"`，
   丢失"make → c/cpp 族"这一 manifest 级信号。
2. `_source_stats` 按扩展名把 `debugbreak-gdb.py` 计入主体统计（c:3, py:1, cpp:1，
   total=5，主体 60% < 70%）——未执行协议 D.4-3"辅助脚本不算主体"的排除。

两者叠加 → "无 manifest 且主体占比 < 70% → mixed" → cpp 任务报 env_unsupported。

## 复核与修复（流程侧）

按协议 §D.4 边界规则人工复核：

- 辅助脚本不计入主体：剔除 debugbreak-gdb.py（gdb 调试器扩展，非库主体）→ c:3, cpp:1，主体 c/cpp 100%。
- C/C++ 混编按主体判不算 mixed；c↔cpp 为兼容族（conan 流程通吃）不迁移。
- GNUmakefile 属 make 构建系统。

复核判定 `cpp`，与任务语言匹配，继续完整适配（编译、测试、test_package、W3 全部通过），
证明复核正确。

## 验证

- 按 cpp 族完成 debugbreak 1.0 全流程：conan create（ohos-aarch64）通过，test_package 2/2，
  W3 .ci-result.json exit_code=0。
- 误判证据（文件构成 + 统计）留存于最终回报 `language_evidence` 与 notes.md 问题 #1。

## 适用边界

- 适用：以 GNUmakefile/make 为构建入口或携带辅助脚本（gdb/python/lua）的 C/C++ 库。
- 反例：真实 mixed（例如 C 主代码 + Python 主代码各近半且无 manifest）仍应上报
  env_unsupported，不得一律复核通过。