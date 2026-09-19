# DRAFT — lang-preflight 将"单头文件库"误判为 mixed（.h 主体被统计跳过）

> 状态: 草稿（基于 verstable 2.2.1 R01 真实证据，待查重/提升）。
> Contributor: pc1-32 | 任务 verstable-2.2.1-r01-pc1-32-20260918T164131Z
> 关系: similar_to=DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect,
>       DRAFT-libcec-8.1.7-langpreflight-binding-subdir-misdetect（同类"统计噪声误判 mixed"、
>       manual-boundary-rule-override 解决方案），本条目机制新增。

## 真实问题（场景）

verstable 2.2.1 是单头文件 C 库：库主体全部在 `verstable.h`（2069 行），
仅测试文件为 `tests/unit_tests.c`（C）+ `tests/tests_against_stl.cpp`（C++，STL 对照）。
`ohc-run.py lang-preflight verstable 2.2.1 --src <源码目录>` 输出：

```json
"detected_language": "mixed",
"language_evidence": {
  "build_system": "none",
  "manifest": "未发现语言 manifest 文件",
  "source_stats": "源文件 2 个（cpp:1, c:1），主体占比 50%"
}
```

并按 R47 自动写终态 `env_unsupported`（任务语言 cpp ≠ mixed，draft:false）。

## 根因

`scripts/ohc/lang_detect.py` `_source_stats` 把 `.h` 视为"中立头文件"**完全不参与统计**
（注释明确"c/cpp 归属由 .c/.cpp 实源决定，E13"）。对单头文件库（header-only，
库主体 100% 在 .h 中）而言，库的真实语言不可见，统计只剩测试文件。
当库同时携带 `.c` 与 `.cpp` 测试（常见做法：C 单测 + C++/STL 对照或模板实例化测试）时，
c:1 / cpp:1 → 主体占比恰好 50% < 70% → 判定路径"无 manifest 且主体占比 < 70% → mixed"
→ 任务语言（默认 cpp）不匹配 → 误写终态 env_unsupported。
与协议 D.4 边界规则"c↔cpp 兼容族不迁移（conan 流程通吃）"不一致——库主体语言
（C 或 C++）完全取决于 .h 内容，统计机制对单头文件库失效。

## 修复与验证（流程侧）

按 R47 边界规则人工复核：

1. verstable.h 主体为 C11（含 `_Generic`、宏模板），库语言判 C；c↔cpp 兼容族，
   与任务 cpp 匹配，**不构成迁移条件**。
2. 继续完整适配：上游测试 2/2 编译运行通过（unit_tests.c 30 用例×1000 轮、
   tests_against_stl.cpp 5 轮×50000 操作），鸿蒙专项测试通过，conan-verify 8 道门禁、
   W3 本地 CI 全部通过 → 证明复核正确，误报被安全覆盖。

## 适用边界

- 触发: header-only 库（库主体在 .h/.hpp）+ 同时携带 .c 与 .cpp 测试文件 → 50% mixed 误判
- 不触发: 纯 .c 或纯 .cpp 测试的单头文件库（会判单语言）
- 反例: 真正多语言主体（如 .h + .cpp 实现 + .py 绑定）不适用本豁免

## 建议

- 短期（流程侧）: mixed 判定后按 D.4 边界规则人工复核主体语言（查 .h 内容与
  .c/.cpp 测试构成），c↔cpp 族不迁移
- 长期（工具侧）: `_source_stats` 对仅有 .h/.hpp 主体的头文件库可考虑将 .h 计入
  c 主体（若含 .c 测试）或增加 header-only 单文件库特判