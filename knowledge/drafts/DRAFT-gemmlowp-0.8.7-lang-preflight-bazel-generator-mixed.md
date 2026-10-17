# DRAFT — lang-preflight 误判：Bazel 构建的 header-only C++ 库（子目录代码生成器 .py）被判 mixed → env_unsupported

> Status: DRAFT (contributor pc2-44) | Source: gemmlowp/0.8.7 adaptation, task gemmlowp-0.8.7-r01-pc2-44-20260926T172052Z
> Environment: HarmonyOS PC aarch64, OHOS SDK clang 15.0.4, Conan 2.29.1 (OHOS), R47 语言预检

## 1. 问题现象

`ohc-run.py lang-preflight` 对 gemmlowp 0.8.7（纯 C++11 header-only 库）判定
`detected_language="mixed"` 并自动写入终态 `env_unsupported`：

```json
"error_detail": "任务标记 cpp，实测源码为 mixed（none），无法按 cpp 适配",
"language_evidence": {
  "build_system": "none",
  "manifest": "未发现语言 manifest 文件",
  "source_stats": "源文件 32 个（cpp:18, python:14, bash:4），主体占比 56%"
}
```

矛盾的证据一目了然：gemmlowp 的主体是 65 个 C++ 头文件（public/、fixedpoint/、
internal/、meta/、profiling/），却因 14 个代码生成器 .py 被判为 mixed。

## 2. 根因

`scripts/ohc/lang_detect.py` 两处叠加导致误判：

1. `_manifest_scan()` 不识别 Bazel：gemmlowp 官方构建系统是 Bazel（根目录 BUILD +
   WORKSPACE），检测器只识别 Cargo.toml / pyproject.toml / go.mod / CMakeLists.txt /
   configure.ac / Makefile / meson.build，没有 Bazel 分支 → build_system="none"、
   manifest="未发现语言 manifest 文件"。
2. `_source_stats()` 对代码生成器无排除：gemmlowp 的 meta/generators/ 下有 14 个
   .py（cc_emitter.py、neon_emitter.py、quantized_mul_kernels_*.py 等，用于生成
   .h 内核文件），standalone/encode.py 也是辅助工具；这些被计入 python 统计。
   .h 头文件按 E13 中立规则不参与统计 → 统计只剩 cpp 18 / python 14 → 主体占比
   56% < 70% → 无 manifest 且主体占比不足 → mixed → 对任务语言 cpp 判 exit 2。

实际库主体：public/、fixedpoint/、internal/、meta/、profiling/ 共 65 个 .h 头文件，
唯一编译源 eight_bit_int_gemm/eight_bit_int_gemm.cc，.py 全部是构建期代码生成器。

## 3. 判定与验证

| 检查 | 命令 | 结果 |
|---|---|---|
| Bazel 构建标记 | `ls BUILD WORKSPACE` | 均存在（BUILD + WORKSPACE） |
| .py 文件归因 | `find . -name '*.py'` | 14 个，全部在 meta/generators/ 与 standalone/（代码生成器/辅助） |
| .sh 文件归因 | `find . -name '*.sh'` | 4 个 CI 脚本（ci-before.sh/ci-test.sh/test-android.sh/metagemm_generate_headers.sh） |
| 主体头文件数 | `find public fixedpoint internal meta profiling -name '*.h'` | 65 个 .h |
| 兼容族 | `_COMPAT_FAMILY = {"c","cpp"}` | c↔cpp 兼容，任务 cpp 应通过 |

- 真实语言为 **C++**（header-only，Bazel 主构建），属 cpp 兼容族（R47：c↔cpp 不迁移）。
- 处置：记录为检测器误判，**继续适配主流程**（conan-verify / W3 / finish 全部通过，
  上游测试 5/5、OHOS 专项测试 4/4）；终态由最终 result 命令如实接管（不手写 JSON，
  不删除源文件）。

## 4. 修复建议（检测器侧）

