# DRAFT: lang_detect 对纯 header-only C/C++ 库误判 "other" → env_unsupported 假终态

> 草稿编号: DRAFT-json-1.0.1-lang-preflight-headeronly-other-misdetect
> 触发任务: json 1.0.1 HarmonyOS PC 适配 R01（pc4-10, 2026-09-23）
> 状态: 草稿（待主编审核提升）

## 问题

`ohc-run.py lang-preflight` 对纯单头文件 C 库（如 json.h）输出：

```json
{"detected_language": "other",
 "language_evidence": {"build_system": "none",
                       "manifest": "未发现语言 manifest 文件",
                       "source_stats": "无源文件可统计"}}
```

随后按 R47 写入 `env_unsupported` 终态（exit 2）。实际该库是标准 C99 单头文件库
（README 明示 "JSON/SJSON parser in C99 ... single header file"）。

## 根因

`lang_detect.py::_source_stats` 按 E13 规则将 `.h` 视为**中立头文件不计数**
（"c/cpp 归属由 .c/.cpp 实源决定"）。纯 header-only 库的源码树只有 `.h`/`.hpp`
头文件 + README/LICENSE，**不存在任何 .c/.cpp 实源** → `total=0` → `dominant=None`
→ `detected="other"`（分支注释即 "无可统计源文件"）。

与既有 lang_detect 误判家族不同：
- DRAFT-exr_image（辅助 Cargo.toml → mixed）：有 .c 实源，由 manifest 冲突触发
- DRAFT-E592-libyal（根级 pyproject.toml → mixed）：有 .c 实源，由 manifest 冲突触发
- **本条：无任何实源 → other**（.h 中立计数规则在全 .h 源码树的边界失效）

## 解决方案

纯 header-only 库没有构建系统、没有 manifest、没有 .c/.cpp 实源可核验，唯一权威
证据是**上游自带的自测编译入口**（README 声明的 minimal test case）：

```bash
clang -D JSON_TEST -x c --std=c99 json.h -o json_selftest   # COMPILE_EXIT:0
./json_selftest                                            # 输出 "Minimal tests passed", RUN_EXIT:0
```

编译 + 运行通过即证明 C/C++ 语言身份，按 R47 c↔cpp 兼容族不迁移规则继续适配主流程，
并把编译命令/退出码/运行输出记录为语言证据（替代工具缺失的 manifest/统计证据）。

## 验证

- 编译: `clang -D JSON_TEST -x c --std=c99 json.h` → COMPILE_EXIT:0（仅 -Wformat 警告）
- 运行: `./json_selftest` → 输出 "Minimal tests passed"，RUN_EXIT:0
- 日志: /storage/Users/currentUser/tmp/logs/json-1.0.1/upstream_selftest_compile.log
  SHA-256: 52b50bf50da25f0c9b4f03b047f788a5587442ad06e221cb0a44ad88aeba545e
- 后续 conan-verify G2 通过、W3 本地 CI 通过，证明该库确为可正常适配的 C 库

## 适用边界 / 反例

- 适用：纯单头文件 C/C++ 库（json.h、sole.hpp、catch2/doctest 单头形态等），
  源码树无 .c/.cpp 实源、无构建系统、无 manifest。
- 反例：真正的非 C/C++ 库（Rust/Go/Python 等）——它们通常有 .rs/.go/.py 实源，
  会被正确判为对应语言；不得用本条规则绕过真实语言不匹配。
- 边界：头文件 `.h` 归属 c、`.hpp/.hh` 归属 cpp；c↔cpp 兼容族不迁移（R47）。

## 关系字段

- similar_to: DRAFT-serializer-0.5-langpreflight-headeronly-h-neutral（机制最接近：同为
  .h 中立计数 → total=0 → other → env_unsupported 假终态；本条新增差异为 C99 库 +
  以上游自带可执行自测入口 JSON_TEST 编译运行实证语言身份，区别于 serializer 的
  头文件内容静态判别）、DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest
  （mixed 出口，manifest 触发）、DRAFT-E592-libyal-root-pep517-langpreflight-mixed-misdetect
  （mixed 出口，manifest 触发）
- caused_by: []（无前置条目）
- prerequisite_of: []（无后续依赖）
- conflicts_with: []

## 框架改进建议（fallback，需单独框架 PR）

`lang_detect.py::_source_stats`：当 `total == 0` 但存在 `.h`/`.hpp` 头文件时，
不再判 other，按头文件归属判 c/cpp 族（.h→c、.hpp→cpp），或至少输出 warning
提示"疑似纯 header-only 库，请按上游自测编译命令人工核验"。
