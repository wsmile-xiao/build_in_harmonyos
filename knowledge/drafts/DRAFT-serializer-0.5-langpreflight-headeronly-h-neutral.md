# lang-preflight 对纯头文件（仅 .h）C++ 库误判 other/none——按源码实质复核为 cpp 后继续

- **草稿 ID**: DRAFT-serializer-0.5-langpreflight-headeronly-h-neutral
- **来源**: serializer 0.5 HarmonyOS PC 适配（单 .h 头文件 C++ 序列化框架，lang-preflight 误判 other/none）
- **分类**: detection / header-only / R47 / lang-preflight
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 serializer 归档同 PR 交付）

## 问题 / 错误签名

- **错误输出**：`ohc-run.py lang-preflight serializer 0.5 --src <src>` 判定 `detected_language: other`，
  build_system=none，source_stats=`无源文件可统计`，自动写终态 `env_unsupported`（draft:false）。
- **复现**：任何只发布 `.h` 头文件（无 `.c/.cpp/.hpp/.cc`）的纯头文件 C++ 库——lang_detect.py
  `_source_stats` 把 `.h` 视为中立头文件不计数，仅 .h 时 total=0 → 无主体语言 → `other`。
- **对照验证**：serializer.h 内含 `namespace zpp`、类模板、`#include <string>/<vector>/<memory>`
  等 C++ 标准头，README 自述 "A single header only standard C++ serialization framework"；
  conan create（C++17）消费端编译、运行全部通过。

## 根因

1. **lang_detect.py `_source_stats` 的 .h 中立规则**：`# .h 跳过：中立头文件`（`_C_EXTS`/`_CPP_EXTS`
   均不含 `.h`），设计意图是 c/cpp 归属由实源决定；但对**纯头文件库**（只有 .h 没有实源）导致
   total=0，`_stats_desc` 返回 "无源文件可统计"，无 dominant 语言 → 判定 `other`。

2. **与既有 mixed 误判草稿的差异**：DRAFT-debugbreak（GNUmakefile+辅助脚本→mixed）、
   DRAFT-emio（辅助 Cargo.toml→mixed）、DRAFT-exr_image（全树 manifest→mixed）均为
   **mixed** 判定；本候选是 **other/none**（total=0，无任何可统计实源），触发条件
   （.h 中立计数）与判定结果均不同，属新增边界。

3. **R47 边界规则（附录 D.4）未覆盖此路径**：c↔cpp 属兼容族不迁移；header-only 库主体
   就是其 `.h` 头文件，源码实质（namespace/模板/C++ 头）应作为判定依据。

## 方案

**方法**: header-only-source-substance-judgement

**说明**：lang-preflight 输出 other/none 且任务语言为 c/cpp 时，先核对主头文件源码实质
（namespace、模板、C++ 标准头），纯头文件库按兼容族判 c/cpp 并记录证据后继续适配主流程；
仅当主库主体确为非 C/C++ 时才走 env_unsupported/lang_hold。

## 验证

- serializer 0.5：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
  rc=0；consumer test 与 OHOS 专项测试均 PASS；W3/finish 门禁通过。
- 本候选已跨库可复用：任意单 .h 头文件 C++ 库走 lang-preflight 时适用。

## 适用边界

- 适用：仅含 .h（无实源）的纯头文件 C/C++ 库。
- 反例：含 .c/.cpp 实源的库不应据此跳过 mixed/other 判定；确为非 C/C++ 主库
  （如脚本/数据包）必须如实走 env_unsupported。