`lang_detect` 应识别 Bazel 构建标记（根目录 BUILD + WORKSPACE → c/cpp 族），并对
`_source_stats` 增加代码生成器/aux 目录排除（与 _AUX_MANIFEST_DIRS 同类规则，如
paths 含 `generators/`、文件名匹配 `*_emitter.py`、`metagem*` 等），使 header-only
C++ 库在无任何 python 主体时不再落入 mixed。

## 5. 适用边界与反例

- **适用**：以 Bazel 为主构建系统的 C/C++ header-only 库；任何「根目录无被识别构建
  标记 + 子目录代码生成器 .py」的组合布局包。
- **反例**：确有 Python 主体（pybind11 绑定、setup.py 打包、.py 源 ≥ 主体）的仓库
  必须判 python/cpp 绑定，不得套用本方案。
- 不得通过删除/移动生成器目录绕过检测器（CI 仍是原仓库，误判照旧），也不得手写
  result.json 覆盖终态（R46 协议红线）。

## 6. 查重差异

四范围检索（index.tsv / doc/ / graph/*.kv / drafts/）lang-preflight 家族条目逐项对比：

| 既有条目 | 布局/签名 | 出口 | 与本条差异 |
|---|---|---|---|
| DRAFT-E592-libyal | 根级 pyproject.toml（PEP517 绑定清单）+ autotools C 主体 | manifest=python vs 统计 c≥70% 冲突 → mixed | 本条 manifest 未发现（Bazel 不识别）、无绑定清单 |
| DRAFT-bptree | dev-tooling pyproject.toml（无 [build-system]） | 误判 python | 本条无 pyproject，是生成器 .py 计入统计 |
| DRAFT-verstable | 单头文件库，.h 主体被统计跳过 | 统计剩测试 50% → mixed | 本条叠加 Bazel 未识别 + 生成器 .py 两重因素 |
| DRAFT-onnx | 根级 python 打包清单 + cpp 主体 | pyproject 优先 → python | 本条无 python 打包清单 |
| DRAFT-emio | 辅助 Cargo.toml | — | 语言不同 |
| DRAFT-random123 | GNUmakefile 未命中 manifest | none | 本条是 Bazel 未命中 |

- 正式知识（graph）全库检索 "bazel / lang-preflight / generators"：**0 命中**
  （E470 是 Bazel BUILD 与 cmake build 目录冲突，主题不同；E307/E321/E322/E257 是
  header-only 配方类，非语言预检）。
- 新增差异：lang_detect 不识别 Bazel + 代码生成器 .py 子目录计入统计，无既有条目覆盖。
- 关系：`similar_to=DRAFT-E592/DRAFT-bptree/DRAFT-verstable`（同属 lang_detect
  mixed 误判家族，本条是 Bazel+生成器新签名），无 conflicts/caused_by。

## 7. 处置（对 gemmlowp 的落地）

1. 归因工具证据里的 14 个 .py：全部为代码生成器/辅助（meta/generators/ 12 个 +
   standalone/encode.py），4 个 .sh 为 CI 脚本；
2. 确认根目录存在 BUILD + WORKSPACE（Bazel 主构建），contrib/CMakeLists.txt 为
   Debian 附带 CMake 入口；
3. 主体 = 65 个 .h 头文件 + eight_bit_int_gemm.cc，与任务语言 cpp 属 c↔cpp 兼容族
   → 判定主体语言 C++，继续适配；
4. lang-preflight 按「未执行≠通过」留痕跳过，本轮真实证据（编译/测试/门禁全部通过）
   在最终回报的 language_evidence 记录；
5. 工具缺陷另记 workflow 反馈，不在软件 PR 内改框架。

## 禁止

- 禁止因 mixed 误判对 C++ header-only 库直接接受 env_unsupported 终态；
- 禁止为通过预检删除或改写上游生成器文件；
- 禁止对真正 python 主体的项目强行按 cpp 适配（应如实上报迁移）。