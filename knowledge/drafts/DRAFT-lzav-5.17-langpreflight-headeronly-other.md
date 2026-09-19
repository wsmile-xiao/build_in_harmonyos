# DRAFT: lang-preflight header-only C/C++ 库误判 other(none) → env_unsupported

> 知识草稿（与 `DRAFT-lzav-5.17-langpreflight-headeronly-other.kv` 配对）
> 来源任务: lzav-5.17-r01-pc4-1-20260918T174002Z（路径 B：知识库扩展）

## 问题

`lang-preflight`（lang_detect.py）对 **header-only / 单头文件 C/C++ 库** 返回
`detected_language: other (none)`，并自动写入终态 `env_unsupported`，即使该库
实为 C99/C++ 单头文件实现（官方 tag 仅含 `.h`、LICENSE、README）。

### 复现证据（lzav 5.17）

```text
官方 tag 5.17 tarball 清单（tar tzf）:
  lzav-5.17/LICENSE
  lzav-5.17/README.md
  lzav-5.17/lzav.h          # 77KB，C99 + C++ 兼容的单头文件压缩库实现

lang-preflight 输出:
  "status": "env_unsupported"
  "detected_language": "other"
  "language_evidence": { "build_system": "none", "manifest": "未发现语言 manifest 文件",
                         "source_stats": "无源文件可统计" }
```

## 根因

`lang_detect.py::_source_stats` 将 `.h` 视为中立头文件（`_H_EXTS` 不计数，
c/cpp 归属由 `.c/.cpp` 实源决定）。当库为 header-only 时：

1. 无任何 `.c/.cpp/.cc` 实源 → 源码统计零计数 → `"无源文件可统计"`
2. 无 manifest、无构建系统标记 → 判定路径落到默认 `other(none)`
3. 与任务语言 cpp 不匹配 → 自动写终态 `env_unsupported`

该判定是**假阴性**：header-only C/C++ 库属于协议 §D.4/R47 的 **c↔cpp 兼容族**
（不迁移、conan 流程通吃），工具"无证据 → other"的默认值不是真实语言不匹配。

## 方案

按 R47 边界规则**人工复核覆盖**，不得直接接受 `env_unsupported` 终态：

1. 收到 `detected_language=other(none)` 且 `source_stats="无源文件可统计"` 时，
   先列出官方 tag 文件清单；
2. 若仅含头文件/LICENSE/README（header-only C/C++ 库）→ 复核判定为 **cpp**，
   继续正常适配（header-only 由 `package_type="header-library"` 配方消费，
   无编译需求，conan 流程通吃）；
3. 记录复核证据（tar 清单、README 语言声明、头文件版本/API 宏）于 notes.md
   与最终回报 `language_evidence` 字段；
4. 仅当确为真实非 C/C++（纯 Lisp/纯脚本等）才按 lang-hold / env_unsupported 上报。

## 验证

lzav 5.17 复核为 cpp 后完整适配通过：

- conan-verify: G0 预查询 PASS / G1 配方完整性 PASS / G2 conan create PASS
  （含 test_package 消费者 + 鸿蒙专项双测试实际运行）/ G3 系统同名库隔离 PASS /
  G4 产物完整性 PASS
- W3 本地 CI 模拟 PASS（基线隔离复验后）
- 上游测试全量枚举: source_declared_total=0（官方 tag 无测试入口，附 tar 清单证据）
- 新增实际执行: 消费者验证 1/1 + 鸿蒙专项 1/1（uname=HarmonyOS, HongMeng Kernel 1.12.0）

## 适用边界 / 反例

- ✅ 适用: 官方 release tag 仅含 `.h` + LICENSE + README 的 C/C++ 单头文件库
  （lzav、及同类 header-only 库）
- ❌ 反例: 纯 Common Lisp（cl-unicode，lang-hold 正确）、纯脚本/Rust/OCaml 等
  真实非 C/C++ 库——不得用本条覆盖，必须如实上报

## 查重差异（七轴摘要）

- exact_duplicate: false（全库无"header-only 无实源 → other"条目）
- causal_duplicate: 部分（cl-unicode 同为 other/无可统计源文件但根因是纯 Lisp；
  debugbreak 同为 lang-preflight 误判但根因是 GNUmakefile 未识别 + 辅助脚本→mixed）
- trigger_overlap: 部分（`语言不匹配: task=cpp, detected=other|无可统计源文件` 文本重叠）
- solution_overlap: 部分（与 debugbreak 的 manual-boundary-rule-override 同族，
  但针对"无实源"场景而非"辅助脚本混入"场景）
- boundary_novelty: **true**（新增边界: 无 .c/.cpp 实源的纯头文件 C/C++ 库）
- combination_novelty / test_migration_novelty: false

## 关系

- similar_to: DRAFT-cl-unicode-lisp-lang-hold-verification,
  DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect
- caused_by: lang_detect.py `_source_stats` 对 .h 中立不计数 + header-only 库无实源
- conflicts_with: 无
- prerequisite_of: 无
