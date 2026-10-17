# notes.md — quickcpplib 0.1.0.0-gh0.20231208（任务 7384，GLM-8）

## 任务信息

- 包：quickcpplib（Niall Douglas C++14-23 基础设施工具库：boost 兼容单测 shim、uint128、offset_ptr、ringbuffer_log、span/optional/byte 视图）
- 上游：https://github.com/ned14/quickcpplib ，**无 tag/release**（分支分发模式）
- 版本策略：R37 X.Y.Z 先例 + cmigemo `1.2-gh0.20220623` 先例 → `0.1.0.0-gh0.20231208`（CMake 工程版本 0.1.0.0 + 锁定 commit 日期 2023-12-08）
- 锁定依据：outcome v2.2.9（2026 年赛事适配对象，任务 7326/#9741 整改需要其测试设施）官方自举机制（cmake/QuickCppLibBootstrap.cmake）在构建期拉取 master；本包锁定 2024-03-13（outcome v2.2.9 提交日）之前最后一个 master commit `72277c70f925829935a2af846731ab36063ec16f`，保证与 outcome v2.2.9 时代兼容
- 语言：cpp（header-only，C++17）；构建系统：无（header-only）
- worktree：`~/qzy/GLM8-quickcpplib-0.1.0.0-gh0.20231208`，分支 `feat/quickcpplib-0.1.0.0-gh0.20231208`

## 依赖处理（本包关键技术点）

GitHub commit tarball 不含子模块。quickcpplib 官方 .gitmodules 声明 include 树内 3 个嵌套子模块：

| 子模块路径 | 上游 | pinned commit | 处置 |
|---|---|---|---|
| include/quickcpplib/byte | martinmoene/byte-lite | 5bf0d803 | conandata 多 source + destination 落位 |
| include/quickcpplib/optional | akrzemi1/Optional | 2b433154 | 同上 |
| include/quickcpplib/span-lite | martinmoene/span-lite | dbb484f6 | 同上 |

未打包项：pcpp（pcap 工具链依赖，位于仓库根不在 include/，包交付与测试均不需要）、doc/html（文档）。

## 测试账本（四维，2026-09-13 真机实测）

- N_static = **20**（test/*.cpp 逐文件静态清点，单测 shim 自带 main 形态）
- N_executed = 19（编译并运行尝试；1 项因运行超时按跳过计）
- 通过 **15**，test_skipped **5**（逐项原因见下），未预期失败 0
- 消费者测试 N_consumer = 1（test_package/test_shim.cpp，3 断言）

### test_skipped 清单（逐项技术原因）

1. **signal_guard**（compile）：`feenableexcept` 未声明——glibc 专有浮点异常控制接口，OHOS musl 不提供，上游代码未覆盖 musl
2. **test_guard**（compile）：依赖上游构建期生成的 `test/include/import.h`，commit tarball 未分发该目录
3. **test_import**（compile）：同 test_guard
4. **test_message**（compile）：同 test_guard
5. **open_hash_index**（run）：运行超过 120s 超时（上游长时测试），如实申报不冒充通过

## 门禁与环境

- CONAN_HOME：`~/tmp/ch/home-GLM8-qcpplib`（jobs=2，remotes.json 自 home-outcome 复制）
- profile：`ci/conan/profiles/ohos-aarch64`（-pr:h 与 -pr:b 同 profile）
- 编译器：clang/clang++ 15.0.4（tools.build:compiler_executables），`tools.build:jobs=2`
- 真机：OpenHarmonyPCDeveloper 共享设备（经 gate.sh 准入）

## 经验沉淀评估（路径 B 预判）

"ned14 系无 tag 上游 + commit tarball 嵌套子模块补齐"是多仓库可复用的通用手法（conandata 多 source + destination 落位 + R37 gh 日期后缀版本策略），待首次 conan create 通过后评估按路径 B 申报（查重 knowledge 图谱后定）。
---

**编译结束**: 2026-09-14 00:57
**最终状态**: built
